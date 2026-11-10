"""
Envia o índice para o Hugging Face Hub.

Sem argumentos, envia a pasta do índice vetorial (cerca de 4,4 GB).
Com --acervo, envia só o acervo léxico (cerca de 0,6 GB), que basta para o modo
de busca "lexica".

Requer HF_TOKEN com permissão de escrita no .env.
"""

import argparse
import os

from huggingface_hub import HfApi

import lexico
from config import ARQUIVO_LEXICO, HF_REPO_ID, PASTA_VECTORSTORE  # config.py também carrega o .env


def main() -> None:
    parser = argparse.ArgumentParser(description="Envia o índice para o Hugging Face Hub.")
    parser.add_argument("--acervo", action="store_true", help="Envia só o acervo léxico.")
    args = parser.parse_args()

    # Nunca coloque o token de fallback no código! Se não achar no .env, tem que quebrar.
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError("❌ HF_TOKEN (tipo Write) não configurado no arquivo .env!")
    api = HfApi(token=token)
    print(f"Destino: {HF_REPO_ID}")

    if args.acervo:
        if not lexico.existe():
            raise FileNotFoundError("❌ Acervo léxico não encontrado. Rode: python scripts/lexico.py")
        lexico.fechar()
        print(f"Enviando o acervo léxico: {lexico.caminho()}")
        api.upload_file(
            path_or_fileobj=lexico.caminho(),
            path_in_repo=ARQUIVO_LEXICO,
            repo_id=HF_REPO_ID,
            repo_type="dataset",
        )
        print("✅ Acervo léxico enviado com sucesso!")
        return

    if not os.path.exists(PASTA_VECTORSTORE):
        raise FileNotFoundError(f"❌ Pasta não encontrada: {PASTA_VECTORSTORE}")
    print(f"Enviando a pasta: {PASTA_VECTORSTORE}")
    print("Atenção: O upload de ~4,4 GB pode levar bastante tempo e parecer 'parado'. Aguarde...")
    # ignora arquivos temporários do SQLite, que travam o upload
    api.upload_folder(
        folder_path=PASTA_VECTORSTORE,
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        ignore_patterns=["*.journal", "*.wal", "*.shm", ".DS_Store"],
    )
    print("✅ Vectorstore enviado com sucesso!")


if __name__ == "__main__":
    main()
