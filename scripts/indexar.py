import os                          # para navegar no sistema de arquivos
import re                          # para extrair o bloco YAML dos chunks com regex
from tqdm import tqdm              # barra de progresso visual no terminal

import chromadb                    # banco vetorial — persiste os embeddings em disco
from sentence_transformers import SentenceTransformer
# SentenceTransformer: carrega e roda o modelo de embeddings multilingual

# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_CHUNKS     = "../chunks"       # onde estão os .txt gerados pelo chunking.py
PASTA_VECTORSTORE = "../vectorstore" # onde o ChromaDB vai salvar os dados em disco

NOME_COLECAO = "aneel_docs"          # nome da coleção dentro do ChromaDB

# modelo multilingual treinado para similaridade semântica em português
MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

BATCH_SIZE = 64   # quantos chunks processa por vez
                  # valores maiores são mais rápidos mas consomem mais RAM
                  # 64 é seguro para ~8 GB de RAM; reduza para 32 se travar

# ============================================================

os.makedirs(PASTA_VECTORSTORE, exist_ok=True)   # cria a pasta do vectorstore se não existir

# ------------------------------------------------------------

def extrair_metadata_e_texto(conteudo):
    """
    Recebe o conteúdo completo de um arquivo .txt de chunk.
    Retorna (dicionário de metadata, texto do corpo).

    O cabeçalho YAML tem formato:
        ---
        titulo: ...
        chunk_id: 3
        chunk_total: 7
        ---
        <texto do chunk>
    """

    metadata = {}   # vai guardar os campos do cabeçalho

    # busca o bloco entre os dois "---"
    match = re.search(r"^---\s*\n(.*?)\n---", conteudo, re.DOTALL)

    if match:
        bloco_yaml = match.group(1)          # conteúdo entre os "---"
        for linha in bloco_yaml.split("\n"):  # percorre linha por linha
            if ":" in linha:
                chave, _, valor = linha.partition(":")   # divide na primeira ":"
                metadata[chave.strip()] = valor.strip()  # salva no dicionário

    # remove o cabeçalho YAML e retorna só o corpo do chunk
    texto = re.sub(r"^---\s*\n.*?\n---\s*\n", "", conteudo, flags=re.DOTALL)

    return metadata, texto.strip()   # retorna os dois valores

# ------------------------------------------------------------

def limpar_metadata_para_chroma(metadata):
    """
    ChromaDB só aceita valores de metadata dos tipos: str, int, float, bool.
    Nenhum campo pode ser None ou outro tipo.
    Esta função converte tudo para string e remove Nones.

    Parâmetro:
        metadata — dicionário com os campos do cabeçalho YAML
    Retorna:
        dicionário seguro para passar ao ChromaDB
    """

    metadata_limpa = {}
    for chave, valor in metadata.items():
        if valor is None:
            metadata_limpa[chave] = ""          # None vira string vazia
        else:
            metadata_limpa[chave] = str(valor)  # garante que tudo é string
    return metadata_limpa

# ------------------------------------------------------------

def carregar_ids_existentes(colecao):
    """
    Retorna um conjunto (set) com todos os IDs já indexados no ChromaDB.
    Usado para não re-indexar chunks que já estão no banco (retomada).

    Busca em páginas de 5000 para não sobrecarregar a memória.
    """

    ids_existentes = set()   # conjunto — busca por pertencimento é O(1)
    offset = 0               # posição de início de cada página
    pagina = 5000            # quantos IDs busca por vez

    while True:
        # include=[] → retorna só os IDs, sem embeddings/documentos (mais rápido)
        resultado = colecao.get(limit=pagina, offset=offset, include=[])
        ids_pagina = resultado["ids"]   # lista de IDs desta página

        if not ids_pagina:              # página vazia → chegou ao fim
            break

        ids_existentes.update(ids_pagina)   # adiciona ao conjunto total
        offset += pagina                    # avança para a próxima página

    return ids_existentes   # ex: {"ndsp20163386_chunk1", "ndsp20163386_chunk2", ...}

# ------------------------------------------------------------

def processar_em_batches(arquivos, ids_existentes, colecao, modelo):
    """
    Função principal de indexação.
    Percorre os arquivos de chunk, gera embeddings em lotes e salva no ChromaDB.

    Parâmetros:
        arquivos        — lista de nomes de arquivo .txt na PASTA_CHUNKS
        ids_existentes  — set com IDs já no ChromaDB (para pular)
        colecao         — objeto de coleção do ChromaDB
        modelo          — modelo SentenceTransformer carregado
    """

    # acumuladores do lote atual
    batch_ids        = []   # IDs únicos de cada chunk
    batch_textos     = []   # textos dos chunks (para o ChromaDB armazenar e para embedding)
    batch_metadatas  = []   # metadatas dos chunks
    batch_embeddings = []   # vetores gerados pelo modelo

    total_indexados = 0    # chunks novos indexados nesta execução
    total_pulados   = 0    # chunks já existentes, pulados
    total_erros     = 0    # arquivos com erro de leitura

    # tqdm cria a barra de progresso — desc é o texto que aparece ao lado
    for nome_arquivo in tqdm(arquivos, desc="Indexando chunks", unit="chunk"):

        # o nome do arquivo (sem .txt) é o ID único do chunk no ChromaDB
        chunk_id = nome_arquivo.replace(".txt", "")
        # ex: "ndsp20163386_chunk1.txt" → "ndsp20163386_chunk1"

        # ── pula se já foi indexado ────────────────────────────────────────
        if chunk_id in ids_existentes:
            total_pulados += 1
            continue   # vai direto para o próximo arquivo

        # ── lê o arquivo ──────────────────────────────────────────────────
        caminho = os.path.join(PASTA_CHUNKS, nome_arquivo)   # caminho completo

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()   # lê o arquivo inteiro como string
        except Exception as e:
            print(f"\n❌ Erro ao ler {nome_arquivo}: {e}")
            total_erros += 1
            continue   # erro não para o script, só pula esse arquivo

        # ── extrai metadata e corpo do chunk ──────────────────────────────
        metadata, texto = extrair_metadata_e_texto(conteudo)

        if not texto:       # chunk vazio não tem o que indexar
            total_erros += 1
            continue

        metadata_limpa = limpar_metadata_para_chroma(metadata)   # garante tipos corretos

        # ── adiciona ao lote atual ─────────────────────────────────────────
        batch_ids.append(chunk_id)              # ID único
        batch_textos.append(texto)              # texto que será armazenado
        batch_metadatas.append(metadata_limpa)  # campos para filtro no retrieval

        # ── envia o lote quando atinge BATCH_SIZE ─────────────────────────
        if len(batch_ids) >= BATCH_SIZE:
            # encode() gera os embeddings para todos os textos do lote de uma vez
            # show_progress_bar=False porque o tqdm externo já mostra o progresso
            embeddings = modelo.encode(
                batch_textos,
                show_progress_bar=False,
                convert_to_numpy=True    # ChromaDB espera numpy arrays ou listas
            ).tolist()                   # converte para lista de listas Python

            # upsert: insere se não existe, atualiza se já existe
            # mais seguro que add() para reexecuções parciais
            colecao.upsert(
                ids        = batch_ids,
                documents  = batch_textos,
                embeddings = embeddings,
                metadatas  = batch_metadatas,
            )

            total_indexados += len(batch_ids)   # conta quantos foram indexados

            # limpa os acumuladores para o próximo lote
            batch_ids        = []
            batch_textos     = []
            batch_metadatas  = []
            batch_embeddings = []

    # ── envia o lote final (pode ter menos que BATCH_SIZE) ────────────────
    if batch_ids:
        embeddings = modelo.encode(
            batch_textos,
            show_progress_bar=False,
            convert_to_numpy=True
        ).tolist()

        colecao.upsert(
            ids        = batch_ids,
            documents  = batch_textos,
            embeddings = embeddings,
            metadatas  = batch_metadatas,
        )

        total_indexados += len(batch_ids)   # conta o último lote

    # ── resumo final ──────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"✅ Chunks indexados agora:  {total_indexados}")
    print(f"⏭️  Já existiam (pulados):  {total_pulados}")
    print(f"❌ Erros:                   {total_erros}")
    print(f"📦 Total na coleção:        {colecao.count()}")
    print(f"💾 Vectorstore salvo em:    {PASTA_VECTORSTORE}/")

# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    # ── 1. carrega o modelo de embeddings ─────────────────────────────────
    print(f"Carregando modelo de embeddings: {MODELO_EMBEDDING}")
    print("(Na primeira vez, fará download de ~1 GB — aguarde)\n")
    modelo = SentenceTransformer(MODELO_EMBEDDING)
    # o modelo fica em cache local após o primeiro download
    # nas próximas execuções carrega do cache em segundos

    # ── 2. conecta ao ChromaDB (cria ou abre o banco existente) ───────────
    print(f"Conectando ao ChromaDB em: {PASTA_VECTORSTORE}/")
    client = chromadb.PersistentClient(path=PASTA_VECTORSTORE)
    # PersistentClient: salva tudo em disco automaticamente
    # se a pasta já tiver dados de uma execução anterior, eles são preservados

    # get_or_create_collection: abre a coleção se já existe, cria se não existe
    # hnsw:space=cosine → usa similaridade de cosseno (melhor para embeddings de texto)
    colecao = client.get_or_create_collection(
        name     = NOME_COLECAO,
        metadata = {"hnsw:space": "cosine"}
    )

    print(f"Coleção '{NOME_COLECAO}' carregada. Chunks já indexados: {colecao.count()}\n")

    # ── 3. lista todos os chunks disponíveis ──────────────────────────────
    arquivos = sorted([
        f for f in os.listdir(PASTA_CHUNKS) if f.endswith(".txt")
    ])
    # sorted() garante ordem alfabética — facilita depuração e retomada consistente

    print(f"Total de chunks encontrados na pasta: {len(arquivos)}\n")

    if not arquivos:
        print("⚠️  Nenhum arquivo .txt encontrado em", PASTA_CHUNKS)
        print("   Execute o chunking.py primeiro.")
        exit(0)   # encerra o script sem erro

    # ── 4. carrega IDs já indexados para evitar retrabalho ────────────────
    print("Verificando chunks já indexados...")
    ids_existentes = carregar_ids_existentes(colecao)
    novos = len(arquivos) - len(ids_existentes)
    print(f"  Já indexados: {len(ids_existentes)} | A indexar: {novos}\n")

    # ── 5. indexa os chunks novos ─────────────────────────────────────────
    processar_em_batches(arquivos, ids_existentes, colecao, modelo)
