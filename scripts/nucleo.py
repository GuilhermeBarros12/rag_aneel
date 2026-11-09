"""
Núcleo do RAG: recuperação, montagem de prompt e geração com fallback.

pipeline.py e avaliar.py importam este módulo, então a avaliação mede
exatamente o sistema entregue. Cada resposta registra qual LLM respondeu
e quais documentos foram usados.
"""

import os
import sys
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


def carregar_recursos() -> Tuple[object, object]:
    """Garante o índice e devolve (colecao, modelo de embeddings)."""

    import chromadb
    from sentence_transformers import SentenceTransformer

    garantir_vectorstore()

    print("Carregando modelo de embeddings...")
    modelo = SentenceTransformer(config.MODELO_EMBEDDING)
    print("[OK] Modelo carregado.\n")

    client = chromadb.PersistentClient(path=config.PASTA_VECTORSTORE)
    colecao = client.get_collection(name=config.NOME_COLECAO)
    print(f"[OK] ChromaDB conectado. {colecao.count()} chunks indexados.\n")

    if config.MODO_BUSCA != "densa":
        import lexico

        if not lexico.existe():
            print("Criando o indice lexico (so na primeira execucao)...")
            lexico.construir()

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

    if config.MODO_BUSCA == "lexica":
        return carregar_trechos(lexicos[:top_k], colecao, {})

    densos = busca_densa(query, colecao, modelo, candidatos, filtro)
    ids = fundir_rrf([[t.id for t in densos], lexicos], [1.0, config.PESO_LEXICO])[:top_k]
    return carregar_trechos(ids, colecao, {t.id: t for t in densos})


def carregar_trechos(ids: List[str], colecao, conhecidos: Dict[str, Trecho]) -> List[Trecho]:
    """Monta os trechos na ordem de ids, buscando no índice os que faltam."""

    faltam = [i for i in ids if i not in conhecidos]
    trechos = dict(conhecidos)
    if faltam:
        r = colecao.get(ids=faltam, include=["documents", "metadatas"])
        for i, d, m in zip(r["ids"], r["documents"], r["metadatas"]):
            trechos[i] = Trecho(id=i, texto=d, distancia=None, metadata=m or {})
    return [trechos[i] for i in ids]


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


def gerar_resposta(prompt: str, provedores: Optional[List[str]] = None) -> Geracao:
    """
    Tenta os provedores em ordem e guarda os erros de quem falhou.
    Sem a lista, usa Gemini e depois Groq.
    """

    disponiveis = {
        "gemini": (f"gemini/{config.GEMINI_MODELO}", gerar_com_gemini),
        "groq": (f"groq/{config.GROQ_MODELO}", gerar_com_groq),
    }

    erros: List[str] = []
    for chave in provedores or ["gemini", "groq"]:
        nome, gerar = disponiveis[chave]
        try:
            texto = (gerar(prompt) or "").strip()
            if not texto:
                raise ValueError("resposta vazia")
            return Geracao(texto=texto, llm=nome, erros=erros)
        except Exception as e:
            erros.append(f"{nome}: {e}")

    return Geracao(texto=None, llm=None, erros=erros)


# ============================================================
# PIPELINE COMPLETO
# ============================================================


def responder(
    query: str,
    colecao,
    modelo,
    top_k: int = config.TOP_K,
    provedores: Optional[List[str]] = None,
) -> RespostaRAG:
    """Pipeline RAG completo: pergunta, recuperação, prompt e geração."""

    trechos = recuperar_trechos(
        query, colecao, modelo, top_k=top_k, filtro=config.FILTRO_PADRAO
    )
    geracao = gerar_resposta(montar_prompt(query, trechos), provedores=provedores)

    resposta = geracao.texto
    if resposta is None:
        detalhes = "\n".join(f"  {e}" for e in geracao.erros)
        resposta = f"[ERRO] Nenhum LLM disponivel.\n{detalhes}"

    return RespostaRAG(
        pergunta=query,
        resposta=resposta,
        llm=geracao.llm,
        erros=geracao.erros,
        trechos=trechos,
    )
