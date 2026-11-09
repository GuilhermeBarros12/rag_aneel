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
from nucleo import carregar_recursos, recuperar_trechos, responder

KS = (1, 3, 5, 10)
FRASE_RECUSA = "nao encontrei informacao suficiente"
DELAY_ENTRE_PERGUNTAS = 2  # segundos, para evitar rate limit

# ============================================================
# MÉTRICAS (funções puras, sem índice nem rede)
# ============================================================


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e com espaços simples, para comparar textos."""
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


def medir_recuperacao(perguntas: List[dict], colecao, modelo, filtro) -> List[dict]:
    linhas = []
    for q in perguntas:
        trechos = recuperar_trechos(q["pergunta"], colecao, modelo, top_k=max(KS), filtro=filtro)
        ids = [t.id for t in trechos]
        linhas.append({
            "id": q["id"],
            "categoria": q["categoria"],
            "posicao": posicao_primeiro_acerto(ids, q["documentos_esperados"]),
            "top3": ids[:3],
        })
    return linhas


def medir_geracao(perguntas: List[dict], colecao, modelo) -> List[dict]:
    """Usa um único LLM, para os números não misturarem modelos."""
    linhas = []
    for i, q in enumerate(perguntas, 1):
        print(f"[{i}/{len(perguntas)}] {q['pergunta'][:70]}")
        r = responder(q["pergunta"], colecao, modelo, provedores=[config.LLM_AVALIACAO])
        if r.llm is None:
            raise SystemExit(f"[ERRO] Medicao interrompida: {r.resposta}")
        linhas.append({
            "id": q["id"],
            "categoria": q["categoria"],
            "deve_recusar": q["deve_recusar"],
            "llm": r.llm,
            "resposta": r.resposta,
            "recusou": recusou(r.resposta),
            "termos_ok": contem_termos(r.resposta, q["termos"]) if q["termos"] else None,
        })
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
    return {
        "llm": sorted({l["llm"] for l in linhas}),
        "abstencao_correta": sum(l["recusou"] for l in recusar) / len(recusar),
        "recusa_indevida": sum(l["recusou"] for l in responder_) / len(responder_),
        "termos_presentes": sum(bool(l["termos_ok"]) for l in responder_) / len(responder_),
    }


def linha_tabela(nome: str, m: Dict[str, float]) -> str:
    valores = " | ".join(f"{m[f'hit@{k}']:.3f}" for k in KS)
    return f"| {nome} | {m['n']} | {valores} | {m['mrr']:.3f} |"


def escrever_relatorio(caminho: str, dados: dict) -> None:
    cab = "| Grupo | n | " + " | ".join(f"hit@{k}" for k in KS) + " | MRR |"
    sep = "|---|---|" + "---|" * (len(KS) + 1)
    m = [f"# Resultados: {dados['rotulo']}", "",
         f"Executado em {dados['executado_em']}. Conjunto: `{dados['conjunto']}`.",
         f"Embedding: `{config.MODELO_EMBEDDING}`. Chunks recuperados pelo sistema: {config.TOP_K}.", ""]
    for chave, titulo in (("com_filtro", "Recuperação do sistema entregue (exclui revogados)"),
                          ("sem_filtro", "Recuperação sem o filtro de revogados")):
        bloco = dados["recuperacao"][chave]
        m += [f"## {titulo}", "", cab, sep, linha_tabela("Todas com documento esperado", bloco["geral"])]
        m += [linha_tabela(c, v) for c, v in bloco["categorias"].items()] + [""]
    if "geracao" in dados:
        g = dados["geracao"]["resumo"]
        m += ["## Geração", "", f"LLM: `{', '.join(g['llm'])}`.", "",
              "| Métrica | Valor |", "|---|---|",
              f"| Abstenção correta (deve recusar) | {g['abstencao_correta']:.3f} |",
              f"| Recusa indevida (deve responder) | {g['recusa_indevida']:.3f} |",
              f"| Termos esperados presentes | {g['termos_presentes']:.3f} |", ""]
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(m))


def main() -> None:
    parser = argparse.ArgumentParser(description="Mede o RAG no conjunto de ouro.")
    parser.add_argument("--conjunto", default=os.path.join(config.PASTA_DOCS_AVALIACAO, "conjunto_ouro.json"))
    parser.add_argument("--saida", default=config.PASTA_DOCS_AVALIACAO)
    parser.add_argument("--rotulo", default="baseline")
    parser.add_argument("--com-llm", action="store_true", help="Também gera respostas (consome cota).")
    args = parser.parse_args()

    with open(args.conjunto, encoding="utf-8") as f:
        perguntas = json.load(f)["perguntas"]
    colecao, modelo = carregar_recursos()

    # Perguntas de recusa não têm documento esperado, então não entram em hit@k
    com_alvo = [q for q in perguntas if q["documentos_esperados"]]
    dados = {
        "rotulo": args.rotulo,
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "conjunto": os.path.basename(args.conjunto),
        "recuperacao": {},
    }
    for nome, filtro in (("com_filtro", config.FILTRO_PADRAO), ("sem_filtro", None)):
        linhas = medir_recuperacao(com_alvo, colecao, modelo, filtro)
        dados["recuperacao"][nome] = {
            "geral": resumir_posicoes([l["posicao"] for l in linhas]),
            "categorias": por_categoria(linhas),
            "detalhe": linhas,
        }
    if args.com_llm:
        linhas = medir_geracao(perguntas, colecao, modelo)
        dados["geracao"] = {"resumo": resumir_geracao(linhas), "detalhe": linhas}

    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, f"{args.rotulo}.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
    escrever_relatorio(os.path.join(args.saida, f"{args.rotulo}.md"), dados)
    print(f"Resultados salvos em {args.saida} ({args.rotulo}.json e {args.rotulo}.md)")


if __name__ == "__main__":
    main()
