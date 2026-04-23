import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Referer": "https://www2.aneel.gov.br/cedoc/",
    "Accept": "*/*",
}

urls_teste = [
    "https://www2.aneel.gov.br/cedoc/aren2016731_2.xlsx",
    "https://www2.aneel.gov.br/cedoc/aprt20163936_2.xlsx",
    "https://www2.aneel.gov.br/cedoc/areh20162014_2.xlsm",
]

for url in urls_teste:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        print(f"Status: {r.status_code} | Content-Type: {r.headers.get('Content-Type')} | {url}")
    except Exception as e:
        print(f"Erro: {e} | {url}")