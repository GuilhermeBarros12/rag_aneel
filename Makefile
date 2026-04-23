# ============================================================
# Makefile — RAG ANEEL (Linux/Mac)
# Atalhos para rodar cada etapa do pipeline
# ============================================================

PYTHON = .venv/bin/python
SCRIPTS = scripts

.PHONY: help setup download ingestao chunking indexar pipeline avaliar docker-build docker-run

help:  ## Exibe esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────

setup:  ## Cria .venv e instala dependências
	bash setup.sh

# ── Pipeline (ordem de execução) ──────────────────────────────

download:  ## [Passo 1] Baixa os documentos da ANEEL
	cd $(SCRIPTS) && $(PYTHON) downloads.py
	cd $(SCRIPTS) && $(PYTHON) download_extras.py

ingestao:  ## [Passo 2] Converte PDFs em Markdown
	cd $(SCRIPTS) && $(PYTHON) ingestao.py

chunking:  ## [Passo 3] Divide os Markdowns em chunks
	cd $(SCRIPTS) && $(PYTHON) chunking.py

indexar:  ## [Passo 4] Gera embeddings e indexa no ChromaDB
	cd $(SCRIPTS) && $(PYTHON) indexar.py

pipeline:  ## [Passo 5] Inicia o pipeline RAG interativo
	cd $(SCRIPTS) && $(PYTHON) pipeline.py

avaliar:  ## [Passo 6] Avalia com RAGAS nas 400 perguntas
	cd $(SCRIPTS) && $(PYTHON) avaliacao.py

# ── Docker ────────────────────────────────────────────────────

docker-build:  ## Build da imagem Docker
	docker-compose build

docker-run:  ## Shell interativo no container
	docker-compose run rag bash
