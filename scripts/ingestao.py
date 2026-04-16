import os           # biblioteca para interagir com o sistema de arquivos (pastas, caminhos)
import json         # biblioteca para ler arquivos .json
import pymupdf4llm  # biblioteca que converte PDFs em Markdown preservando tabelas

# ============================================================
# CONFIGURAÇÕES — ajuste esses caminhos se necessário
# ============================================================

PASTA_JSONS = "."          # "." significa "a pasta atual onde o script está"
PASTA_PDFS  = "."          # pasta onde os PDFs já baixados estão armazenados
PASTA_SAIDA = "chunks_md"  # nome da pasta que será criada para guardar os markdowns

# ============================================================

os.makedirs(PASTA_SAIDA, exist_ok=True)  # cria a pasta de saída se ela não existir ainda
                                          # exist_ok=True evita erro se a pasta já existir

# ------------------------------------------------------------

def corrigir_encoding(texto):
    # função que conserta o problema de caracteres corrompidos (ex: "SituaÃ§Ã£o" → "Situação")
    # isso acontece porque o arquivo foi salvo em latin-1 mas lido como utf-8

    if texto is None:       # se o campo for vazio/nulo no JSON, não tenta corrigir
        return None         # retorna None diretamente

    try:
        return texto.encode("latin-1").decode("utf-8")  
        # encode("latin-1"): transforma o texto corrompido de volta em bytes "crus"
        # decode("utf-8"): lê esses bytes agora com o encoding correto
    except:
        return texto  # se a correção falhar (texto já estava certo), retorna como está

# ------------------------------------------------------------

def carregar_todos_documentos(pasta_jsons):
    # função que lê TODOS os arquivos .json da pasta e junta tudo numa lista única

    todos = []  # lista vazia que vai acumular todos os documentos encontrados

    arquivos = [f for f in os.listdir(pasta_jsons) if f.endswith(".json")]
    # os.listdir: lista todos os arquivos da pasta
    # o "if f.endswith('.json')" filtra só os arquivos que terminam com .json

    for arquivo in arquivos:  # percorre cada arquivo .json encontrado
        caminho = os.path.join(pasta_jsons, arquivo)  
        # os.path.join monta o caminho completo, ex: "./biblioteca_aneel.json"

        try:
            with open(caminho, "r", encoding="utf-8") as f:  
                # abre o arquivo em modo leitura ("r") com encoding utf-8
                dados = json.load(f)  # carrega o conteúdo JSON como uma lista Python

            if isinstance(dados, list):  # verifica se o JSON é uma lista de documentos
                todos.extend(dados)      # adiciona todos os documentos à nossa lista total
                print(f"✅ {arquivo}: {len(dados)} documentos carregados")  # feedback visual

        except Exception as e:               # se qualquer erro acontecer ao ler o arquivo
            print(f"❌ Erro ao ler {arquivo}: {e}")  # mostra o erro mas não para o programa

    return todos  # retorna a lista completa com todos os documentos de todos os JSONs

# ------------------------------------------------------------

def extrair_pdf_para_markdown(caminho_pdf):
    # função que recebe o caminho de um PDF e retorna seu conteúdo em formato Markdown

    try:
        return pymupdf4llm.to_markdown(caminho_pdf)  
        # to_markdown: lê o PDF e converte para Markdown
        # tabelas viram tabelas Markdown, títulos viram #, etc.

    except Exception as e:                                      # se o PDF estiver corrompido ou ilegível
        print(f"   ⚠️  Erro ao extrair {caminho_pdf}: {e}")    # avisa mas não para o programa
        return None  # retorna None para sinalizar que a extração falhou

# ------------------------------------------------------------

def processar_documentos(documentos):
    # função principal: percorre todos os documentos e gera um .md para cada PDF

    total      = len(documentos)  # total de documentos para mostrar progresso
    processados = 0               # contador de PDFs convertidos com sucesso
    ignorados   = 0               # contador de PDFs pulados (não encontrados ou com erro)

    for i, doc in enumerate(documentos):  
        # enumerate dá o índice (i) e o item (doc) a cada iteração
        # doc é um dicionário com titulo, situacao, ementa, pdfs, etc.

        # extrai e corrige cada campo de metadata do documento
        titulo   = corrigir_encoding(doc.get("titulo",    "sem_titulo"))
        situacao = corrigir_encoding(doc.get("situacao",  ""))
        ementa   = corrigir_encoding(doc.get("ementa",    ""))
        autor    = corrigir_encoding(doc.get("autor",     ""))
        assunto  = corrigir_encoding(doc.get("assunto",   ""))
        # .get("campo", "valor_padrão"): busca o campo no dicionário
        # se o campo não existir, retorna o valor padrão (string vazia ou "sem_titulo")

        pdfs = doc.get("pdfs", [])  
        # pega a lista de PDFs do documento
        # se não tiver o campo "pdfs", retorna lista vazia []

        for pdf_info in pdfs:  # percorre cada PDF dentro do documento
                               # um documento pode ter Texto Integral + Nota Técnica, por exemplo

            if not pdf_info.get("baixado", False):  
                # verifica se o campo "baixado" é True
                # se for False ou não existir, pula esse PDF
                continue  # "continue" pula para a próxima iteração do loop

            nome_arquivo = pdf_info.get("arquivo", "")       # ex: "dsp20223683ti.pdf"
            tipo_pdf     = corrigir_encoding(pdf_info.get("tipo", ""))  
            # ex: "Texto Integral", "Nota Técnica" — será salvo na metadata

            caminho_pdf = os.path.join(PASTA_PDFS, nome_arquivo)  
            # monta o caminho completo do PDF, ex: "./dsp20223683ti.pdf"

            if not os.path.exists(caminho_pdf):  
                # verifica se o arquivo realmente existe no disco
                # se não existir (não foi baixado localmente), pula
                print(f"[{i+1}/{total}] ⚠️  PDF não encontrado: {nome_arquivo}")
                ignorados += 1  # incrementa o contador de ignorados
                continue        # pula para o próximo PDF

            print(f"[{i+1}/{total}] Processando: {nome_arquivo}")  # mostra progresso no terminal

            markdown = extrair_pdf_para_markdown(caminho_pdf)  
            # chama a função que converte o PDF em Markdown
            # retorna o texto completo do documento em formato Markdown

            if markdown is None:    # se a extração falhou (PDF corrompido, etc.)
                ignorados += 1      # conta como ignorado
                continue            # pula para o próximo

            # monta o cabeçalho de metadata que vai no TOPO de cada arquivo .md
            # isso é o que vai permitir filtrar por situação, autor, data, etc. no retrieval
            metadata_header = f"""---
titulo: {titulo}
autor: {autor}
situacao: {situacao}
assunto: {assunto}
assinatura: {doc.get('assinatura', '')}
publicacao: {doc.get('publicacao', '')}
tipo_pdf: {tipo_pdf}
arquivo_pdf: {nome_arquivo}
ementa: {ementa}
---

"""
            # f"""...""": string multilinha com f-string (substitui as variáveis pelo valor real)
            # o bloco entre --- é chamado de "frontmatter YAML", padrão para metadata em .md

            conteudo_final = metadata_header + markdown  
            # junta o cabeçalho de metadata com o conteúdo extraído do PDF

            nome_saida    = nome_arquivo.replace(".pdf", ".md")  
            # transforma "dsp20223683ti.pdf" em "dsp20223683ti.md"

            caminho_saida = os.path.join(PASTA_SAIDA, nome_saida)  
            # monta o caminho completo de saída, ex: "chunks_md/dsp20223683ti.md"

            with open(caminho_saida, "w", encoding="utf-8") as f:  
                # abre (ou cria) o arquivo de saída em modo escrita ("w")
                f.write(conteudo_final)  # escreve o conteúdo final no arquivo

            processados += 1  # incrementa o contador de sucessos

    # após processar tudo, imprime o resumo final
    print("\n" + "=" * 50)
    print(f"✅ Processados: {processados}")   # quantos PDFs viraram .md com sucesso
    print(f"⚠️  Ignorados:  {ignorados}")    # quantos foram pulados
    print(f"📁 Markdowns salvos em: {PASTA_SAIDA}/")  # onde encontrar os arquivos gerados

# ============================================================
# EXECUÇÃO — esse bloco só roda quando você executa o arquivo diretamente
# (não roda se outro script importar esse arquivo como biblioteca)
# ============================================================

if __name__ == "__main__":
    print("Carregando documentos dos JSONs...")
    documentos = carregar_todos_documentos(PASTA_JSONS)  # carrega todos os JSONs
    print(f"\nTotal de documentos encontrados: {len(documentos)}\n")
    print("Iniciando extração dos PDFs...\n")
    processar_documentos(documentos)  # processa e gera os markdowns