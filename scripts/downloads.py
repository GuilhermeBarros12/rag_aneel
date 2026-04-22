import os
import json
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm                                  # barra de progresso visual

# ============================================================
PASTA_JSONS     = "../dados/jsons"
PASTA_PDFS      = "../dados/pdfs"
DELAY_DOWNLOAD  = 1     # segundos entre downloads
MAX_ESPERA      = 30    # segundos máximos esperando cada download
MAX_TENTATIVAS  = 3     # máximo de vezes que tenta reiniciar o Chrome
EXTENSOES_VALIDAS = {".pdf"}  # apenas PDFs serão baixados
# ============================================================

os.makedirs(PASTA_PDFS, exist_ok=True)

# ------------------------------------------------------------

def criar_driver(pasta_destino):
    """Cria e configura uma nova instância do Chrome."""
    opcoes = webdriver.ChromeOptions()
    opcoes.add_experimental_option("prefs", {
        "download.default_directory":              os.path.abspath(pasta_destino),
        "download.prompt_for_download":            False,
        "download.directory_upgrade":              True,
        "plugins.always_open_pdf_externally":      True,
        "profile.default_content_settings.popups": 0,
    })
    opcoes.add_argument("--no-sandbox")
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--disable-gpu")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opcoes
    )
    return driver

# ------------------------------------------------------------

def normalizar_url(url):
    """Corrige URLs com caracteres especiais e força https."""
    url = url.replace("http://", "https://", 1)
    partes = urllib.parse.urlsplit(url)
    caminho_corrigido = urllib.parse.quote(
        urllib.parse.unquote(partes.path),
        safe="/"
    )
    return urllib.parse.urlunsplit((
        partes.scheme,
        partes.netloc,
        caminho_corrigido,
        partes.query,
        partes.fragment
    ))

# ------------------------------------------------------------

def aguardar_download(pasta, nome_arquivo, timeout=30):
    """Aguarda o arquivo aparecer na pasta, verificando nome original e decodificado."""
    nome_decodificado    = urllib.parse.unquote(nome_arquivo)
    destino              = os.path.join(pasta, nome_arquivo)
    destino_decodificado = os.path.join(pasta, nome_decodificado)
    em_progresso         = os.path.join(pasta, nome_arquivo + ".crdownload")

    inicio = time.time()
    while time.time() - inicio < timeout:
        if os.path.exists(destino) and os.path.getsize(destino) > 0:
            return True
        if os.path.exists(destino_decodificado) and os.path.getsize(destino_decodificado) > 0:
            return True
        time.sleep(1)

    if os.path.exists(em_progresso):
        os.remove(em_progresso)            # limpa arquivo incompleto
    return False

# ------------------------------------------------------------

def carregar_todas_urls(pasta_jsons):
    """Percorre todos os JSONs e monta lista de PDFs para baixar."""
    todas_urls = []

    arquivos = [
        f for f in os.listdir(pasta_jsons)
        if f.endswith(".json") and f != "testes.json"
    ]

    for arquivo in arquivos:
        caminho = os.path.join(pasta_jsons, arquivo)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)       # tenta carregar o JSON
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"⚠️  Erro ao carregar {arquivo}: {e}")
            continue                       # pula JSONs corrompidos sem parar o script

        for data, conteudo in dados.items():
            for doc in conteudo.get("registros", []):
                for pdf in doc.get("pdfs", []):
                    url         = pdf.get("url", "")
                    arquivo_pdf = pdf.get("arquivo", "")

                    if not url or not arquivo_pdf:
                        continue           # pula entradas incompletas

                    _, extensao = os.path.splitext(arquivo_pdf.lower())
                    if extensao not in EXTENSOES_VALIDAS:
                        continue           # pula .html, .zip, etc. silenciosamente

                    todas_urls.append({
                        "url":     normalizar_url(url),
                        "arquivo": arquivo_pdf,
                        "titulo":  doc.get("titulo", "")
                    })

    print(f"📋 Total de PDFs mapeados: {len(todas_urls)}")
    return todas_urls

# ------------------------------------------------------------

def reiniciar_driver(driver, pasta_destino):
    """Fecha o Chrome atual e abre um novo. Retorna o novo driver."""
    try:
        driver.quit()                      # tenta fechar o Chrome atual
    except:
        pass                               # ignora erro se já estava fechado
    time.sleep(3)                          # pausa antes de reabrir
    return criar_driver(pasta_destino)     # retorna novo driver

# ------------------------------------------------------------

def baixar_com_selenium(lista_urls, pasta_destino):
    """
    Baixa cada PDF navegando diretamente para a URL.
    - Reinicia o Chrome automaticamente se a sessão cair (máx. 3 tentativas)
    - Pula arquivos já existentes (permite retomar após interrupção)
    - Mostra barra de progresso em tempo real
    """
    driver   = criar_driver(pasta_destino)
    baixados = 0
    pulados  = 0
    erros    = 0
    log_erros = []

    # tqdm cria a barra de progresso — total= define o máximo
    barra = tqdm(lista_urls, desc="Baixando PDFs", unit="pdf")

    for item in barra:
        url      = item["url"]
        nome_pdf = item["arquivo"]
        destino  = os.path.join(pasta_destino, nome_pdf)

        # pula se já existe no disco
        if os.path.exists(destino):
            pulados += 1
            barra.set_postfix(baixados=baixados, pulados=pulados, erros=erros)
            continue

        sucesso      = False
        tentativas   = 0

        while not sucesso and tentativas < MAX_TENTATIVAS:
            # tenta o mesmo arquivo até MAX_TENTATIVAS vezes
            tentativas += 1
            try:
                driver.get(url)
                sucesso = aguardar_download(pasta_destino, nome_pdf, MAX_ESPERA)

                if sucesso:
                    baixados += 1
                else:
                    if tentativas < MAX_TENTATIVAS:
                        # reinicia o Chrome e tenta de novo
                        driver = reiniciar_driver(driver, pasta_destino)

            except Exception as e:
                if "invalid session id" in str(e) or "disconnected" in str(e):
                    if tentativas < MAX_TENTATIVAS:
                        driver = reiniciar_driver(driver, pasta_destino)
                else:
                    break                  # erro desconhecido — não tenta de novo

        if not sucesso:
            log_erros.append(url)
            erros += 1

        # atualiza os contadores na barra de progresso
        barra.set_postfix(baixados=baixados, pulados=pulados, erros=erros)
        time.sleep(DELAY_DOWNLOAD)

    driver.quit()

    print("\n" + "=" * 50)
    print(f"✅ Baixados:  {baixados}")
    print(f"⏭️  Pulados:  {pulados}")
    print(f"❌ Erros:    {erros}")

    if log_erros:
        with open("erros_download.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(log_erros))
        print(f"⚠️  {len(log_erros)} erros salvos em: erros_download.txt")

# ============================================================
# EXECUÇÃO
# ============================================================
if __name__ == "__main__":
    lista_urls = carregar_todas_urls(PASTA_JSONS)
    baixar_com_selenium(lista_urls, PASTA_PDFS)