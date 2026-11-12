"""
Núcleo do RAG: recuperação, montagem de prompt e geração com fallback.

pipeline.py e avaliar.py importam este módulo, então a avaliação mede
exatamente o sistema entregue. Cada resposta registra qual LLM respondeu
e quais documentos foram usados.
"""

import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import config

# ============================================================
# ESTRUTURAS DE DADOS
# ============================================================


@dataclass
class Trecho:
    """Um chunk recuperado do índice, com a origem dele."""

    id: str
    texto: str
    distancia: Optional[float]  # None se o trecho veio só da busca léxica
    metadata: Dict[str, str]

    @property
    def titulo(self) -> str:
        return self.metadata.get("titulo", "")

    @property
    def arquivo(self) -> str:
        return self.metadata.get("arquivo_original", "")


@dataclass
class Geracao:
    """Resultado da chamada aos LLMs. llm fica None se todos falharem."""

    texto: Optional[str]
    llm: Optional[str]
    erros: List[str] = field(default_factory=list)


@dataclass
class RespostaRAG:
    """Tudo que o sistema produziu para uma pergunta."""

    pergunta: str
    resposta: str
    llm: Optional[str]
    erros: List[str]
    trechos: List[Trecho]

    @property
    def documentos(self) -> List[Dict[str, str]]:
        """Documentos usados, sem repetição, na ordem de recuperação."""
        vistos = {}
        for t in self.trechos:
            vistos.setdefault(t.arquivo, {"titulo": t.titulo, "arquivo": t.arquivo})
        return list(vistos.values())

    def para_dict(self) -> dict:
        """Formato salvo nos resultados da avaliação."""
        return {
            "pergunta": self.pergunta,
            "resposta": self.resposta,
            "llm": self.llm,
            "erros": self.erros,
            "documentos": self.documentos,
            "trechos": [asdict(t) for t in self.trechos],
        }


# ============================================================
# ÍNDICE E MODELO
# ============================================================


def garantir_vectorstore() -> None:
    """Baixa o índice do Hugging Face se ele não existir localmente."""

    if os.path.exists(os.path.join(config.PASTA_VECTORSTORE, "chroma.sqlite3")):
        print("[OK] Vectorstore encontrado localmente.")
        return

    print(f"Vectorstore nao encontrado. Baixando de: {config.HF_REPO_ID}")
    print("(Primeira execucao: cerca de 4,4 GB)\n")

    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=config.HF_REPO_ID,
            repo_type="dataset",
            local_dir=config.PASTA_VECTORSTORE,
        )
        print("[OK] Vectorstore baixado com sucesso.\n")
    except Exception as e:
        print(f"[ERRO] Falha ao baixar o vectorstore: {e}")
        print("       Verifique sua conexao e o valor de HF_REPO_ID no .env")
        sys.exit(1)


def garantir_lexico() -> None:
    """Garante o acervo léxico: usa o local, baixa o pronto ou cria a partir do índice vetorial."""

    import lexico

    if lexico.existe():
        return

    tem_indice = os.path.exists(os.path.join(config.PASTA_VECTORSTORE, "chroma.sqlite3"))
    if not tem_indice:
        print(f"Acervo lexico nao encontrado. Tentando baixar de: {config.HF_REPO_ID}")
        if lexico.baixar():
            print("[OK] Acervo lexico baixado.\n")
            return
        print("Acervo pronto indisponivel. Sera criado a partir do indice vetorial.")
        garantir_vectorstore()

    print("Criando o acervo lexico (so na primeira execucao)...")
    lexico.construir()


def carregar_recursos() -> Tuple[object, object]:
    """
    Prepara o que o modo de busca precisa e devolve (colecao, modelo de embeddings).
    No modo "lexica" os dois são None: basta o acervo léxico, sem ChromaDB nem embeddings.
    """

    if config.MODO_BUSCA != "densa":
        import lexico

        garantir_lexico()
        print(f"[OK] Acervo lexico pronto. {lexico.total()} chunks.\n")

    if config.MODO_BUSCA == "lexica":
        return None, None

    # Importados só aqui: são pesados e o modo léxico não precisa deles
    import chromadb
    from sentence_transformers import SentenceTransformer

    garantir_vectorstore()

    print("Carregando modelo de embeddings...")
    modelo = SentenceTransformer(config.MODELO_EMBEDDING)
    print("[OK] Modelo carregado.\n")

    client = chromadb.PersistentClient(path=config.PASTA_VECTORSTORE)
    colecao = client.get_collection(name=config.NOME_COLECAO)
    print(f"[OK] ChromaDB conectado. {colecao.count()} chunks indexados.\n")

    if config.MODO_BUSCA == "hibrida" and lexico.total() != colecao.count():
        print(f"[AVISO] O acervo lexico tem {lexico.total()} chunks e o indice vetorial tem "
              f"{colecao.count()}. Rode 'python scripts/lexico.py' para recriar o acervo.\n")

    return colecao, modelo


# ============================================================
# RETRIEVER
# ============================================================


def fundir_rrf(listas: List[List[str]], pesos: List[float], k: int = config.RRF_K) -> List[str]:
    """Reciprocal Rank Fusion com pesos: soma peso/(k + posição) de cada lista e ordena."""

    pontos: Dict[str, float] = {}
    for lista, peso in zip(listas, pesos):
        for posicao, item in enumerate(lista, 1):
            pontos[item] = pontos.get(item, 0.0) + peso / (k + posicao)
    return sorted(pontos, key=lambda item: pontos[item], reverse=True)


def recuperar_trechos(
    query: str,
    colecao,
    modelo,
    top_k: int = config.TOP_K,
    filtro: Optional[dict] = None,
) -> List[Trecho]:
    """Recupera os top_k trechos segundo config.MODO_BUSCA."""

    if config.MODO_BUSCA == "densa":
        return busca_densa(query, colecao, modelo, top_k, filtro)

    import lexico

    candidatos = max(top_k, config.CANDIDATOS_FUSAO)
    excluir = filtro["situacao"]["$ne"] if filtro else None
    lexicos = lexico.buscar(query, candidatos, excluir_situacao=excluir)

    conhecidos: Dict[str, Trecho] = {}
    ids = lexicos
    if config.MODO_BUSCA != "lexica":
        densos = busca_densa(query, colecao, modelo, candidatos, filtro)
        conhecidos = {t.id: t for t in densos}
        ids = fundir_rrf([[t.id for t in densos], lexicos], [1.0, config.PESO_LEXICO])

    if config.RERANKER == "nenhum":
        return carregar_trechos(ids[:top_k], conhecidos)
    trechos = carregar_trechos(ids[:max(top_k, config.RERANK_CANDIDATOS)], conhecidos)
    return reordenar(query, trechos)[:top_k]


# Ordem dada pelo reranker a cada (modelo, pergunta, candidatos): evita pagar duas vezes
# pela mesma chamada. A medição salva e recarrega este dicionário entre execuções.
CACHE_RERANK: Dict[str, List[str]] = {}
FALHAS_RERANK: List[str] = []


def chave_rerank(query: str, ids: List[str]) -> str:
    return " | ".join([config.COHERE_RERANK_MODELO, query, ",".join(ids)])


def reordenar(query: str, trechos: List[Trecho]) -> List[Trecho]:
    """Reordena os trechos com config.RERANKER. Se o reranker falhar, mantém a ordem da busca."""
    if len(trechos) < 2:
        return trechos
    chave = chave_rerank(query, [t.id for t in trechos])
    if chave not in CACHE_RERANK:
        try:
            CACHE_RERANK[chave] = rerank_cohere(query, trechos)
        except Exception as e:
            FALHAS_RERANK.append(f"{query[:60]}: {e}")
            print(f"[AVISO] Reranker falhou, mantida a ordem da busca: {e}")
            return trechos
    por_id = {t.id: t for t in trechos}
    return [por_id[i] for i in CACHE_RERANK[chave] if i in por_id]


def rerank_cohere(query: str, trechos: List[Trecho]) -> List[str]:
    """Chama o rerank da Cohere e devolve os ids do mais para o menos relevante."""
    import httpx

    chave = os.getenv("COHERE_API_KEY", "")
    if not chave:
        raise ValueError("COHERE_API_KEY nao configurada no .env")
    documentos = [f"{t.titulo}\n{t.texto[:config.MAX_CHARS_TRECHO]}" for t in trechos]
    for tentativa in range(1, config.RERANK_TENTATIVAS + 1):
        r = httpx.post(
            "https://api.cohere.com/v2/rerank",
            headers={"Authorization": f"Bearer {chave}"},
            json={"model": config.COHERE_RERANK_MODELO, "query": query, "documents": documentos},
            timeout=config.TIMEOUT_LLM_S,
        )
        if r.status_code == 429 and tentativa < config.RERANK_TENTATIVAS:
            time.sleep(config.RERANK_ESPERA_S * tentativa)
            continue
        if r.status_code != 200:
            raise ErroDeApi(f"{r.status_code} {r.text[:300]}", status_code=r.status_code)
        return [trechos[item["index"]].id for item in r.json()["results"]]
    raise ErroDeApi("limite por minuto", status_code=429)


def carregar_trechos(ids: List[str], conhecidos: Dict[str, Trecho]) -> List[Trecho]:
    """Monta os trechos na ordem de ids, lendo do acervo léxico os que faltam."""

    import lexico

    trechos = dict(conhecidos)
    faltam = [i for i in ids if i not in trechos]
    for chunk_id, texto, metadata in lexico.carregar(faltam):
        trechos[chunk_id] = Trecho(id=chunk_id, texto=texto, distancia=None, metadata=metadata)
    return [trechos[i] for i in ids if i in trechos]


def busca_densa(
    query: str,
    colecao,
    modelo,
    top_k: int,
    filtro: Optional[dict] = None,
) -> List[Trecho]:
    """Embeda a pergunta e devolve os top_k chunks mais próximos, com metadata."""

    embedding = modelo.encode(query, convert_to_numpy=True).tolist()

    kwargs = {
        "query_embeddings": [embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if filtro:
        kwargs["where"] = filtro

    r = colecao.query(**kwargs)

    # O Chroma devolve uma lista por pergunta; enviamos só uma
    return [
        Trecho(id=i, texto=d, distancia=dist, metadata=m or {})
        for i, d, m, dist in zip(
            r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0]
        )
    ]


# ============================================================
# GERAÇÃO
# ============================================================


def montar_prompt(query: str, trechos: List[Trecho]) -> str:
    """Monta o prompt com cada trecho identificado pelo documento de origem."""

    contexto = "\n\n---\n\n".join(
        f"[Trecho {i + 1}] {t.titulo} | {t.metadata.get('publicacao', '')} | "
        f"{t.metadata.get('situacao', '')} | Arquivo: {t.arquivo}\n"
        f"{t.texto[:config.MAX_CHARS_TRECHO]}"
        for i, t in enumerate(trechos)
    )
    return config.PROMPT_TEMPLATE.format(contexto=contexto, query=query)


def gerar_com_gemini(prompt: str) -> str:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nao configurada no .env")

    # O cliente precisa ficar em uma variável: sem isso ele é fechado antes da chamada
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=config.TIMEOUT_LLM_S * 1000),  # em ms
    )
    response = client.models.generate_content(
        model=config.GEMINI_MODELO,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=config.TEMPERATURA),
    )
    return response.text


def gerar_com_groq(prompt: str) -> str:
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "sua_chave_groq_aqui":
        raise ValueError("GROQ_API_KEY nao configurada no .env")

    client = Groq(api_key=api_key, timeout=config.TIMEOUT_LLM_S)
    response = client.chat.completions.create(
        model=config.GROQ_MODELO,
        temperature=config.TEMPERATURA,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


class ErroDeApi(Exception):
    """Erro devolvido por um provedor, com o código HTTP (usado por tipo_de_erro)."""

    def __init__(self, mensagem: str, status_code: Optional[int] = None):
        super().__init__(mensagem)
        self.status_code = status_code


def gerar_com_compativel(provedor: str, prompt: str) -> str:
    """Chama um provedor compatível com a API da OpenAI (ver config.PROVEDORES_COMPATIVEIS)."""
    import httpx

    p = config.PROVEDORES_COMPATIVEIS[provedor]
    cabecalhos = {}
    if p["chave"]:
        chave = os.getenv(p["chave"], "")
        if not chave:
            raise ValueError(f"{p['chave']} nao configurada no .env")
        cabecalhos["Authorization"] = f"Bearer {chave}"
    if not p["modelo"]:
        raise ValueError(f"defina o modelo do provedor {provedor} no .env")

    espera = config.TIMEOUT_LOCAL_S if provedor == "local" else config.TIMEOUT_LLM_S
    r = httpx.post(
        p["url"].rstrip("/") + "/chat/completions",
        headers=cabecalhos,
        json={"model": p["modelo"], "temperature": config.TEMPERATURA,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=espera,
    )
    if r.status_code != 200:
        raise ErroDeApi(f"{r.status_code} {r.text[:300]}", status_code=r.status_code)
    return r.json()["choices"][0]["message"]["content"]


def nome_do_modelo(provedor: str) -> str:
    """'groq' vira 'groq/openai/gpt-oss-120b', e assim por diante."""
    if provedor == "gemini":
        return f"gemini/{config.GEMINI_MODELO}"
    if provedor == "groq":
        return f"groq/{config.GROQ_MODELO}"
    return f"{provedor}/{config.PROVEDORES_COMPATIVEIS[provedor]['modelo']}"


def tipo_de_erro(erro: Exception) -> str:
    """
    Classifica o erro de um LLM:
    "cota"       — limite diário esgotado; insistir não adianta
    "temporario" — sobrecarga ou limite por minuto; vale tentar de novo
    "definitivo" — o resto (chave errada, modelo inexistente, tempo esgotado)
    """
    texto = str(erro).lower()
    codigo = getattr(erro, "status_code", None) or getattr(erro, "code", None)

    if "per day" in texto or "quota" in texto:
        return "cota"
    if "timeout" in texto or "timed out" in texto or "deadline" in texto:
        return "definitivo"  # esperar mais 60 s é pior do que seguir para o próximo LLM
    if codigo in (429, 500, 502, 503) or "unavailable" in texto or "rate limit" in texto:
        return "temporario"
    return "definitivo"


def gerar_resposta(prompt: str, provedores: Optional[List[str]] = None) -> Geracao:
    """
    Tenta os provedores em ordem e guarda os erros de quem falhou.
    Sem a lista, usa Gemini e depois Groq. Erros temporários ganham nova tentativa.
    """

    disponiveis = {
        "gemini": (nome_do_modelo("gemini"), gerar_com_gemini),
        "groq": (nome_do_modelo("groq"), gerar_com_groq),
    }
    for nome in config.PROVEDORES_COMPATIVEIS:
        disponiveis[nome] = (nome_do_modelo(nome), lambda prompt, nome=nome: gerar_com_compativel(nome, prompt))

    erros: List[str] = []
    for chave in provedores or ["gemini", "groq"]:
        nome, gerar = disponiveis[chave]
        for tentativa in range(1, config.TENTATIVAS_LLM + 1):
            try:
                texto = (gerar(prompt) or "").strip()
                if not texto:
                    raise ValueError("resposta vazia")
                return Geracao(texto=texto, llm=nome, erros=erros)
            except Exception as e:
                tipo = tipo_de_erro(e)
                erros.append(f"{nome} ({tipo}): {e}")
                if tipo != "temporario" or tentativa == config.TENTATIVAS_LLM:
                    break
                time.sleep(config.ESPERA_ENTRE_TENTATIVAS_S * tentativa)

    return Geracao(texto=None, llm=None, erros=erros)


# ============================================================
# PIPELINE COMPLETO
# ============================================================


def expandir_contexto(trechos: List[Trecho]) -> List[Trecho]:
    """
    Amplia o contexto a partir dos trechos encontrados, documento por documento, na ordem da busca:
    documento curto entra inteiro; de documento longo entram os trechos encontrados e os vizinhos.
    Para quando o contexto atinge config.MAX_CHARS_CONTEXTO, mas sempre mantém o primeiro trecho.
    """
    import lexico

    if config.EXPANSAO_CONTEXTO != "documento" or not trechos:
        return trechos

    achados = {t.id for t in trechos}
    ordem_docs = list(dict.fromkeys(lexico.documento_do_chunk(t.id) for t in trechos))
    resultado: List[Trecho] = []
    usados = set()
    total = 0
    for doc in ordem_docs:
        chunks = lexico.chunks_do_documento(doc)
        tamanho = sum(len(texto) for _, texto, _ in chunks)
        if tamanho <= config.LIMITE_DOC_CURTO_CHARS:
            escolhidos = chunks
        else:
            posicoes = {i for i, (cid, _, _) in enumerate(chunks) if cid in achados}
            janela = {p + d for p in posicoes for d in range(-config.VIZINHOS, config.VIZINHOS + 1)}
            escolhidos = [c for i, c in enumerate(chunks) if i in janela]
        for cid, texto, metadata in escolhidos:
            if cid in usados:
                continue
            custo = min(len(texto), config.MAX_CHARS_TRECHO)
            if resultado and total + custo > config.MAX_CHARS_CONTEXTO:
                return resultado
            resultado.append(Trecho(id=cid, texto=texto, distancia=None, metadata=metadata))
            usados.add(cid)
            total += custo
    return resultado


# Pergunta que cita um ato: "Despacho nº 3.683", "Resolução Autorizativa nº 10.230", "3.386/2016"
_CITA_ATO = re.compile(
    r"\b(?:despacho|resolu\w*|portaria|decreto|lei|edital|comunicado|of[ií]cio|nota t[eé]cnica)\b\D{0,30}\d"
    r"|\b\d{1,3}(?:\.\d{3})*\s*/\s*\d{4}\b",
    re.IGNORECASE,
)
# Pergunta sobre a situação do ato: "está vigente?", "foi revogada?", "ainda está em vigor?"
_SOBRE_VIGENCIA = re.compile(r"revoga|vig[eê]n|em vigor|vigora|ainda vale", re.IGNORECASE)


def motivo_para_incluir_revogados(query: str) -> Optional[str]:
    """Diz por que a política intermediária inclui revogados nesta pergunta, ou None."""
    if _SOBRE_VIGENCIA.search(query):
        return "pergunta sobre vigência"
    if _CITA_ATO.search(query):
        return "pergunta cita um ato"
    return None


def recuperar_com_politica(query: str, colecao, modelo, top_k: int = config.TOP_K) -> List[Trecho]:
    """Recupera os trechos aplicando config.POLITICA_REVOGADOS."""

    politica = config.POLITICA_REVOGADOS
    if politica == "incluir":
        return recuperar_trechos(query, colecao, modelo, top_k=top_k, filtro=None)
    if politica == "intermediaria" and motivo_para_incluir_revogados(query):
        return recuperar_trechos(query, colecao, modelo, top_k=top_k, filtro=None)

    trechos = recuperar_trechos(query, colecao, modelo, top_k=top_k, filtro=config.FILTRO_SEM_REVOGADOS)
    if not trechos and politica == "intermediaria":
        # nada vigente encontrado: os revogados são a única fonte possível
        trechos = recuperar_trechos(query, colecao, modelo, top_k=top_k, filtro=None)
    return trechos


def responder(
    query: str,
    colecao,
    modelo,
    top_k: int = config.TOP_K,
    provedores: Optional[List[str]] = None,
) -> RespostaRAG:
    """Pipeline RAG completo: pergunta, recuperação, prompt e geração."""

    trechos = []
    if query.strip():
        trechos = expandir_contexto(recuperar_com_politica(query, colecao, modelo, top_k=top_k))

    # Sem trechos não há o que perguntar ao LLM: responde direto, sem gastar cota
    if not trechos:
        return RespostaRAG(
            pergunta=query,
            resposta=config.RESPOSTA_SEM_TRECHOS,
            llm=config.SEM_LLM,
            erros=[],
            trechos=[],
        )

    geracao = gerar_resposta(montar_prompt(query, trechos), provedores=provedores)

    resposta = geracao.texto
    if resposta is None:
        detalhes = "\n".join(f"  {e}" for e in geracao.erros)
        resposta = f"[ERRO] Nenhum LLM disponivel.\n{detalhes}"
        if any("(cota)" in e for e in geracao.erros):
            resposta += "\nA cota diaria de um LLM acabou. Tente mais tarde ou troque o modelo no .env."

    return RespostaRAG(
        pergunta=query,
        resposta=resposta,
        llm=geracao.llm,
        erros=geracao.erros,
        trechos=trechos,
    )
