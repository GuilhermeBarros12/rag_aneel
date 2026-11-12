"""
Experimento: um modelo de embedding feito para busca (multilingual-e5-base) recupera
melhor que o modelo atual (paraphrase-multilingual-mpnet-base-v2)?

Roda em um subconjunto de documentos, com busca exata, sem alterar o índice.
Compara, nas mesmas perguntas:
  - busca léxica (BM25, restrita ao subconjunto)
  - busca vetorial com o modelo atual (vetores já guardados no índice)
  - busca vetorial com o E5
  - busca híbrida: BM25 + E5, com fusão RRF

Em corpus menor o acerto é mais fácil; só a diferença entre as linhas é comparável.
"""

import argparse
import hashlib
import json
import os
import random
import time
from types import SimpleNamespace

import numpy as np

import config
import lexico
from avaliar_ouro import KS, posicao_primeiro_correto, resumir_posicoes
from nucleo import fundir_rrf

SEMENTE = 2027
MAX_CHUNKS_POR_DOC = 200
MODELO_NOVO = "intfloat/multilingual-e5-base"
LOTE = 2000  # chunks codificados por vez
# Vetores do E5 salvos por lote: se o processo cair, a próxima execução continua de onde parou
PASTA_CACHE = os.path.join(os.path.dirname(config.PASTA_LEXICO), "cache_experimentos")


def main():
    parser = argparse.ArgumentParser(description="Compara modelos de embedding em um subconjunto.")
    parser.add_argument("--conjunto", default=os.path.join(config.PASTA_DOCS_AVALIACAO, "conjunto_ouro_v2_rascunho.json"))
    parser.add_argument("--documentos", type=int, default=2000)
    parser.add_argument("--rotulo", default="embedding_e5_subconjunto")
    args = parser.parse_args()

    import chromadb
    from sentence_transformers import SentenceTransformer

    with open(args.conjunto, encoding="utf-8") as f:
        perguntas = [q for q in json.load(f)["perguntas"] if q["documentos_esperados"] or q.get("evidencia")]

    # ---- subconjunto: documentos esperados + sorteio com semente fixa ----
    col = chromadb.PersistentClient(path=config.PASTA_VECTORSTORE).get_collection(config.NOME_COLECAO)
    por_doc = {}
    for offset in range(0, col.count(), 50000):
        for i in col.get(limit=50000, offset=offset, include=[])["ids"]:
            por_doc.setdefault(lexico.documento_do_chunk(i), []).append(i)
    obrigatorios = {d for q in perguntas for d in q["documentos_esperados"]} & set(por_doc)
    candidatos = sorted(d for d, c in por_doc.items() if d not in obrigatorios and len(c) <= MAX_CHUNKS_POR_DOC)
    sorteados = random.Random(SEMENTE).sample(candidatos, max(0, args.documentos - len(obrigatorios)))
    docs = sorted(obrigatorios | set(sorteados))
    ids = [i for d in docs for i in sorted(por_doc[d])]
    no_subconjunto = set(ids)
    print(f"documentos: {len(docs)} | chunks: {len(ids)}", flush=True)

    textos, vetores_atuais = {}, {}
    for i in range(0, len(ids), 4000):
        r = col.get(ids=ids[i:i + 4000], include=["documents", "embeddings"])
        for k, cid in enumerate(r["ids"]):
            textos[cid] = r["documents"][k]
            vetores_atuais[cid] = np.asarray(r["embeddings"][k], dtype=np.float32)

    def normaliza(m):
        return m / np.linalg.norm(m, axis=1, keepdims=True)

    def ranking_vetorial(q_emb, matriz, n=50):
        ordem = np.argsort(-(q_emb @ matriz.T), axis=1)[:, :n]
        return [[ids[j] for j in linha] for linha in ordem]

    def medir(rankings):
        grupos, posicoes = {}, []
        for lista, q in zip(rankings, perguntas):
            trechos = [SimpleNamespace(id=i, texto=textos[i]) for i in lista[:max(KS)]]
            p = posicao_primeiro_correto(trechos, q)
            posicoes.append(p)
            grupos.setdefault(q["categoria"], []).append(p)
        return {"geral": resumir_posicoes(posicoes),
                "categorias": {c: resumir_posicoes(v) for c, v in sorted(grupos.items())}}

    resultados = {}

    # ---- léxica, restrita ao subconjunto ----
    lexicos = [[i for i in lexico.buscar(q["pergunta"], 5000) if i in no_subconjunto][:50] for q in perguntas]
    resultados["lexica"] = medir(lexicos)

    # ---- modelo atual: vetores já guardados ----
    atual = SentenceTransformer(config.MODELO_EMBEDDING)
    q_atual = atual.encode([q["pergunta"] for q in perguntas], normalize_embeddings=True)
    resultados["vetorial_atual"] = medir(ranking_vetorial(q_atual, normaliza(np.array([vetores_atuais[i] for i in ids]))))
    del atual

    # ---- E5: o modelo pede os prefixos "query: " e "passage: " ----
    novo = SentenceTransformer(MODELO_NOVO)
    novo.max_seq_length = 512
    os.makedirs(PASTA_CACHE, exist_ok=True)
    assinatura = hashlib.sha256((MODELO_NOVO + "|".join(ids)).encode()).hexdigest()[:12]
    inicio = time.time()
    partes = []
    for p in range(0, len(ids), LOTE):
        arquivo = os.path.join(PASTA_CACHE, f"e5_{assinatura}_{p:06d}.npy")
        if os.path.exists(arquivo):
            partes.append(np.load(arquivo))
            continue
        lote = ["passage: " + textos[i][:3000] for i in ids[p:p + LOTE]]
        vetores = novo.encode(lote, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        np.save(arquivo, vetores)
        partes.append(vetores)
        print(f"   e5: {min(p + LOTE, len(ids))}/{len(ids)} em {time.time() - inicio:.0f}s", flush=True)
    m_novo = np.vstack(partes)
    segundos_e5 = round(time.time() - inicio)
    q_novo = novo.encode(["query: " + q["pergunta"] for q in perguntas], normalize_embeddings=True)
    densos_novo = ranking_vetorial(q_novo, m_novo)
    resultados["vetorial_e5"] = medir(densos_novo)

    # ---- híbrida: BM25 + E5 ----
    resultados["hibrida_e5"] = medir([fundir_rrf([d, l], [1.0, 1.0]) for d, l in zip(densos_novo, lexicos)])

    saida = {"modelo_novo": MODELO_NOVO, "documentos": len(docs), "chunks": len(ids), "semente": SEMENTE,
             "conjunto": os.path.basename(args.conjunto), "segundos_embedding_e5": segundos_e5, "resultados": resultados}
    destino = os.path.join(config.PASTA_DOCS_AVALIACAO, "experimentos", args.rotulo + ".json")
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    for nome, r in resultados.items():
        g = r["geral"]
        print(f"{nome:16} hit@1={g['hit@1']:.3f} hit@5={g['hit@5']:.3f} hit@10={g['hit@10']:.3f} mrr={g['mrr']:.3f}")
    print("tempo do E5 no subconjunto:", segundos_e5, "s")


if __name__ == "__main__":
    main()
