#!/usr/bin/env bash
# ============================================================
# setup.sh — Configuração do ambiente no Linux/Mac
# Executa: python -m venv .venv, instala deps, cria pastas
# ============================================================

set -e  # para o script se qualquer comando falhar

echo ""
echo "============================================================"
echo " RAG ANEEL - Setup do Ambiente (Linux/Mac)"
echo "============================================================"
echo ""

# Detecta Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERRO] Python 3 não encontrado. Instale em: https://www.python.org/downloads/"
    exit 1
fi

echo "Python encontrado: $($PYTHON --version)"
echo ""

# Cria ambiente virtual se não existir
if [ ! -d ".venv" ]; then
    echo "[1/4] Criando ambiente virtual .venv ..."
    $PYTHON -m venv .venv
    echo "      Pronto."
else
    echo "[1/4] Ambiente virtual .venv já existe. Pulando."
fi

# Ativa o ambiente virtual
echo "[2/4] Ativando ambiente virtual ..."
source .venv/bin/activate

# Instala dependências
echo "[3/4] Instalando dependências (requirements.txt) ..."
pip install --upgrade pip
pip install -r requirements.txt
echo "      Pronto."

# Cria pastas necessárias
echo "[4/4] Criando pastas do pipeline ..."
mkdir -p dados/pdfs dados/jsons dados/extras chunks_md chunks vectorstore
echo "      Pronto."

# Cria .env a partir do .env.example se ainda não existir
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "[AVISO] Arquivo .env criado a partir de .env.example."
    echo "        Edite o .env e adicione suas chaves de API antes de rodar o pipeline."
    echo "        Arquivo: $(pwd)/.env"
fi

echo ""
echo "============================================================"
echo " Setup concluído!"
echo ""
echo " Para ativar o ambiente em novos terminais:"
echo "   source .venv/bin/activate"
echo ""
echo " Próximos passos: veja o README.md"
echo "============================================================"
echo ""
