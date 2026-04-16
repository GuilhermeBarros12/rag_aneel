import pymupdf4llm

nome_do_pdf = "dsp20214137ti.pdf" 

print(f"Lendo {nome_do_pdf} com foco em LLMs (Markdown)...")
print("=" * 50)

try:
    # A mágica acontece em uma linha só. Ele já lê tudo e converte as tabelas!
    texto_markdown = pymupdf4llm.to_markdown(nome_do_pdf)
    
    # Vamos imprimir os primeiros 15 00 caracteres para ver a diferença
    print(texto_markdown[:1500])

except Exception as erro:
    print(f"Erro ao processar: {erro}")