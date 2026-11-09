"""
Cria uma cópia do índice sem os chunks de páginas de bloqueio.

O índice de origem nunca é alterado. A cópia é compactada no final, para que o
texto apagado não continue dentro do arquivo, e depois verificada byte a byte.

Uso: python scripts/limpar_indice.py --destino vectorstore_limpo
"""

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys

import config
from validacao import MARCAS_BLOQUEIO

LOTE = 500  # ids apagados por chamada ao ChromaDB


def caminho_sqlite(pasta: str) -> str:
    return os.path.join(pasta, "chroma.sqlite3")


def ids_de_bloqueio(pasta: str) -> list:
    """Ids dos chunks cujo texto contém alguma marca de página de bloqueio."""
    condicao = " or ".join("instr(m.string_value, ?) > 0" for _ in MARCAS_BLOQUEIO)
    db = sqlite3.connect(caminho_sqlite(pasta))
    linhas = db.execute(
        "select e.embedding_id from embeddings e join embedding_metadata m on m.id = e.id "
        f"where m.key = 'chroma:document' and ({condicao})",
        MARCAS_BLOQUEIO,
    ).fetchall()
    db.close()
    return [l[0] for l in linhas]


def apagar_chunks(pasta: str) -> None:
    """Apaga os chunks de bloqueio pela API do ChromaDB (texto, metadata e vetor)."""
    import chromadb

    ids = ids_de_bloqueio(pasta)
    documentos = {re.sub(r"_chunk\d+$", "", i) for i in ids}
    colecao = chromadb.PersistentClient(path=pasta).get_collection(config.NOME_COLECAO)
    antes = colecao.count()
    for inicio in range(0, len(ids), LOTE):
        colecao.delete(ids=ids[inicio:inicio + LOTE])
    print(f"chunks apagados: {len(ids)} | documentos afetados: {len(documentos)}")
    print(f"total antes: {antes} | total depois: {colecao.count()}")


def compactar(pasta: str) -> None:
    """Reescreve o arquivo SQLite, eliminando o conteúdo das linhas apagadas."""
    db = sqlite3.connect(caminho_sqlite(pasta))
    db.execute("vacuum")
    db.execute("pragma wal_checkpoint(truncate)")
    db.close()


def contar_residuos(pasta: str) -> int:
    """Procura as marcas de bloqueio nos bytes de todos os arquivos da cópia."""
    marcas = [m.encode("utf-8") for m in MARCAS_BLOQUEIO] + [b"Your IP"]
    sobra = max(len(m) for m in marcas)
    achados = 0
    for raiz, _, arquivos in os.walk(pasta):
        for nome in arquivos:
            anterior = b""
            with open(os.path.join(raiz, nome), "rb") as f:
                while bloco := f.read(64 * 1024 * 1024):
                    dados = anterior + bloco
                    achados += sum(dados.count(m) for m in marcas)
                    anterior = bloco[-sobra:]
    return achados


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera uma cópia limpa do índice.")
    parser.add_argument("--origem", default=config.PASTA_VECTORSTORE)
    parser.add_argument("--destino", required=True)
    parser.add_argument("--so-apagar", action="store_true", help="Uso interno.")
    args = parser.parse_args()

    if args.so_apagar:
        apagar_chunks(args.destino)
        return

    if os.path.exists(args.destino):
        raise SystemExit(f"[ERRO] O destino ja existe: {args.destino}")
    print(f"Copiando {args.origem} para {args.destino} ...")
    shutil.copytree(args.origem, args.destino)

    # Em outro processo, para o ChromaDB soltar o arquivo antes da compactação
    subprocess.run([sys.executable, __file__, "--destino", args.destino, "--so-apagar"], check=True)

    print("Compactando ...")
    compactar(args.destino)
    residuos = contar_residuos(args.destino)
    print(f"marcas de bloqueio restantes nos arquivos: {residuos}")
    if residuos:
        raise SystemExit("[ERRO] A copia ainda contem texto de paginas de bloqueio.")
    print(f"[OK] Indice limpo em: {args.destino}")


if __name__ == "__main__":
    main()
