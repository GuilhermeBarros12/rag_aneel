import os
from huggingface_hub import HfApi

from config import HF_REPO_ID, PASTA_VECTORSTORE  # config.py também carrega o .env

# Nunca coloque o token de fallback no código! Se não achar no .env, tem que quebrar.
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("❌ HF_TOKEN (tipo Write) não configurado no arquivo .env!")

if not os.path.exists(PASTA_VECTORSTORE):
    raise FileNotFoundError(f"❌ Pasta não encontrada: {PASTA_VECTORSTORE}")

print(f"Iniciando conexão com Hugging Face...")
api = HfApi(token=HF_TOKEN)

print(f"Preparando upload da pasta: {PASTA_VECTORSTORE}")
print(f"Destino: {HF_REPO_ID}")
print("Atenção: O upload de ~4,4 GB pode levar bastante tempo e parecer 'parado'. Aguarde...")

# 3. A CORREÇÃO: ignorar arquivos temporários que travam o upload
api.upload_folder(
    folder_path=PASTA_VECTORSTORE,
    repo_id=HF_REPO_ID,
    repo_type="dataset",
    ignore_patterns=["*.journal", "*.wal", "*.shm", ".DS_Store"] # O Segredo está aqui!
)

print("✅ Vectorstore enviado com sucesso!")