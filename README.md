# RAG ANEEL — Sistema de Perguntas e Respostas sobre Documentos Regulatórios

Sistema de **Retrieval-Augmented Generation (RAG)** desenvolvido para responder perguntas sobre o corpus regulatório da ANEEL (Agência Nacional de Energia Elétrica), composto por mais de **26.000 documentos** — resoluções normativas, despachos, notas técnicas e portarias.

---

## Arquitetura do Pipeline

```
Documentos ANEEL (PDFs, HTMLs, XLSXs)
          │
          ▼
   [1] downloads.py          → baixa os arquivos da ANEEL
          │
          ▼
   [2] ingestao.py           → converte PDF/HTML → Markdown (.md)
          │                     preservando tabelas e metadados
          ▼
   [3] chunking.py           → divide os .md em chunks de 512 chars
          │                     com sobreposição de 80 chars
          ▼
   [4] indexar.py            → gera embeddings multilinguais e
          │                     persiste no ChromaDB (HNSW cosine)
          ▼
   [5] pipeline.py           → recebe query → recupera chunks →
          │                     gera resposta com LLM (Groq/Gemini)
          ▼
   [6] avaliacao.py          → avalia com RAGAS (faithfulness,
                               context_recall, answer_relevancy)
```

**Modelo de embeddings:** `paraphrase-multilingual-mpnet-base-v2` (768 dims, PT-BR nativo)  
**Banco vetorial:** ChromaDB com índice HNSW e similaridade de cosseno  
**LLM:** Groq (llama-3.1-70b) ou Gemini 1.5 Flash — ambos gratuitos

---

## Pré-requisitos

| Requisito | Versão mínima | Observação |
|-----------|--------------|------------|
| Python | 3.10+ | [Download](https://www.python.org/downloads/) |
| Google Chrome | Qualquer | Necessário para o download (Selenium) |
| Docker + Docker Compose | 24+ | Opcional — para rodar em container |
| RAM | 8 GB | Recomendado para indexação dos 168K chunks |
| Espaço em disco | ~15 GB | Dados brutos + chunks + vectorstore |

---

## Quick Start (sem Docker)

### 1. Clone o repositório

```bash
git clone https://github.com/<seu-usuario>/projeto_rag.git
cd projeto_rag
```

### 2. Execute o script de setup

**Windows:**
```bat
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh && ./setup.sh
```

O script cria o `.venv`, instala todas as dependências e cria as pastas necessárias.

### 3. Configure as chaves de API

Edite o arquivo `.env` criado pelo setup:

```bash
# Abra o .env e preencha suas chaves:
GROQ_API_KEY=sua_chave_aqui       # https://console.groq.com (gratuito)
GEMINI_API_KEY=sua_chave_aqui     # https://aistudio.google.com (gratuito)
```

### 4. Ative o ambiente virtual

**Windows:**
```bat
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 5. Execute o pipeline (ordem obrigatória)

> **Importante:** todos os scripts devem ser rodados **de dentro da pasta `scripts/`**,
> pois usam caminhos relativos.

```bash
cd scripts

# Passo 1 — Download dos documentos (~26.000 arquivos)
# Tempo estimado: várias horas (depende da conexão)
python downloads.py
python download_extras.py

# Passo 2 — Conversão PDF → Markdown
python ingestao.py

# Passo 3 — Chunking dos documentos
python chunking.py

# Passo 4 — Geração de embeddings e indexação no ChromaDB
# Tempo estimado: 2-4 horas (168K chunks, modelo ~1 GB)
python indexar.py

# Passo 5 — Pipeline RAG interativo
python pipeline.py

# Passo 6 — Avaliação com RAGAS
python avaliacao.py
```

Todos os scripts possuem **retomada automática** — se interrompidos, continuam de onde pararam.

---

## Quick Start (com Docker)

> O Docker cobre os passos 2 a 6 do pipeline.
> O download dos dados (passo 1) deve ser feito localmente antes,
> pois requer o Google Chrome (Selenium).

### 1. Clone, configure o .env e baixe os dados

```bash
git clone https://github.com/<seu-usuario>/projeto_rag.git
cd projeto_rag
cp .env.example .env
# Edite .env com suas chaves de API

# Download local (requer Chrome instalado):
python -m venv .venv && source .venv/bin/activate  # ou setup.bat no Windows
pip install -r requirements.txt
cd scripts && python downloads.py && python download_extras.py && cd ..
```

### 2. Build e execução

```bash
# Build da imagem
docker-compose build

# Rodar cada etapa do pipeline
docker-compose run rag python scripts/ingestao.py
docker-compose run rag python scripts/chunking.py
docker-compose run rag python scripts/indexar.py
docker-compose run rag python scripts/pipeline.py
docker-compose run rag python scripts/avaliacao.py

# Ou shell interativo
docker-compose run rag bash
```

Os dados são montados como volumes — nada é copiado para dentro da imagem.

---

## Estrutura de Pastas

```
projeto_rag/
│
├── scripts/                    # Todo o código do pipeline
│   ├── downloads.py            # [Passo 1] Download dos PDFs da ANEEL
│   ├── download_extras.py      # [Passo 1b] Download de HTML/XLSX
│   ├── ingestao.py             # [Passo 2] PDF/HTML → Markdown
│   ├── chunking.py             # [Passo 3] Markdown → chunks .txt
│   ├── indexar.py              # [Passo 4] Chunks → embeddings → ChromaDB
│   ├── pipeline.py             # [Passo 5] Pipeline RAG (query → resposta)
│   └── avaliacao.py            # [Passo 6] Avaliação RAGAS
│
├── dados/                      # Dados brutos (não versionados)
│   ├── pdfs/                   # PDFs originais da ANEEL
│   ├── jsons/                  # Metadados dos documentos
│   └── html, xlsm, etc/        # Formatos alternativos
│
├── chunks_md/                  # Markdowns gerados (não versionados)
├── chunks/                     # Chunks .txt gerados (não versionados)
├── vectorstore/                # Índice ChromaDB (não versionado)
│
├── Dockerfile                  # Imagem Docker do pipeline
├── docker-compose.yml          # Orquestração dos containers
├── setup.bat                   # Setup automático Windows
├── setup.sh                    # Setup automático Linux/Mac
├── Makefile                    # Atalhos para Linux/Mac
├── requirements.txt            # Dependências Python
├── .env.example                # Template de variáveis de ambiente
└── .gitignore
```

---

## Configuração Avançada

### Parâmetros do indexar.py

```bash
# Customizar pasta de chunks ou batch size
python indexar.py --chunks-dir ../chunks --batch-size 32

# Ver todas as opções
python indexar.py --help
```

### Parâmetros relevantes em cada script

| Script | Parâmetro | Padrão | Descrição |
|--------|-----------|--------|-----------|
| `chunking.py` | `CHUNK_SIZE` | 512 | Tamanho máximo do chunk em caracteres |
| `chunking.py` | `CHUNK_OVERLAP` | 80 | Sobreposição entre chunks consecutivos |
| `indexar.py` | `BATCH_SIZE` | 64 | Chunks por lote de embedding |
| `pipeline.py` | `TOP_K` | 5 | Chunks retornados por query |

> Para máquinas com menos de 8 GB de RAM, reduza `BATCH_SIZE` para 32.

---

## Avaliação com RAGAS

O pipeline é avaliado usando a biblioteca [RAGAS](https://docs.ragas.io/) com as seguintes métricas:

| Métrica | O que mede |
|---------|-----------|
| **Faithfulness** | A resposta está ancorada nos chunks recuperados? |
| **Answer Relevancy** | A resposta responde de fato à pergunta? |
| **Context Precision** | Os chunks retornados são relevantes para a query? |
| **Context Recall** | Os chunks cobrem completamente a resposta esperada? |

---

## Dependências principais

| Biblioteca | Versão | Finalidade |
|-----------|--------|-----------|
| `pymupdf4llm` | latest | Extração de PDF → Markdown |
| `langchain-text-splitters` | latest | Chunking com RecursiveCharacterTextSplitter |
| `sentence-transformers` | latest | Modelo de embeddings multilingual |
| `chromadb` | latest | Banco vetorial com HNSW |
| `groq` | latest | Cliente da API Groq (LLM gratuito) |
| `ragas` | latest | Framework de avaliação RAG |
| `selenium` | latest | Download automatizado da ANEEL |

---

## Troubleshooting

**`UnicodeEncodeError` no Windows:**  
Os scripts foram escritos com saída ASCII pura para evitar esse erro. Se aparecer, certifique-se de rodar com o Python do `.venv`.

**`FileNotFoundError: ../chunks_md`:**  
Os scripts usam caminhos relativos e devem ser executados **de dentro da pasta `scripts/`**.

**Download lento ou com erro:**  
Os scripts de download possuem retomada automática. Rode novamente para continuar.

**Pouca RAM durante o `indexar.py`:**  
Reduza `BATCH_SIZE` de 64 para 32 editando o arquivo ou usando `--batch-size 32`.
