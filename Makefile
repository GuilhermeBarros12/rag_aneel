# ============================================================
# Makefile — RAG ANEEL (Linux/Mac)
# Atalhos para rodar cada etapa do pipeline
# ============================================================

PYTHON = .venv/bin/python

.PHONY: help setup download ingestao chunking indexar pipeline avaliar docker-build docker-run

help:  ## Exibe esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────

setup:  ## Cria .venv e instala dependências
	bash setup.sh

# ── Pipeline (ordem de execução) ───────────────────────────────────────

download:  ## [Passo 1] Baixa os documentos da ANEEL
	$(PYTHON) scripts/downloads.py
	$(PYTHON) scripts/download_extras.py

ingestao:  ## [Passo 2] Converte PDFs em Markdown
	$(PYTHON) scripts/ingestao.py

chunking:  ## [Passo 3] Divide os Markdowns em chunks
	$(PYTHON) scripts/chunking.py

indexar:  ## [Passo 4] Gera embeddings e indexa no ChromaDB
	$(PYTHON) scripts/indexar.py

pipeline:  ## [Passo 5] Inicia o pipeline RAG interativo
	$(PYTHON) scripts/pipeline.py

avaliar:  ## [Passo 6] Avalia com RAGAS nas 400 perguntas
	$(PYTHON) scripts/avaliar.py

# ── Docker ────────────────────────────────────────────────────────

docker-build:  ## Build da imagem Docker
	docker-compose build

docker-run:  ## Shell interativo no container
	docker-compose run rag bash
