import os
from dotenv import load_dotenv
from huggingface_hub import HfApi

# Carrega HF_TOKEN e HF_REPO_ID do .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

HF_TOKEN   = os.getenv("HF_TOKEN", "")
HF_REPO_ID = os.getenv("HF_REPO_ID", "")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN nao configurado no .env — crie em https://huggingface.co/settings/tokens")

if not HF_REPO_ID:
    raise ValueError("HF_REPO_ID nao configurado no .env — ex: seu-usuario/aneel-vectorstore")

api = HfApi(token=HF_TOKEN)

print(f"Enviando vectorstore para: {HF_REPO_ID}")

api.upload_folder(
    folder_path="../vectorstore",
    repo_id=HF_REPO_ID,
    repo_type="dataset",
)

print("✅ Vectorstore enviado com sucesso!")