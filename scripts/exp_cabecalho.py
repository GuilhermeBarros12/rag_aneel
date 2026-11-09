"""
Experimento: incluir título e ementa no texto embedado melhora a recuperação?

Roda em um subconjunto (documentos do conjunto de ouro + sorteio com semente fixa),
com busca exata, sem alterar o índice. Em corpus menor o acerto é mais fácil, então
só a diferença entre as variantes é comparável, não o valor absoluto.
"""

import json
import os
import random
import re
import time

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

import config
from avaliar_ouro import KS, documento_do_trecho, posicao_primeiro_acerto, resumir_posicoes

SEMENTE = 2027
N_DOCUMENTOS = 3000
MAX_CHUNKS_POR_DOC = 200  # documentos sorteados maiores que isso ficam de fora


def sem_prefixo(ementa):
    return "" if ementa in (None, "None") else re.sub(r"\s*Imprimir\s*$", "", ementa)


VARIANTES = {
    "somente_titulo": lambda m, t: f"{m.get('titulo', '')}\n{t}",
    "titulo_e_ementa": lambda m, t: f"{m.get('titulo', '')}. {sem_prefixo(m.get('ementa'))}\n{t}",
}


def main():
    with open(os.path.join(config.PASTA_DOCS_AVALIACAO, "conjunto_ouro.json"), encoding="utf-8") as f:
        perguntas = [q for q in json.load(f)["perguntas"] if q["documentos_esperados"]]
    obrigatorios = {d for q in perguntas for d in q["documentos_esperados"]}

    col = chromadb.PersistentClient(path=config.PASTA_VECTORSTORE).get_collection(config.NOME_COLECAO)
    ids_todos = []
    for offset in range(0, col.count(), 50000):
        ids_todos += col.get(limit=50000, offset=offset, include=[])["ids"]
    por_doc = {}
    for i in sorted(ids_todos):
        por_doc.setdefault(documento_do_trecho(i), []).append(i)

    candidatos = sorted(d for d, c in por_doc.items() if d not in obrigatorios and len(c) <= MAX_CHUNKS_POR_DOC)
    sorteados = random.Random(SEMENTE).sample(candidatos, N_DOCUMENTOS - len(obrigatorios & set(por_doc)))
    docs = sorted((obrigatorios & set(por_doc)) | set(sorteados))
    ids = [i for d in docs for i in por_doc[d]]
    print(f"documentos: {len(docs)} | chunks: {len(ids)}")

    textos, metas, base = {}, {}, {}
    for i in range(0, len(ids), 4000):
        r = col.get(ids=ids[i:i + 4000], include=["documents", "metadatas", "embeddings"])
        for k, cid in enumerate(r["ids"]):
            textos[cid], metas[cid], base[cid] = r["documents"][k], r["metadatas"][k], r["embeddings"][k]
    permitido = np.array([metas[i].get("situacao") != "Situação:REVOGADA" for i in ids])

    modelo = SentenceTransformer(config.MODELO_EMBEDDING)
    q_emb = modelo.encode([q["pergunta"] for q in perguntas], normalize_embeddings=True)

    def normaliza(m):
        return m / np.linalg.norm(m, axis=1, keepdims=True)

    def medir(emb):
        resumo = {}
        for nome, mascara in (("com_filtro", permitido), ("sem_filtro", np.ones(len(ids), bool))):
            indices = np.where(mascara)[0]
            ordem = np.argsort(-(q_emb @ emb[indices].T), axis=1)[:, :max(KS)]
            posicoes = [
                posicao_primeiro_acerto([ids[indices[j]] for j in linha], q["documentos_esperados"])
                for linha, q in zip(ordem, perguntas)
            ]
            grupos = {}
            for p, q in zip(posicoes, perguntas):
                grupos.setdefault(q["categoria"], []).append(p)
            resumo[nome] = {"geral": resumir_posicoes(posicoes),
                            "categorias": {c: resumir_posicoes(v) for c, v in sorted(grupos.items())}}
        return resumo

    saida = {"documentos": len(docs), "chunks": len(ids), "semente": SEMENTE, "variantes": {}}
    saida["variantes"]["atual"] = medir(normaliza(np.array([base[i] for i in ids])))
    for nome, montar in VARIANTES.items():
        inicio = time.time()
        emb = modelo.encode([montar(metas[i], textos[i]) for i in ids], batch_size=64,
                            normalize_embeddings=True, show_progress_bar=False)
        saida["variantes"][nome] = medir(emb)
        saida.setdefault("segundos_por_variante", {})[nome] = round(time.time() - inicio)
        print(nome, "segundos:", saida["segundos_por_variante"][nome])

    destino = os.path.join(config.PASTA_DOCS_AVALIACAO, "experimentos", "cabecalho_subconjunto.json")
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    for nome, v in saida["variantes"].items():
        g = v["com_filtro"]["geral"]
        print(nome, " ".join(f"hit@{k}={g[f'hit@{k}']:.3f}" for k in KS), f"mrr={g['mrr']:.3f}")


if __name__ == "__main__":
    main()
