import os
import json
import pymupdf4llm
from bs4 import BeautifulSoup  # extrai texto limpo de arquivos HTML

# ============================================================
# CONFIGURAÇÕES
# ============================================================
PASTA_JSONS  = "../dados/jsons"          # onde estão os 3 arquivos .json
PASTA_PDFS   = "../dados/pdfs"           # onde estão os PDFs baixados
PASTA_EXTRAS = "../dados/html, xlsm, etc"  # onde estão os HTMLs baixados
PASTA_SAIDA  = "../chunks_md"            # onde os markdowns serão salvos
# ============================================================

os.makedirs(PASTA_SAIDA, exist_ok=True)  # cria a pasta de saída se não existir

# ------------------------------------------------------------

def extrair_pdf_para_markdown(caminho):
    """Converte PDF para Markdown preservando tabelas."""
    try:
        return pymupdf4llm.to_markdown(caminho)
    except Exception as e:
        print(f"   ⚠️  Erro ao extrair PDF {caminho}: {e}")
        return None

# ------------------------------------------------------------

def extrair_html_para_markdown(caminho):
    """
    Extrai texto limpo de um arquivo HTML.
    Remove tags, scripts, estilos e retorna texto simples formatado.
    """
    try:
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            conteudo = f.read()

        soup = BeautifulSoup(conteudo, "html.parser")

        # remove scripts e estilos — não são conteúdo útil
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()  # remove a tag e todo seu conteúdo

        # extrai o texto limpo, separando parágrafos com quebra de linha
        texto = soup.get_text(separator="\n", strip=True)

        # remove linhas vazias excessivas (mais de 2 seguidas)
        linhas = texto.split("\n")
        linhas_limpas = []
        vazias_seguidas = 0
        for linha in linhas:
            if linha.strip() == "":
                vazias_seguidas += 1
                if vazias_seguidas <= 1:  # permite no máximo 1 linha vazia seguida
                    linhas_limpas.append(linha)
            else:
                vazias_seguidas = 0
                linhas_limpas.append(linha)

        return "\n".join(linhas_limpas)

    except Exception as e:
        print(f"   ⚠️  Erro ao extrair HTML {caminho}: {e}")
        return None

# ------------------------------------------------------------

def carregar_todos_documentos(pasta_jsons):
    """Lê todos os JSONs e retorna lista unificada de documentos."""
    todos = []

    arquivos = [
        f for f in os.listdir(pasta_jsons)
        if f.endswith(".json") and f != "testes.json"
    ]

    for arquivo in arquivos:
        caminho = os.path.join(pasta_jsons, arquivo)
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)

            # estrutura real: dicionário com chave=data → registros
            for data, conteudo in dados.items():
                registros = conteudo.get("registros", [])
                todos.extend(registros)  # adiciona os documentos do dia à lista

            print(f"✅ {arquivo} carregado")

        except Exception as e:
            print(f"❌ Erro ao ler {arquivo}: {e}")

    print(f"\nTotal de documentos: {len(todos)}")
    return todos

# ------------------------------------------------------------

def montar_metadata(doc, nome_arquivo, tipo_pdf):
    """
    Monta o cabeçalho YAML que vai no topo de cada .md.
    Esse cabeçalho permite filtrar por situação, autor, data no retrieval.
    """
    return f"""---
titulo: {doc.get('titulo', '')}
autor: {doc.get('autor', '')}
situacao: {doc.get('situacao', '')}
assunto: {doc.get('assunto', '')}
assinatura: {doc.get('assinatura', '')}
publicacao: {doc.get('publicacao', '')}
tipo_pdf: {tipo_pdf}
arquivo_original: {nome_arquivo}
ementa: {doc.get('ementa', '')}
---

"""

# ------------------------------------------------------------

def processar_documentos(documentos):
    """
    Para cada documento:
    - Encontra o arquivo correspondente (PDF ou HTML) no disco
    - Extrai o conteúdo para Markdown
    - Adiciona metadata no topo
    - Salva na pasta de saída
    """
    total       = len(documentos)
    processados = 0
    ignorados   = 0

    for i, doc in enumerate(documentos):
        pdfs = doc.get("pdfs", [])

        for pdf_info in pdfs:
            nome_arquivo = pdf_info.get("arquivo", "").strip()
            tipo_pdf     = pdf_info.get("tipo", "")

            if not nome_arquivo:
                continue

            _, ext = os.path.splitext(nome_arquivo.lower())

            # ── define onde procurar o arquivo e como extrair ────────────
            if ext == ".pdf":
                caminho = os.path.join(PASTA_PDFS, nome_arquivo)
                extrator = extrair_pdf_para_markdown

            elif ext in {".html", ".htm"}:
                caminho = os.path.join(PASTA_EXTRAS, nome_arquivo)
                extrator = extrair_html_para_markdown

            else:
                continue  # ignora .zip, .xlsx, .rar, etc.

            # ── verifica se o arquivo existe no disco ────────────────────
            if not os.path.exists(caminho):
                ignorados += 1
                continue

            # ── define o nome do arquivo de saída ────────────────────────
            nome_saida    = nome_arquivo.replace(ext, ".md")  # ex: dsp20163284.md
            caminho_saida = os.path.join(PASTA_SAIDA, nome_saida)

            # pula se o markdown já foi gerado (permite retomar se interrompido)
            if os.path.exists(caminho_saida):
                processados += 1
                continue

            print(f"[{i+1}/{total}] Processando: {nome_arquivo}")

            # ── extrai o conteúdo ─────────────────────────────────────────
            conteudo = extrator(caminho)
            if conteudo is None:
                ignorados += 1
                continue

            # ── monta e salva o arquivo final ─────────────────────────────
            metadata       = montar_metadata(doc, nome_arquivo, tipo_pdf)
            conteudo_final = metadata + conteudo

            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(conteudo_final)

            processados += 1

            # mostra progresso a cada 100 arquivos
            if processados % 100 == 0:
                print(f"   ✅ {processados} processados até agora...")

    print("\n" + "=" * 50)
    print(f"✅ Processados: {processados}")
    print(f"⚠️  Ignorados:  {ignorados}")
    print(f"📁 Markdowns salvos em: {PASTA_SAIDA}/")

# ============================================================
if __name__ == "__main__":
    print("Carregando documentos dos JSONs...\n")
    documentos = carregar_todos_documentos(PASTA_JSONS)
    print("\nIniciando extração...\n")
    processar_documentos(documentos)