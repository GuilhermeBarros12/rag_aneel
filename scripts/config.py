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
PASTA_LEXICO      = os.getenv("LEXICO_DIR", str(ROOT / "vectorstore_lexico"))
ARQUIVO_LEXICO    = "lexico.sqlite3"  # textos, metadata e índice BM25 em um arquivo só
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

FILTRO_SEM_REVOGADOS = {"situacao": {"$ne": "Situação:REVOGADA"}}

# Com "1", atos revogados podem ser recuperados, e o prompt pede para avisar a situação
INCLUIR_REVOGADOS = os.getenv("INCLUIR_REVOGADOS", "0") == "1"
FILTRO_PADRAO = None if INCLUIR_REVOGADOS else FILTRO_SEM_REVOGADOS

# "densa" usa só embeddings; "hibrida" funde embeddings e BM25; "lexica" usa só BM25
MODO_BUSCA = os.getenv("MODO_BUSCA", "lexica")
CANDIDATOS_FUSAO = 50  # quantos resultados de cada busca entram na fusão
RRF_K = 60             # constante padrão da Reciprocal Rank Fusion
PESO_LEXICO = float(os.getenv("PESO_LEXICO", "1"))  # peso do BM25 na fusão (embeddings = 1)
# Peso de cada coluna no BM25: título, ementa e texto do chunk
PESOS_BM25 = tuple(float(p) for p in os.getenv("PESOS_BM25", "1,1,1").split(","))

# ============================================================
# GERAÇÃO
# ============================================================

GEMINI_MODELO = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODELO   = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
TEMPERATURA   = 0.0  # respostas o mais repetíveis possível, nos dois LLMs
MAX_CHARS_TRECHO = 4000  # corta chunks de tabela muito longos ao montar o prompt
TIMEOUT_LLM_S = 60  # espera máxima por LLM antes de seguir para o fallback
TENTATIVAS_LLM = 2  # vezes que cada LLM é tentado quando o erro é temporário (ex.: 503)
ESPERA_ENTRE_TENTATIVAS_S = 5

# Valor do campo "llm" quando a resposta não precisou de LLM (ex.: a busca não achou nada)
SEM_LLM = "sem-llm"
RESPOSTA_SEM_TRECHOS = (
    "Não encontrei informação suficiente nos documentos disponíveis. "
    "A busca não devolveu nenhum trecho para essa pergunta. "
    "Tente citar o número do ato, o nome da empresa ou o tema."
)

# A medição usa um único LLM, sem fallback, para os números não misturarem modelos
LLM_AVALIACAO = os.getenv("LLM_AVALIACAO", "groq")

PROMPT_TEMPLATE = """Você é um assistente especializado em regulação do setor elétrico brasileiro.
Responda à pergunta usando APENAS as informações dos trechos regulatórios abaixo.
Se a resposta não estiver nos trechos, responda: "Não encontrei informação suficiente nos documentos disponíveis."
Seja objetivo e cite o documento de cada informação pelo título e pela marcação do trecho (ex: 'DSP - DESPACHO 3386/2016 [Trecho 1]').
Se o documento citado tiver situação REVOGADA, ANULADA, SUSPENSA ou outra que indique perda de vigência, avise isso na resposta.

--- TRECHOS RECUPERADOS ---
{contexto}
--- FIM DOS TRECHOS ---

Pergunta: {query}

Resposta:"""
