# RAG ANEEL — Sistema de Perguntas e Respostas sobre Documentos Regulatórios

Sistema de **Retrieval-Augmented Generation (RAG)** desenvolvido para responder perguntas sobre o corpus regulatório da ANEEL (Agência Nacional de Energia Elétrica), composto por mais de **26.000 documentos** — resoluções normativas, despachos, notas técnicas e portarias.

**Modelo de embeddings:** `paraphrase-multilingual-mpnet-base-v2` (768 dims, PT-BR nativo)  
**Banco vetorial:** ChromaDB com índice HNSW e similaridade de cosseno  
**LLM:** Gemini 1.5 Flash (primário) ou Groq / Llama 3.3 70B (fallback) — ambos gratuitos

---

## Quick Start — Usar o sistema (recomendado)

> O vectorstore com todos os documentos da ANEEL já está pré-construído e hospedado no Hugging Face.
> Ele é baixado automaticamente na primeira execução. Você **não precisa** baixar PDFs nem gerar embeddings.

### Pré-requisitos

| Requisito | Detalhe |
|-----------|---------|
| Python 3.10+ | [Download](https://www.python.org/downloads/) |
| Chave de API Gemini | Gratuita em [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Chave de API Groq | Gratuita em [console.groq.com](https://console.groq.com) — usado como fallback |
| Espaço em disco | ~3 GB (vectorstore baixado automaticamente) |
| RAM | 2 GB |

### Passo 1 — Clone o repositório

```bash
git clone https://github.com/<seu-usuario>/projeto_rag.git
cd projeto_rag
```

### Passo 2 — Execute o setup

O script cria o ambiente virtual, instala todas as dependências e prepara o `.env`.

**Windows:**
```bat
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh && ./setup.sh
```

### Passo 3 — Configure suas chaves de API

Abra o arquivo `.env` criado pelo setup e preencha:

```env
GEMINI_API_KEY=sua_chave_aqui    # https://aistudio.google.com/app/apikey (gratuito)
GROQ_API_KEY=sua_chave_aqui      # https://console.groq.com (gratuito, fallback)
HF_REPO_ID=GuilhermeBarros12/rag-aneel-vectorstore  # já preenchido
HF_TOKEN=seu_token_aqui          # https://huggingface.co/settings/tokens (tipo: Read)
```

### Passo 4 — Ative o ambiente virtual

**Windows:**
```bat
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### Passo 5 — Inicie o pipeline

```bash
python scripts/pipeline.py
```

Na **primeira execução**, o vectorstore (~3 GB) será baixado automaticamente do Hugging Face.
Nas execuções seguintes, ele já estará em disco e o sistema inicia em segundos.

**Modo direto (uma pergunta):**
```bash
python scripts/pipeline.py --query "Qual o prazo para reclamações na ANEEL?"
```

**Modo interativo (loop de perguntas):**
```bash
python scripts/pipeline.py
# Digite suas perguntas e pressione Enter. Digite 'sair' para encerrar.
```

---

## Arquitetura do Pipeline

```
Documentos ANEEL (PDFs, HTMLs, XLSXs)
          │
          ▼
   [1] downloads.py          → baixa os arquivos da ANEEL (~26.000 docs)
          │
          ▼
   [2] ingestao.py           → converte PDF/HTML → Markdown (.md)
          │                     preservando tabelas e metadados
          ▼
   [3] chunking.py           → divide os .md em chunks de 512 chars
          │                     com sobreposição de 80 chars → 508K chunks
          ▼
   [4] indexar.py            → gera embeddings multilinguais e
          │                     persiste no ChromaDB (HNSW cosine)
          ▼
   [5] pipeline.py           → recebe query → recupera chunks →
          │                     gera resposta com LLM (Gemini → Groq)
          ▼
   [6] avaliacao.py          → avalia com RAGAS (faithfulness,
                                context_recall, answer_relevancy)
```

---

## Reconstruir o pipeline do zero (avançado / opcional)

> Esta seção é necessária **apenas** para quem quiser reprocessar todos os documentos
> da ANEEL desde o início — por exemplo, para atualizar o corpus ou reproduzir o experimento completo.
> Para uso normal, siga o Quick Start acima.

### Pré-requisitos adicionais

| Requisito | Detalhe |
|-----------|---------|
| Google Chrome | Para download automatizado via Selenium |
| RAM | 8 GB recomendado (indexação de 508K chunks) |
| Espaço em disco | ~15 GB (PDFs brutos + chunks + vectorstore) |
| Tempo estimado | ~6-10 horas no total |

### Passo 1 — Download dos documentos (~26.000 arquivos)

O `downloads.py` usa o Selenium para navegar no portal da ANEEL e baixar todos os PDFs.
O `download_extras.py` baixa os arquivos complementares (HTML, XLSX, XLSM).

**Tempo estimado:** várias horas (depende da conexão). Ambos os scripts têm **retomada automática** — se interrompidos, continuam de onde pararam.

```bash
python scripts/downloads.py        # baixa os PDFs principais → dados/pdfs/
python scripts/download_extras.py  # baixa HTMLs e planilhas  → dados/extras/
```

> Requer o Google Chrome instalado. O ChromeDriver é gerenciado automaticamente pelo `webdriver-manager`.

### Passo 2 — Conversão PDF/HTML → Markdown

Converte cada arquivo baixado para Markdown, preservando tabelas e adicionando metadados
(título, autor, situação, assunto) no cabeçalho de cada arquivo.

**Tempo estimado:** 1-2 horas. Tem retomada automática.

```bash
python scripts/ingestao.py   # gera .md em chunks_md/
```

### Passo 3 — Chunking dos documentos

Divide cada Markdown em chunks de 512 caracteres com sobreposição de 80 caracteres,
preservando tabelas inteiras e descartando trechos com menos de 50 caracteres (ruído).

**Resultado:** ~508.000 arquivos `.txt` em `chunks/`

```bash
python scripts/chunking.py   # gera .txt em chunks/
```

### Passo 4 — Geração de embeddings e indexação

Gera embeddings com o modelo `paraphrase-multilingual-mpnet-base-v2` (768 dimensões)
e persiste tudo no ChromaDB com índice HNSW e similaridade de cosseno.

**Tempo estimado:** 4-8 horas (508K chunks). Tem retomada automática — chunks já indexados são pulados.

```bash
python scripts/indexar.py    # popula vectorstore/
```

> Para máquinas com menos de 8 GB de RAM, use `--batch-size 32`.

### Passo 5 — Upload do vectorstore para o Hugging Face

Após a indexação, envie o vectorstore para o Hugging Face Hub para que outros
possam usar o sistema sem precisar repetir o processo.

```bash
python scripts/upload_vectorstore.py
```

> Requer `HF_TOKEN` (tipo Write) e `HF_REPO_ID` configurados no `.env`.

---

## Rodar com Docker (avançado)

> O Docker cobre os passos 2 a 6 do pipeline (ingestão, chunking, indexação, pipeline e avaliação).
> O download dos dados (passo 1) deve ser feito localmente antes, pois requer o Google Chrome.

```bash
# Build da imagem
docker-compose build

# Rodar cada etapa
docker-compose run rag python scripts/ingestao.py
docker-compose run rag python scripts/chunking.py
docker-compose run rag python scripts/indexar.py
docker-compose run rag python scripts/pipeline.py
docker-compose run rag python scripts/avaliacao.py

# Shell interativo
docker-compose run rag bash
```

Os dados são montados como volumes — nenhum arquivo de dados é copiado para dentro da imagem.

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
│   ├── upload_vectorstore.py   # Sobe o vectorstore para o Hugging Face
│   └── avaliacao.py            # [Passo 6] Avaliação RAGAS
│
├── dados/                      # Dados brutos (não versionados)
│   ├── pdfs/                   # PDFs originais da ANEEL
│   ├── jsons/                  # Metadados dos documentos
│   └── extras/                 # HTMLs e planilhas (.xlsx, .xlsm)
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

## Avaliação com RAGAS

O pipeline é avaliado usando a biblioteca [RAGAS](https://docs.ragas.io/) com as seguintes métricas:

| Métrica | O que mede |
|---------|-----------|
| **Faithfulness** | A resposta está ancorada nos chunks recuperados? |
| **Answer Relevancy** | A resposta responde de fato à pergunta? |
| **Context Precision** | Os chunks retornados são relevantes para a query? |
| **Context Recall** | Os chunks cobrem completamente a resposta esperada? |

---

## Parâmetros configuráveis

| Script | Parâmetro | Padrão | Descrição |
|--------|-----------|--------|-----------|
| `chunking.py` | `CHUNK_SIZE` | 512 | Tamanho máximo do chunk em caracteres |
| `chunking.py` | `CHUNK_OVERLAP` | 80 | Sobreposição entre chunks consecutivos |
| `indexar.py` | `BATCH_SIZE` | 64 | Chunks por lote de embedding |
| `pipeline.py` | `TOP_K` | 5 | Chunks retornados por query |

---

## Troubleshooting

**Download lento ou interrompido:**  
Os scripts `downloads.py` e `download_extras.py` têm retomada automática. Basta rodar novamente — arquivos já baixados são pulados.

**Indexação interrompida:**  
O `indexar.py` verifica os IDs já presentes no ChromaDB antes de começar. Basta rodar novamente para continuar de onde parou.

**`UnicodeEncodeError` no Windows:**  
Certifique-se de estar usando o Python do `.venv` (`.venv\Scripts\activate`).

**Pouca RAM durante o `indexar.py`:**  
Reduza o batch size: `python scripts/indexar.py --batch-size 32`
