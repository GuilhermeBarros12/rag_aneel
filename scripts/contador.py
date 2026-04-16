import json, os

arquivos = [f for f in os.listdir(".") if f.endswith(".json") and f != "testes.json"]

total_pdfs    = 0  # contador total de PDFs
total_docs    = 0  # contador total de documentos
datas_vazias  = 0  # datas sem registros
urls_exemplo  = [] # guarda algumas URLs para checar o padrão

for arquivo in arquivos:                                    # percorre cada JSON
    with open(arquivo, "r", encoding="utf-8") as f:
        dados = json.load(f)

    for data, conteudo in dados.items():                    # percorre cada data
        registros = conteudo.get("registros", [])

        if len(registros) == 0:                             # conta datas vazias
            datas_vazias += 1
            continue

        for doc in registros:                               # percorre cada documento
            total_docs += 1
            for pdf in doc.get("pdfs", []):                 # percorre cada PDF do doc
                total_pdfs += 1
                if len(urls_exemplo) < 5:                   # guarda 5 URLs de exemplo
                    urls_exemplo.append(pdf.get("url", ""))

print(f"Total de documentos: {total_docs}")
print(f"Total de PDFs para baixar: {total_pdfs}")
print(f"Datas sem registros: {datas_vazias}")
print(f"\nExemplos de URLs:")
for url in urls_exemplo:
    print(f"  {url}")