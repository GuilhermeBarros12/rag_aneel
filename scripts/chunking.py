import os      # para navegar no sistema de arquivos e checar caminhos
import re      # para usar expressões regulares (extrair o bloco YAML e detectar tabelas)
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
# RecursiveCharacterTextSplitter: divide o texto tentando os separadores em ordem
# (parágrafos → linhas → frases → palavras → caracteres), evitando cortes ruins

# ============================================================
# Caminhos resolvidos a partir da raiz do projeto (funciona de qualquer CWD)
ROOT            = Path(__file__).resolve().parent.parent
PASTA_MARKDOWNS = str(ROOT / "chunks_md")  # onde estão os .md gerados pelo ingestao.py
PASTA_CHUNKS    = str(ROOT / "chunks")     # onde serão salvos os .txt de cada chunk

CHUNK_SIZE    = 512   # tamanho máximo de cada chunk em caracteres
CHUNK_OVERLAP = 80    # quantos caracteres de sobreposição entre chunks consecutivos
MIN_CHARS     = 50    # chunks menores que isso são descartados (ruído)

# separadores tentados em ordem — do mais semântico ao mais bruto
SEPARADORES = ["\n\n", "\n", ". ", " ", ""]

# ============================================================

os.makedirs(PASTA_CHUNKS, exist_ok=True)   # cria a pasta de saída se não existir
                                            # exist_ok=True evita erro se já existir

# ------------------------------------------------------------

def extrair_metadata_do_header(conteudo):
    """
    Lê o bloco YAML entre os '---' no topo do arquivo .md
    e retorna um dicionário com os campos encontrados.

    Exemplo de entrada:
        ---
        titulo: DSP - DESPACHO 3386/2016
        autor: SCG/ANEEL
        ---
    Saída: {'titulo': 'DSP - DESPACHO 3386/2016', 'autor': 'SCG/ANEEL', ...}
    """

    metadata = {}   # dicionário vazio que vai acumular os campos encontrados

    # re.search busca o padrão em qualquer parte do texto
    # ^---\s*\n  →  linha com "---" no início do arquivo
    # (.*?)      →  captura tudo entre os dois "---" (modo não-guloso)
    # \n---      →  linha de fechamento "---"
    # re.DOTALL  →  faz "." casar com quebras de linha também
    match = re.search(r"^---\s*\n(.*?)\n---", conteudo, re.DOTALL)

    if not match:              # se não encontrou bloco YAML, retorna dicionário vazio
        return metadata

    bloco_yaml = match.group(1)   # pega apenas o conteúdo entre os "---"

    for linha in bloco_yaml.split("\n"):    # percorre linha por linha do bloco
        if ":" in linha:                    # só processa linhas que têm ":" (campo: valor)
            chave, _, valor = linha.partition(":")
            # partition(":") divide na PRIMEIRA ocorrência de ":"
            # ex: "titulo: DSP: algo" → chave="titulo", valor=" DSP: algo"
            metadata[chave.strip()] = valor.strip()
            # .strip() remove espaços extras das bordas

    return metadata   # ex: {'titulo': 'DSP...', 'autor': 'SCG/ANEEL', ...}

# ------------------------------------------------------------

def extrair_texto_sem_header(conteudo):
    """
    Remove o bloco YAML do topo e retorna apenas o corpo do documento.

    Entrada: string completa do .md (com o cabeçalho)
    Saída:   string só com o texto/markdown do documento
    """

    # re.sub substitui o padrão encontrado por uma string vazia ""
    # flags=re.DOTALL para o "." casar com \n também
    texto = re.sub(r"^---\s*\n.*?\n---\s*\n", "", conteudo, flags=re.DOTALL)
    # o \s*\n depois do "---" de fechamento consome a linha em branco após o cabeçalho

    return texto.strip()   # remove espaços/quebras de linha sobrando nas bordas

# ------------------------------------------------------------

def proteger_tabelas(texto):
    """
    Detecta blocos de tabela Markdown (linhas que contêm "|")
    e os substitui por placeholders __TABELA_0__, __TABELA_1__, etc.

    Por quê? O splitter não sabe que uma tabela é uma unidade indivisível —
    sem essa proteção ele poderia cortar a tabela no meio, gerando chunks inúteis.

    Retorna:
        texto_protegido  — texto com os placeholders no lugar das tabelas
        tabelas          — dicionário { '__TABELA_0__': '<texto original>' }
    """

    tabelas    = {}         # vai guardar o texto original de cada tabela
    contador   = [0]        # lista com um inteiro (truque para modificar dentro da função interna)
    linhas     = texto.split("\n")   # divide o texto em linhas individuais
    resultado  = []         # vai acumular as linhas do texto final (com placeholders)
    bloco      = []         # acumula as linhas do bloco de tabela sendo lido no momento

    def fechar_bloco():
        """Chamada quando o bloco de tabela terminou: salva e insere o placeholder."""
        if bloco:                                           # só age se há algo no bloco
            chave = f"__TABELA_{contador[0]}__"            # cria o nome do placeholder
            tabelas[chave] = "\n".join(bloco)              # salva o texto original da tabela
            resultado.append(chave)                        # insere o placeholder no texto
            bloco.clear()                                  # limpa o buffer do bloco
            contador[0] += 1                               # incrementa o contador para a próxima tabela

    for linha in linhas:            # percorre cada linha do texto
        if "|" in linha:            # linha de tabela Markdown sempre tem "|"
            bloco.append(linha)     # adiciona ao bloco de tabela em construção
        else:
            fechar_bloco()          # linha normal: fecha o bloco anterior (se havia um)
            resultado.append(linha) # adiciona a linha normal ao resultado

    fechar_bloco()   # fecha o último bloco, se o arquivo terminar com uma tabela

    texto_protegido = "\n".join(resultado)   # remonta o texto com as linhas tratadas
    return texto_protegido, tabelas          # retorna os dois valores

# ------------------------------------------------------------

def restaurar_tabelas(chunks, tabelas):
    """
    Percorre a lista de chunks e substitui cada placeholder
    pelo texto original da tabela correspondente.

    Parâmetros:
        chunks   — lista de strings (os chunks gerados pelo splitter)
        tabelas  — dicionário { '__TABELA_N__': '<texto original>' }
    Retorna:
        lista de chunks com as tabelas restauradas
    """

    chunks_restaurados = []   # vai acumular os chunks após a restauração

    for chunk in chunks:                           # percorre cada chunk
        for chave, texto_tabela in tabelas.items():   # percorre cada tabela salva
            chunk = chunk.replace(chave, texto_tabela)
            # replace troca o placeholder pelo texto original da tabela
        chunks_restaurados.append(chunk)           # adiciona o chunk restaurado

    return chunks_restaurados   # retorna a lista completa já restaurada

# ------------------------------------------------------------

def chunkar_documento(texto):
    """
    Pipeline completo de chunking de um único documento:
      1. Protege as tabelas com placeholders
      2. Aplica o RecursiveCharacterTextSplitter
      3. Restaura as tabelas nos chunks
      4. Filtra chunks muito curtos (ruído)

    Parâmetro:
        texto — string com o corpo do documento (sem o cabeçalho YAML)
    Retorna:
        lista de strings, cada uma sendo um chunk pronto
    """

    # passo 1: substitui tabelas por placeholders antes de dividir
    texto_protegido, tabelas = proteger_tabelas(texto)

    # passo 2: cria o splitter com os parâmetros definidos no topo do arquivo
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = CHUNK_SIZE,    # tamanho máximo de cada pedaço
        chunk_overlap = CHUNK_OVERLAP, # sobreposição entre pedaços consecutivos
        separators    = SEPARADORES,   # ordem de tentativa dos separadores
    )

    # split_text divide o texto e retorna uma lista de strings
    chunks_brutos = splitter.split_text(texto_protegido)

    # passo 3: devolve as tabelas originais para os chunks onde os placeholders caíram
    chunks_restaurados = restaurar_tabelas(chunks_brutos, tabelas)

    # passo 4: filtra chunks muito curtos — geralmente são cabeçalhos soltos ou ruído
    chunks_finais = [
        c for c in chunks_restaurados
        if len(c.strip()) >= MIN_CHARS   # só mantém se tiver ao menos MIN_CHARS caracteres
    ]

    return chunks_finais   # lista de strings prontas para salvar

# ------------------------------------------------------------

def montar_cabecalho_chunk(metadata, chunk_id, chunk_total):
    """
    Monta o bloco YAML que vai no topo de cada arquivo de chunk.
    É idêntico ao cabeçalho original + dois campos extras: chunk_id e chunk_total.

    Parâmetros:
        metadata    — dicionário com os campos do documento original
        chunk_id    — índice do chunk (começa em 1)
        chunk_total — total de chunks do documento
    Retorna:
        string com o bloco YAML completo
    """

    linhas = ["---"]   # abre o bloco YAML

    for chave, valor in metadata.items():       # insere cada campo do documento original
        linhas.append(f"{chave}: {valor}")

    linhas.append(f"chunk_id: {chunk_id}")       # campo extra: índice deste chunk
    linhas.append(f"chunk_total: {chunk_total}") # campo extra: total de chunks do doc
    linhas.append("---")                         # fecha o bloco YAML
    linhas.append("")                            # linha em branco após o cabeçalho

    return "\n".join(linhas)   # une tudo com quebras de linha e retorna

# ------------------------------------------------------------

def processar_markdowns(pasta_entrada, pasta_saida):
    """
    Função principal: percorre todos os .md da pasta de entrada,
    aplica o chunking e salva os chunks como .txt na pasta de saída.

    Mecanismo de retomada: se já existir pelo menos um chunk de um documento,
    ele é pulado — assim o script pode ser interrompido e continuado de onde parou.
    """

    # lista todos os arquivos .md da pasta de entrada
    arquivos = [f for f in os.listdir(pasta_entrada) if f.endswith(".md")]

    total_docs    = len(arquivos)   # total de documentos a processar
    processados   = 0               # documentos processados com sucesso nesta execução
    ignorados     = 0               # documentos pulados (já existiam ou com erro)
    total_chunks  = 0               # chunks gerados no total

    for i, nome_arquivo in enumerate(arquivos):   # enumerate dá índice + nome

        nome_base = nome_arquivo.replace(".md", "")
        # ex: "ndsp20163386.md" → "ndsp20163386"
        # será usado como prefixo no nome dos chunks

        # ── verifica se já foi processado (mecanismo de retomada) ────────────
        # procura qualquer arquivo que comece com nome_base + "_chunk" na pasta de saída
        ja_existe = any(
            f.startswith(nome_base + "_chunk")
            for f in os.listdir(pasta_saida)
        )
        # os.listdir lista todos os arquivos já na pasta de saída
        # any() retorna True se pelo menos um arquivo satisfaz a condição

        if ja_existe:      # se o documento já foi processado antes, pula
            ignorados += 1
            continue       # vai direto para o próximo arquivo

        # ── lê o arquivo .md ─────────────────────────────────────────────────
        caminho_entrada = os.path.join(pasta_entrada, nome_arquivo)   # caminho completo

        try:
            with open(caminho_entrada, "r", encoding="utf-8") as f:
                conteudo = f.read()   # lê todo o conteúdo do arquivo como string
        except Exception as e:
            print(f"[ERRO] Falha ao ler {nome_arquivo}: {e}")
            ignorados += 1
            continue   # erro de leitura não para o script, só pula esse arquivo

        # ── extrai metadata e corpo do documento ─────────────────────────────
        metadata = extrair_metadata_do_header(conteudo)   # dicionário com os campos YAML
        texto    = extrair_texto_sem_header(conteudo)     # só o corpo do documento

        if not texto.strip():       # se o corpo estiver vazio, não há o que chunkar
            ignorados += 1
            continue

        # ── aplica o chunking ─────────────────────────────────────────────────
        try:
            chunks = chunkar_documento(texto)   # lista de strings (os pedaços)
        except Exception as e:
            print(f"[ERRO] Falha ao chunkar {nome_arquivo}: {e}")
            ignorados += 1
            continue   # erro no chunking não para o script

        if not chunks:      # se não gerou nenhum chunk válido, ignora
            ignorados += 1
            continue

        chunk_total = len(chunks)   # total de chunks deste documento

        # ── salva cada chunk como um arquivo .txt separado ───────────────────
        for idx, chunk_texto in enumerate(chunks):    # idx começa em 0
            chunk_id = idx + 1                        # usamos 1-indexed para facilitar leitura

            # monta o cabeçalho YAML com os dados originais + chunk_id e chunk_total
            cabecalho = montar_cabecalho_chunk(metadata, chunk_id, chunk_total)

            conteudo_chunk = cabecalho + chunk_texto   # cabeçalho + texto do chunk

            # nome do arquivo: ex "ndsp20163386_chunk1.txt", "ndsp20163386_chunk2.txt"
            nome_chunk   = f"{nome_base}_chunk{chunk_id}.txt"
            caminho_saida = os.path.join(pasta_saida, nome_chunk)

            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(conteudo_chunk)   # escreve o chunk no disco

        processados  += 1             # conta mais um documento processado
        total_chunks += chunk_total   # acumula o total de chunks

        # ── mostra progresso a cada 200 documentos ───────────────────────────
        if processados % 200 == 0:
            print(f"   [OK] {processados}/{total_docs} documentos processados "
                  f"| {total_chunks} chunks gerados ate agora...")

    # ── resumo final ─────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"[OK]  Documentos processados: {processados}")
    print(f"[--]  Ignorados (ja prontos ou erro): {ignorados}")
    print(f"[DOC] Total de chunks gerados: {total_chunks}")
    print(f"[DIR] Chunks salvos em: {pasta_saida}/")

# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    print("Iniciando chunking dos markdowns...\n")
    processar_markdowns(PASTA_MARKDOWNS, PASTA_CHUNKS)
