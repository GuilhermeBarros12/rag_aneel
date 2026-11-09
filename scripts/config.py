"""
Configuração única do projeto.

Tudo que precisa ser igual entre indexação, pipeline e avaliação fica aqui:
caminhos, parâmetros de chunking, modelos, top_k, filtro e prompt.
Valores marcados com os.getenv podem ser sobrescritos no .env.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

# ============================================================
# CAMINHOS
# ============================================================

PASTA_JSONS       = str(ROOT / "dados" / "jsons")
PASTA_PDFS        = str(ROOT / "dados" / "pdfs")
PASTA_EXTRAS      = str(ROOT / "dados" / "extras")
PASTA_MARKDOWNS   = str(ROOT / "chunks_md")
PASTA_CHUNKS      = str(ROOT / "chunks")
# Podem apontar para uma cópia, para testar sem tocar no índice original
PASTA_VECTORSTORE = os.getenv("VECTORSTORE_DIR", str(ROOT / "vectorstore"))
PASTA_RESULTADOS  = os.getenv("RESULTADOS_DIR", str(ROOT / "avaliacao"))
PASTA_DOCS_AVALIACAO = str(ROOT / "docs" / "avaliacao")  # resultados versionados

# ============================================================
# CHUNKING
# ============================================================

CHUNK_SIZE    = 512  # tamanho máximo de cada chunk em caracteres (tabelas podem passar disso)
CHUNK_OVERLAP = 80   # caracteres de sobreposição entre chunks consecutivos
MIN_CHARS     = 50   # chunks menores que isso são descartados (ruído)
SEPARADORES   = ["\n\n", "\n", ". ", " ", ""]  # do mais semântico ao mais bruto

# ============================================================
# EMBEDDINGS E ÍNDICE
# ============================================================

# Mesmo modelo na indexação e na consulta. Trocar exige reindexar.
MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
NOME_COLECAO     = "aneel_docs"
BATCH_SIZE       = 64  # chunks por lote de embedding; reduza para 32 se faltar RAM

# Repositório público no Hugging Face com o índice pré-construído
HF_REPO_ID = os.getenv("HF_REPO_ID") or "guilhermebarros/rag-aneel-vectorstore"

# ============================================================
# RETRIEVER
# ============================================================

TOP_K = int(os.getenv("TOP_K", "5"))

# Decisão de projeto atual: atos com situação REVOGADA não são recuperados.
# Consequência: perguntas sobre atos revogados ficam sem resposta.
FILTRO_PADRAO = {"situacao": {"$ne": "Situação:REVOGADA"}}

# ============================================================
# GERAÇÃO
# ============================================================

GEMINI_MODELO = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODELO   = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TEMPERATURA   = 0.0  # respostas o mais repetíveis possível, nos dois LLMs
TIMEOUT_LLM_S = 60   # espera máxima por LLM antes de seguir para o fallback

# A medição usa um único LLM, sem fallback, para os números não misturarem modelos
LLM_AVALIACAO = os.getenv("LLM_AVALIACAO", "groq")

PROMPT_TEMPLATE = """Você é um assistente especializado em regulação do setor elétrico brasileiro.
Responda à pergunta usando APENAS as informações dos trechos regulatórios abaixo.
Se a resposta não estiver nos trechos, responda: "Não encontrei informação suficiente nos documentos disponíveis."
Seja objetivo e sempre cite a fonte da sua resposta usando a marcação fornecida (ex: 'De acordo com o [Trecho 1]...').

--- TRECHOS RECUPERADOS ---
{contexto}
--- FIM DOS TRECHOS ---

Pergunta: {query}

Resposta:"""
