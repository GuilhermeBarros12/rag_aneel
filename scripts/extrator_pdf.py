import pymupdf4llm

# muda o nome para um dos PDFs que você baixou
nome_do_pdf = "../dados/pdfs/dsp20163399ti.pdf"

texto_markdown = pymupdf4llm.to_markdown(nome_do_pdf)
print(texto_markdown[:2000])  # mostra os primeiros 2000 caracteres

