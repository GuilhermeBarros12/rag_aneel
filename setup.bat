@echo off
:: ============================================================
:: setup.bat — Configuração do ambiente no Windows
:: Executa: python -m venv .venv, instala deps, cria pastas
:: ============================================================

echo.
echo ============================================================
echo  RAG ANEEL - Setup do Ambiente (Windows)
echo ============================================================
echo.

:: Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale em: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Cria o ambiente virtual se não existir
if not exist ".venv" (
    echo [1/4] Criando ambiente virtual .venv ...
    python -m venv .venv
    echo       Pronto.
) else (
    echo [1/4] Ambiente virtual .venv ja existe. Pulando.
)

:: Ativa o ambiente virtual
echo [2/4] Ativando ambiente virtual ...
call .venv\Scripts\activate.bat

:: Instala dependências
echo [3/4] Instalando dependencias (requirements.txt) ...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo       Pronto.

:: Cria pastas necessárias para o pipeline
echo [4/4] Criando pastas do pipeline ...
if not exist "dados\pdfs"           mkdir dados\pdfs
if not exist "dados\jsons"          mkdir dados\jsons
if not exist "dados\extras"         mkdir dados\extras
if not exist "chunks_md"            mkdir chunks_md
if not exist "chunks"               mkdir chunks
if not exist "vectorstore"          mkdir vectorstore
echo       Pronto.

:: Cria .env a partir do .env.example se ainda não existir
if not exist ".env" (
    copy .env.example .env >nul
    echo.
    echo [AVISO] Arquivo .env criado a partir de .env.example.
    echo         Edite o .env e adicione suas chaves de API antes de rodar o pipeline.
    echo         Arquivo: %CD%\.env
)

echo.
echo ============================================================
echo  Setup concluido!
echo.
echo  Para ativar o ambiente em novos terminais:
echo    .venv\Scripts\activate
echo.
echo  Proximos passos: veja o README.md
echo ============================================================
echo.
pause
