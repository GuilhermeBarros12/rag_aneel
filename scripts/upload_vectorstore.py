import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

# 1. BOAS PRÁTICAS: Descobre o caminho absoluto do projeto para não errar a pasta
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_RAIZ = os.path.dirname(DIRETORIO_ATUAL)
PASTA_VECTORSTORE = os.path.join(DIRETORIO_RAIZ, "vectorstore")
CAMINHO_ENV = os.path.join(DIRETORIO_RAIZ, ".env")

# Carrega as variáveis do .env
load_dotenv(dotenv_path=CAMINHO_ENV)

# 2. SEGURANÇA: Nunca coloque o token de fallback no código! Se não achar no .env, tem que quebrar.
HF_TOKEN   = os.getenv("HF_TOKEN")
HF_REPO_ID = os.getenv("HF_REPO_ID")

if not HF_TOKEN:
    raise ValueError("❌ HF_TOKEN não configurado no arquivo .env!")
if not HF_REPO_ID:
    raise ValueError("❌ HF_REPO_ID não configurado no arquivo .env!")

if not os.path.exists(PASTA_VECTORSTORE):
    raise FileNotFoundError(f"❌ Pasta não encontrada: {PASTA_VECTORSTORE}")

print(f"Iniciando conexão com Hugging Face...")
api = HfApi(token=HF_TOKEN)

print(f"Preparando upload da pasta: {PASTA_VECTORSTORE}")
print(f"Destino: {HF_REPO_ID}")
print("Atenção: O upload de ~3GB pode levar bastante tempo e parecer 'parado'. Aguarde...")

# 3. A CORREÇÃO: ignorar arquivos temporários que travam o upload
api.upload_folder(
    folder_path=PASTA_VECTORSTORE,
    repo_id=HF_REPO_ID,
    repo_type="dataset",
    ignore_patterns=["*.journal", "*.wal", "*.shm", ".DS_Store"] # O Segredo está aqui!
)

print("✅ Vectorstore enviado com sucesso!")