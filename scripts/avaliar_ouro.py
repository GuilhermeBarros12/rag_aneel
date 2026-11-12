"""
Mede o sistema no conjunto de ouro, sem juiz de LLM.

Recuperação: hit@k e MRR, verificando se um documento esperado veio entre os k
primeiros resultados.
Geração (com --com-llm): abstenção nas perguntas que devem ser recusadas, recusa
indevida nas demais e presença dos termos esperados na resposta.
"""

import argparse
import collections
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Optional

import config
import nucleo
from nucleo import (
    carregar_recursos,
    expandir_contexto,
    nome_do_modelo,
    recuperar_com_politica,
    recuperar_trechos,
    responder,
)

KS = (1, 3, 5, 10)
FRASE_RECUSA = "nao encontrei informacao suficiente"
# Respostas do reranker guardadas entre execuções, para não gastar a cota duas vezes
CACHE_RERANK = os.path.join(os.path.dirname(config.PASTA_LEXICO), "cache_experimentos", "rerank.json")
DELAY_ENTRE_PERGUNTAS = float(os.getenv("AVALIACAO_ESPERA_S", "2"))  # segundos entre perguntas, para evitar rate limit

# ============================================================
# MÉTRICAS (funções puras, sem índice nem rede)
# ============================================================


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, sem ponto de milhar e com espaços simples, para comparar textos."""
    # hífens e travessões tipográficos (U+2010 a U+2015 e o sinal de menos U+2212) viram "-"
    texto = re.sub("[‐-―−]", "-", texto)
    # separador de milhar: "1.045", "1 045" e "1045" passam a ser iguais (inclui espaços finos e sem quebra)
    texto = re.sub(r"(?<=\d)[.\s  ](?=\d{3}(?!\d))", "", texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto).lower()


def documento_do_trecho(trecho_id: str) -> str:
    """'dsp20163386_chunk4' vira 'dsp20163386'."""
    return re.sub(r"_chunk\d+$", "", trecho_id)


def posicao_primeiro_acerto(ids: List[str], esperados: List[str]) -> Optional[int]:
    """Posição (a partir de 1) do primeiro trecho de um documento esperado."""
    alvo = set(esperados)
    for posicao, trecho_id in enumerate(ids, 1):
        if documento_do_trecho(trecho_id) in alvo:
            return posicao
    return None


def trecho_correto(trecho_id: str, texto: str, q: dict) -> bool:
    """
    Diz se um trecho recuperado serve para a pergunta.
    Perguntas com 'evidencia' exigem que o texto do trecho contenha esses termos;
    as demais exigem que o trecho venha de um documento esperado.
    """
    if q.get("evidencia"):
        return contem_termos(texto, q["evidencia"])
    return documento_do_trecho(trecho_id) in q["documentos_esperados"]


def posicao_primeiro_correto(trechos, q: dict) -> Optional[int]:
    """Posição (a partir de 1) do primeiro trecho correto para a pergunta."""
    for posicao, t in enumerate(trechos, 1):
        if trecho_correto(t.id, t.texto, q):
            return posicao
    return None


def trechos_citados(resposta: str) -> List[int]:
    """Números citados na resposta: '[Trecho 2]' e '[Trechos 1 e 3]' viram [2] e [1, 3]."""
    numeros = []
    for grupo in re.findall(r"Trechos?\s+([\d\s,e]+)", resposta, flags=re.IGNORECASE):
        numeros += [int(n) for n in re.findall(r"\d+", grupo)]
    return numeros


def resumir_posicoes(posicoes: List[Optional[int]]) -> Dict[str, float]:
    """Calcula hit@k e MRR. Uma pergunta sem acerto até k=10 soma zero."""
    n = len(posicoes)
    resumo = {"n": n}
    for k in KS:
        resumo[f"hit@{k}"] = sum(1 for p in posicoes if p and p <= k) / n
    resumo["mrr"] = sum(1 / p for p in posicoes if p) / n
    return resumo


def recusou(resposta: str) -> bool:
    return FRASE_RECUSA in normalizar(resposta)


def contem_termos(resposta: str, termos: List[str]) -> bool:
    texto = normalizar(resposta)
    return all(normalizar(t) in texto for t in termos)


# ============================================================
# EXECUÇÃO
# ============================================================


def medir_recuperacao(perguntas: List[dict], colecao, modelo, filtro, usar_politica: bool = False) -> List[dict]:
    """Mede a recuperação com um filtro fixo ou, com usar_politica, com a política de revogados do sistema."""
    linhas = []
    for q in perguntas:
        if usar_politica:
            trechos = recuperar_com_politica(q["pergunta"], colecao, modelo, top_k=max(KS))
        else:
            trechos = recuperar_trechos(q["pergunta"], colecao, modelo, top_k=max(KS), filtro=filtro)
        linha = {
            "id": q["id"],
            "categoria": q["categoria"],
            "posicao": posicao_primeiro_correto(trechos, q),
            "top3": [t.id for t in trechos[:3]],
        }
        if usar_politica:
            # o que de fato vai ao LLM: os top_k do sistema, com a expansão configurada
            contexto = expandir_contexto(recuperar_com_politica(q["pergunta"], colecao, modelo))
            linha["resposta_no_contexto"] = any(trecho_tem_resposta(t.texto, q) for t in contexto)
            linha["chars_contexto"] = sum(min(len(t.texto), config.MAX_CHARS_TRECHO) for t in contexto)
        linhas.append(linha)
        salvar_cache_rerank(CACHE_RERANK)  # a cada pergunta, para sobreviver a uma interrupção
    return linhas


def trecho_tem_resposta(texto: str, q: dict) -> bool:
    """O trecho contém a resposta: os termos esperados ou, se houver, a evidência exigida."""
    if q.get("evidencia"):
        return contem_termos(texto, q["evidencia"])
    return bool(q["termos"]) and contem_termos(texto, q["termos"])


def salvar_json(caminho: str, dados) -> None:
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


def medir_geracao(perguntas: List[dict], colecao, modelo, caminho_parcial: str, assinatura: dict) -> List[dict]:
    """
    Usa um único LLM, para os números não misturarem modelos.
    Salva o progresso a cada pergunta: se a cota acabar, basta rodar o mesmo
    comando de novo para continuar de onde parou.
    """
    linhas = []
    if os.path.exists(caminho_parcial):
        with open(caminho_parcial, encoding="utf-8") as f:
            parcial = json.load(f)
        if parcial["assinatura"] != assinatura:
            raise SystemExit(f"[ERRO] {caminho_parcial} veio de outra configuracao. Apague o arquivo ou use outro --rotulo.")
        linhas = parcial["linhas"]
        print(f"[RETOMADA] {len(linhas)} perguntas ja respondidas.")
    feitas = {l["id"] for l in linhas}

    for i, q in enumerate(perguntas, 1):
        if q["id"] in feitas:
            continue
        print(f"[{i}/{len(perguntas)}] {q['pergunta'][:70]}")
        inicio = time.time()
        r = responder(q["pergunta"], colecao, modelo, provedores=[config.LLM_AVALIACAO])
        segundos = round(time.time() - inicio, 1)
        if r.llm is None:
            print(r.resposta)
            raise SystemExit(f"[ERRO] Medicao interrompida em {q['id']}. Progresso salvo; rode o mesmo comando para continuar.")

        # trechos que a resposta citou, pela marcação [Trecho N]
        citados = [r.trechos[n - 1] for n in trechos_citados(r.resposta) if 1 <= n <= len(r.trechos)]
        linhas.append({
            "id": q["id"],
            "categoria": q["categoria"],
            "deve_recusar": q["deve_recusar"],
            "llm": r.llm,
            "resposta": r.resposta,
            "recusou": recusou(r.resposta),
            "termos_ok": contem_termos(r.resposta, q["termos"]) if q["termos"] else None,
            "citou_correto": None if q["deve_recusar"] else any(trecho_correto(t.id, t.texto, q) for t in citados),
            "segundos": segundos,
        })
        salvar_json(caminho_parcial, {"assinatura": assinatura, "linhas": linhas})
        time.sleep(DELAY_ENTRE_PERGUNTAS)
    return linhas


def por_categoria(linhas: List[dict]) -> Dict[str, Dict[str, float]]:
    grupos = collections.defaultdict(list)
    for l in linhas:
        grupos[l["categoria"]].append(l["posicao"])
    return {c: resumir_posicoes(p) for c, p in sorted(grupos.items())}


def resumir_geracao(linhas: List[dict]) -> Dict[str, float]:
    recusar = [l for l in linhas if l["deve_recusar"]]
    responder_ = [l for l in linhas if not l["deve_recusar"]]

    def taxa(grupo: List[dict], chave: str) -> Optional[float]:
        """Fração do grupo com a chave verdadeira; None se o grupo for vazio."""
        return sum(bool(l.get(chave)) for l in grupo) / len(grupo) if grupo else None

    return {
        "llm": sorted({l["llm"] for l in linhas}),
        "abstencao_correta": taxa(recusar, "recusou"),
        "recusa_indevida": taxa(responder_, "recusou"),
        "termos_presentes": taxa(responder_, "termos_ok"),
        "citou_trecho_correto": taxa(responder_, "citou_correto"),
        "segundos_por_resposta": round(sum(l.get("segundos", 0) for l in linhas) / len(linhas), 1) if linhas else None,
    }


def formatar(valor: Optional[float]) -> str:
    return "sem perguntas" if valor is None else f"{valor:.3f}"


def linha_tabela(nome: str, m: Dict[str, float]) -> str:
    valores = " | ".join(f"{m[f'hit@{k}']:.3f}" for k in KS)
    return f"| {nome} | {m['n']} | {valores} | {m['mrr']:.3f} |"


def descrever_reranker() -> str:
    if config.RERANKER == "nenhum":
        return "nenhum"
    return f"{config.RERANKER}/{config.COHERE_RERANK_MODELO}, {config.RERANK_CANDIDATOS} candidatos"


def carregar_cache_rerank(caminho: str) -> None:
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            nucleo.CACHE_RERANK.update(json.load(f))


def salvar_cache_rerank(caminho: str) -> None:
    if nucleo.CACHE_RERANK:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        salvar_json(caminho, nucleo.CACHE_RERANK)


def escrever_relatorio(caminho: str, dados: dict) -> None:
    cab = "| Grupo | n | " + " | ".join(f"hit@{k}" for k in KS) + " | MRR |"
    sep = "|---|---|" + "---|" * (len(KS) + 1)
    m = [f"# Resultados: {dados['rotulo']}", "",
         f"Executado em {dados['executado_em']}. Conjunto: `{dados['conjunto']}`.",
         f"Busca: `{config.MODO_BUSCA}`. Embedding: `{config.MODELO_EMBEDDING}`. "
         f"Chunks recuperados pelo sistema: {config.TOP_K}. Política de revogados: `{config.POLITICA_REVOGADOS}`. Reranker: `{descrever_reranker()}`.", ""]
    for chave, titulo in (("politica", "Recuperação com a política de revogados do sistema"),
                          ("com_filtro", "Recuperação excluindo revogados"),
                          ("sem_filtro", "Recuperação incluindo revogados")):
        if chave not in dados["recuperacao"]:
            continue  # resultados antigos não têm o bloco da política
        bloco = dados["recuperacao"][chave]
        m += [f"## {titulo}", "", cab, sep, linha_tabela("Todas com documento esperado", bloco["geral"])]
        m += [linha_tabela(c, v) for c, v in bloco["categorias"].items()] + [""]
        if "contexto" in bloco:
            c = bloco["contexto"]
            m += [f"Expansão de contexto: `{config.EXPANSAO_CONTEXTO}`. Resposta presente no contexto enviado ao LLM: "
                  f"{c['com_resposta']} de {c['n']}. Tamanho médio do contexto: {c['chars_medio']} caracteres.", ""]
    if "geracao" in dados:
        g = dados["geracao"]["resumo"]
        m += ["## Geração", "", f"LLM: `{', '.join(g['llm'])}`.", "",
              "| Métrica | Valor |", "|---|---|",
              f"| Abstenção correta (deve recusar) | {formatar(g['abstencao_correta'])} |",
              f"| Recusa indevida (deve responder) | {formatar(g['recusa_indevida'])} |",
              f"| Termos esperados presentes | {formatar(g['termos_presentes'])} |",
              f"| Citou um trecho correto | {formatar(g.get('citou_trecho_correto'))} |",
              f"| Segundos por resposta (média) | {g.get('segundos_por_resposta')} |", ""]
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(m))


def main() -> None:
    parser = argparse.ArgumentParser(description="Mede o RAG no conjunto de ouro.")
    parser.add_argument("--conjunto", default=os.path.join(config.PASTA_DOCS_AVALIACAO, "conjunto_ouro.json"))
    parser.add_argument("--saida", default=config.PASTA_DOCS_AVALIACAO)
    parser.add_argument("--rotulo", default="baseline")
    parser.add_argument("--com-llm", action="store_true", help="Também gera respostas (consome cota).")
    parser.add_argument("--so-politica", action="store_true",
                        help="Mede só a recuperação com a política do sistema (menos chamadas ao reranker).")
    args = parser.parse_args()

    with open(args.conjunto, encoding="utf-8") as f:
        perguntas = json.load(f)["perguntas"]
    colecao, modelo = carregar_recursos()
    carregar_cache_rerank(CACHE_RERANK)

    # Perguntas de recusa não têm documento nem evidência esperados, então não entram em hit@k
    com_alvo = [q for q in perguntas if q["documentos_esperados"] or q.get("evidencia")]
    dados = {
        "rotulo": args.rotulo,
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "conjunto": os.path.basename(args.conjunto),
        "reranker": descrever_reranker(),
        "recuperacao": {},
    }
    blocos = [("politica", None), ("com_filtro", config.FILTRO_SEM_REVOGADOS), ("sem_filtro", None)]
    for nome, filtro in blocos[:1] if args.so_politica else blocos:
        linhas = medir_recuperacao(com_alvo, colecao, modelo, filtro, usar_politica=(nome == "politica"))
        dados["recuperacao"][nome] = {
            "geral": resumir_posicoes([l["posicao"] for l in linhas]),
            "categorias": por_categoria(linhas),
            "detalhe": linhas,
        }
        if nome == "politica":
            com_termos = [l for l, q in zip(linhas, com_alvo) if q["termos"] or q.get("evidencia")]
            dados["recuperacao"][nome]["contexto"] = {
                "expansao": config.EXPANSAO_CONTEXTO,
                "n": len(com_termos),
                "com_resposta": sum(l["resposta_no_contexto"] for l in com_termos),
                "chars_medio": round(sum(l["chars_contexto"] for l in com_termos) / max(1, len(com_termos))),
            }
    os.makedirs(args.saida, exist_ok=True)
    caminho_parcial = os.path.join(args.saida, f"{args.rotulo}.parcial.json")
    if args.com_llm:
        # identifica a configuração, para não misturar respostas de rodadas diferentes
        assinatura = {
            "conjunto": dados["conjunto"],
            "modo_busca": config.MODO_BUSCA,
            "politica_revogados": config.POLITICA_REVOGADOS,
            "expansao_contexto": config.EXPANSAO_CONTEXTO,
            "reranker": descrever_reranker(),
            "top_k": config.TOP_K,
            "llm": config.LLM_AVALIACAO,
            "modelo_llm": nome_do_modelo(config.LLM_AVALIACAO),
        }
        linhas = medir_geracao(perguntas, colecao, modelo, caminho_parcial, assinatura)
        dados["geracao"] = {"resumo": resumir_geracao(linhas), "detalhe": linhas}

    salvar_cache_rerank(CACHE_RERANK)
    if nucleo.FALHAS_RERANK:
        dados["falhas_rerank"] = nucleo.FALHAS_RERANK
        print(f"[AVISO] O reranker falhou {len(nucleo.FALHAS_RERANK)} vezes; essas perguntas ficaram na ordem da busca.")
    salvar_json(os.path.join(args.saida, f"{args.rotulo}.json"), dados)
    escrever_relatorio(os.path.join(args.saida, f"{args.rotulo}.md"), dados)
    if os.path.exists(caminho_parcial):
        os.remove(caminho_parcial)
    print(f"Resultados salvos em {args.saida} ({args.rotulo}.json e {args.rotulo}.md)")


if __name__ == "__main__":
    main()
