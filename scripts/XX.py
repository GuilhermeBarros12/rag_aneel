import os
import fitz  # pymupdf — para verificar se os PDFs são válidos

PASTA_PDFS = "../dados/pdfs"

arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith(".pdf")]

print(f"Total de PDFs na pasta: {len(arquivos)}\n")

for nome in arquivos:
    caminho = os.path.join(PASTA_PDFS, nome)
    tamanho = os.path.getsize(caminho) / 1024  # tamanho em KB

    try:
        doc    = fitz.open(caminho)             # tenta abrir o PDF
        paginas = doc.page_count                # conta as páginas
        doc.close()
        print(f"✅ {nome} | {tamanho:.1f} KB | {paginas} página(s)")
    except Exception as e:
        print(f"❌ CORROMPIDO: {nome} | {tamanho:.1f} KB | Erro: {e}")