import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www2.aneel.gov.br/cedoc/",  # finge que veio da página da ANEEL
}

url = "http://www2.aneel.gov.br/cedoc/dsp20163386ti.pdf"  # uma das ativas

try:
    # tenta baixar os primeiros 1024 bytes apenas para testar
    resposta = requests.get(
        url,
        headers=HEADERS,
        timeout=15,
        allow_redirects=True,
        stream=True  # stream=True → não baixa tudo de uma vez, só o que pedirmos
    )
    print(f"Status: {resposta.status_code}")
    print(f"Content-Type: {resposta.headers.get('Content-Type', 'desconhecido')}")
    
    # lê só os primeiros bytes para confirmar que é um PDF
    primeiros_bytes = next(resposta.iter_content(1024))
    
    # PDFs sempre começam com "%PDF"
    if primeiros_bytes[:4] == b"%PDF":
        print("✅ É um PDF válido! Download funcionaria.")
    else:
        print(f"⚠️ Não parece um PDF. Início: {primeiros_bytes[:20]}")
        
except Exception as e:
    print(f"❌ Erro: {e}")