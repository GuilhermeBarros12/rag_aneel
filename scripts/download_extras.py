import os
import json
import time
import urllib.parse
import requests                # para HTMLs usamos requests — mais simples que Selenium
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ============================================================
PASTA_JSONS = "../dados/jsons"
PASTA_EXTRAS = "../dados/html, xlsm, etc"   # pasta separada para não misturar com PDFs
DELAY = 1
# ============================================================

os.makedirs(PASTA_EXTRAS, exist_ok=True)

# extensões que vamos baixar agora
EXTENSOES_ALVO = {".html", ".htm", ".xlsx", ".xlsm"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Referer": "https://www2.aneel.gov.br/cedoc/",
    "Accept": "*/*",
}

# ------------------------------------------------------------

def normalizar_url(url):
    """Força https e corrige caracteres especiais."""
    url = url.replace("http://", "https://", 1)
    partes = urllib.parse.urlsplit(url)
    caminho = urllib.parse.quote(urllib.parse.unquote(partes.path), safe="/")
    return urllib.parse.urlunsplit((partes.scheme, partes.netloc, caminho, partes.query, partes.fragment))

# ------------------------------------------------------------

def carregar_extras(pasta_jsons):
    """Carrega apenas arquivos das extensões alvo."""
    lista = []

    arquivos = [f for f in os.listdir(pasta_jsons) if f.endswith(".json") and f != "testes.json"]

    for arquivo in arquivos:
        with open(os.path.join(pasta_jsons, arquivo), "r", encoding="utf-8") as f:
            dados = json.load(f)

        for data, conteudo in dados.items():
            for doc in conteudo.get("registros", []):
                for pdf in doc.get("pdfs", []):
                    url         = pdf.get("url", "")
                    arquivo_pdf = pdf.get("arquivo", "").strip()  # .strip() remove espaços

                    if not url or not arquivo_pdf:
                        continue

                    _, ext = os.path.splitext(arquivo_pdf.lower())
                    if ext not in EXTENSOES_ALVO:
                        continue

                    lista.append({
                        "url":     normalizar_url(url),
                        "arquivo": arquivo_pdf,
                        "titulo":  doc.get("titulo", ""),
                        "tipo":    pdf.get("tipo", "")
                    })

    print(f"📋 Total de arquivos extras mapeados: {len(lista)}")
    return lista

# ------------------------------------------------------------

def baixar_extras(lista, pasta_destino):

    total     = len(lista)
    baixados  = 0
    pulados   = 0
    erros     = 0
    log_erros = []

    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument("--no-sandbox")
    opcoes.add_argument("--disable-dev-shm-usage")
    opcoes.add_argument("--disable-gpu")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opcoes
    )

    for i, item in enumerate(lista):
        url     = item["url"]
        nome    = item["arquivo"].strip()
        destino = os.path.join(pasta_destino, nome)
        _, ext  = os.path.splitext(nome.lower())

        if os.path.exists(destino):
            pulados += 1
            continue

        try:
            if ext in {".html", ".htm"}:
                driver.get(url)
                time.sleep(3)
                conteudo = driver.page_source
                with open(destino, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                tamanho = os.path.getsize(destino)
                if tamanho > 500:
                    baixados += 1
                    print(f"[{i+1}/{total}] ✅ {nome} ({tamanho/1024:.1f} KB)")
                else:
                    os.remove(destino)
                    print(f"[{i+1}/{total}] ❌ Conteúdo vazio: {nome}")
                    log_erros.append(url)
                    erros += 1

            elif ext in {".xlsx", ".xlsm"}:
                driver.get(url)
                time.sleep(3)
                cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
                resposta = requests.get(url, headers=HEADERS, cookies=cookies, timeout=30)
                if resposta.status_code == 200:
                    with open(destino, "wb") as f:
                        f.write(resposta.content)
                    baixados += 1
                    print(f"[{i+1}/{total}] ✅ {nome}")
                else:
                    print(f"[{i+1}/{total}] ❌ Status {resposta.status_code}: {nome}")
                    log_erros.append(url)
                    erros += 1

        except Exception as e:
            print(f"[{i+1}/{total}] ❌ Erro: {nome} | {e}")
            log_erros.append(url)
            erros += 1

        time.sleep(DELAY)

    driver.quit()

    print("\n" + "=" * 50)
    print(f"✅ Baixados:  {baixados}")
    print(f"⏭️  Pulados:  {pulados}")
    print(f"❌ Erros:    {erros}")

    if log_erros:
        with open("erros_extras.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(log_erros))
        print(f"⚠️  Erros salvos em: erros_extras.txt")
# ============================================================
if __name__ == "__main__":
    lista = carregar_extras(PASTA_JSONS)
    baixar_extras(lista, PASTA_EXTRAS)