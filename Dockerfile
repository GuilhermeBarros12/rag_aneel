# ============================================================
# Dockerfile — RAG ANEEL
# ============================================================
# Cobre as etapas: ingestão, chunking, indexação, pipeline e avaliação.
# O download dos dados brutos (Selenium) é feito localmente antes de
# montar o container — veja README.md para instruções completas.
# ============================================================

FROM python:3.11-slim

# Metadados
LABEL maintainer="RAG ANEEL"
LABEL description="Pipeline RAG sobre documentos regulatórios da ANEEL"

# Evita prompts interativos do apt e do Python
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instala dependências de sistema necessárias para PyMuPDF e lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia e instala dependências Python primeiro (camada cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
COPY scripts/ ./scripts/

# Cria as pastas de dados esperadas pelo pipeline
# (serão sobrescritas pelos volumes do docker-compose)
RUN mkdir -p dados chunks_md chunks vectorstore

# Por padrão, exibe ajuda de uso
CMD ["python", "-c", "print('RAG ANEEL container pronto. Use docker-compose run rag python scripts/<script>.py')"]
