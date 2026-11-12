"""
Reindexa só alguns documentos, sem refazer o corpus inteiro.

Faz, para cada documento, o mesmo caminho dos scripts do pipeline:
ingestão (PDF ou HTML para Markdown), chunking e embedding. Depois apaga os
chunks antigos do documento no ChromaDB e grava os novos.

Uso:
    python scripts/atualizar_documentos.py ren2016756 ren2016699 ...
    python scripts/atualizar_documentos.py --normas-bloqueadas

Use VECTORSTORE_DIR para escolher o índice. Depois, recrie o acervo léxico:
    python scripts/lexico.py
"""

import argparse
import json
import os
import time

import chunking
import config
import indexar
import ingestao
from validacao import eh_pagina_de_bloqueio


def registros_por_arquivo() -> dict:
    """Mapa 'ren2016756.pdf' -> (registro do JSON, tipo do arquivo)."""
    mapa = {}
    for nome in sorted(os.listdir(config.PASTA_JSONS)):
        if not nome.endswith(".json"):
            continue
        with open(os.path.join(config.PASTA_JSONS, nome), encoding="utf-8") as f:
            dados = json.load(f)
        for conteudo in dados.values():
            for registro in conteudo.get("registros", []):
                for item in registro.get("pdfs", []):
                    arquivo = (item.get("arquivo") or "").strip()
                    if arquivo:
                        mapa.setdefault(arquivo.lower(), (registro, item.get("tipo", ""), arquivo))
    return mapa


def normas_bloqueadas() -> list:
    """Documentos cujo HTML é página de bloqueio e que têm um PDF de mesmo nome."""
    bases = []
    for nome in sorted(os.listdir(config.PASTA_EXTRAS)):
        base, ext = os.path.splitext(nome)
        if ext.lower() not in {".html", ".htm"}:
            continue
        with open(os.path.join(config.PASTA_EXTRAS, nome), encoding="utf-8", errors="ignore") as f:
            if eh_pagina_de_bloqueio(f.read()) and os.path.exists(os.path.join(config.PASTA_PDFS, base + ".pdf")):
                bases.append(base)
    return bases


def chunks_do_documento(base: str, mapa: dict):
    """Devolve (ids, textos, metadatas) do documento, como o pipeline completo geraria."""
    for ext, pasta, extrator in ((".pdf", config.PASTA_PDFS, ingestao.extrair_pdf_para_markdown),
                                 (".html", config.PASTA_EXTRAS, ingestao.extrair_html_para_markdown)):
        arquivo = base + ext
        if arquivo.lower() in mapa and os.path.exists(os.path.join(pasta, arquivo)):
            registro, tipo, nome_original = mapa[arquivo.lower()]
            conteudo = extrator(os.path.join(pasta, nome_original))
            if conteudo:
                break
    else:
        return [], [], []

    markdown = ingestao.montar_metadata(registro, nome_original, tipo) + conteudo
    metadata = chunking.extrair_metadata_do_header(markdown)
    pedacos = chunking.chunkar_documento(chunking.extrair_texto_sem_header(markdown))

    ids, textos, metadatas = [], [], []
    for n, pedaco in enumerate(pedacos, 1):
        # mesmo formato que o chunking grava em disco e a indexação lê
        arquivo_chunk = chunking.montar_cabecalho_chunk(metadata, n, len(pedacos)) + pedaco
        meta, texto = indexar.extrair_metadata_e_texto(arquivo_chunk)
        if texto:
            ids.append(f"{base}_chunk{n}")
            textos.append(texto)
            metadatas.append(indexar.limpar_metadata_para_chroma(meta))
    return ids, textos, metadatas


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindexa só os documentos indicados.")
    parser.add_argument("documentos", nargs="*", help="Nomes sem extensão, como ren2016756")
    parser.add_argument("--normas-bloqueadas", action="store_true",
                        help="Reindexa as normas cujo HTML era página de bloqueio")
    args = parser.parse_args()

    bases = list(args.documentos) + (normas_bloqueadas() if args.normas_bloqueadas else [])
    if not bases:
        raise SystemExit("Nenhum documento indicado.")

    import chromadb
    from sentence_transformers import SentenceTransformer

    print(f"Indice: {config.PASTA_VECTORSTORE} | documentos: {len(bases)}")
    colecao = chromadb.PersistentClient(path=config.PASTA_VECTORSTORE).get_collection(config.NOME_COLECAO)
    modelo = SentenceTransformer(config.MODELO_EMBEDDING)
    mapa = registros_por_arquivo()
    antes = colecao.count()

    inicio, gravados, sem_texto = time.time(), 0, []
    for i, base in enumerate(bases, 1):
        ids, textos, metadatas = chunks_do_documento(base, mapa)
        if not ids:
            sem_texto.append(base)
            continue
        # apaga os chunks antigos do documento, que podem ser mais numerosos que os novos
        antigos = colecao.get(where={"arquivo_original": {"$in": [base + ".html", base + ".htm", base + ".pdf"]}},
                              include=[])["ids"]
        antigos = [a for a in antigos if a.rsplit("_chunk", 1)[0] == base]
        if antigos:
            colecao.delete(ids=antigos)
        embeddings = modelo.encode(textos, batch_size=config.BATCH_SIZE, show_progress_bar=False).tolist()
        colecao.upsert(ids=ids, documents=textos, embeddings=embeddings, metadatas=metadatas)
        gravados += len(ids)
        if i % 10 == 0 or i == len(bases):
            print(f"   {i}/{len(bases)} documentos | {gravados} chunks | {time.time() - inicio:.0f}s", flush=True)

    print(f"[OK] chunks antes: {antes} | depois: {colecao.count()} | gravados: {gravados}")
    if sem_texto:
        print(f"[AVISO] sem texto extraido: {sem_texto}")
    print("Recrie o acervo lexico: python scripts/lexico.py")


if __name__ == "__main__":
    main()
