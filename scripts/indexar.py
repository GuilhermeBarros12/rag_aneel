import os                          # para navegar no sistema de arquivos
import re                          # para extrair o bloco YAML dos chunks com regex
import argparse                    # para receber argumentos via linha de comando
from pathlib import Path
from typing import Dict, List, Set, Tuple

from tqdm import tqdm              # barra de progresso visual no terminal

import chromadb                    # banco vetorial — persiste os embeddings em disco
from sentence_transformers import SentenceTransformer
# SentenceTransformer: carrega e roda o modelo de embeddings multilingual

# ============================================================
# CONFIGURAÇÕES PADRÃO
# ============================================================

# Caminhos resolvidos a partir da raiz do projeto (funciona de qualquer CWD)
ROOT = Path(__file__).resolve().parent.parent

PASTA_CHUNKS      = str(ROOT / "chunks")       # onde estão os .txt gerados pelo chunking.py
PASTA_VECTORSTORE = str(ROOT / "vectorstore")  # onde o ChromaDB vai salvar os dados em disco

NOME_COLECAO = "aneel_docs"           # nome da coleção dentro do ChromaDB

# modelo multilingual treinado para similaridade semântica em português
# NÃO trocar por all-MiniLM-L6-v2: esse é English-only (384 dims), muito inferior para PT-BR
MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

BATCH_SIZE = 64   # quantos chunks processa por vez
                  # valores maiores são mais rápidos mas consomem mais RAM
                  # 64 é seguro para ~8 GB de RAM; reduza para 32 se travar

# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================

def extrair_metadata_e_texto(conteudo: str) -> Tuple[Dict[str, str], str]:
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

    metadata: Dict[str, str] = {}

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

    return metadata, texto.strip()


def limpar_metadata_para_chroma(metadata: Dict[str, str]) -> Dict[str, str]:
    """
    ChromaDB só aceita valores de metadata dos tipos: str, int, float, bool.
    Nenhum campo pode ser None ou outro tipo.
    Esta função converte tudo para string e remove Nones.

    Parametro:
        metadata — dicionário com os campos do cabeçalho YAML
    Retorna:
        dicionário seguro para passar ao ChromaDB
    """

    metadata_limpa: Dict[str, str] = {}
    for chave, valor in metadata.items():
        metadata_limpa[chave] = "" if valor is None else str(valor)
    return metadata_limpa


def listar_chunks(pasta_chunks: str) -> List[str]:
    """
    Lista arquivos .txt da pasta de chunks em ordem alfabética.
    A ordem alfabética garante consistência entre execuções (facilita retomada).
    """

    if not os.path.exists(pasta_chunks):
        return []
    return sorted([f for f in os.listdir(pasta_chunks) if f.endswith(".txt")])


def carregar_ids_existentes(colecao) -> Set[str]:
    """
    Retorna um conjunto (set) com todos os IDs já indexados no ChromaDB.
    Usado para não re-indexar chunks que já estão no banco (retomada).

    Busca em paginas de 5000 para não sobrecarregar a memória.
    """

    ids_existentes: Set[str] = set()   # conjunto — busca por pertencimento é O(1)
    offset = 0                          # posição de início de cada pagina
    pagina = 5000                       # quantos IDs busca por vez

    while True:
        # include=[] → retorna só os IDs, sem embeddings/documentos (mais rápido)
        resultado = colecao.get(limit=pagina, offset=offset, include=[])
        ids_pagina: List[str] = resultado["ids"]

        if not ids_pagina:              # pagina vazia → chegou ao fim
            break

        ids_existentes.update(ids_pagina)   # adiciona ao conjunto total
        offset += pagina                     # avança para a próxima pagina

    return ids_existentes


# ============================================================
# INDEXAÇÃO
# ============================================================

def indexar_chunks(
    arquivos: List[str],
    pasta_chunks: str,
    ids_existentes: Set[str],
    colecao,
    modelo: SentenceTransformer,
) -> None:
    """
    Função principal de indexação.
    Percorre os arquivos de chunk, gera embeddings em lotes e salva no ChromaDB.

    Parametros:
        arquivos        — lista de nomes de arquivo .txt na pasta de chunks
        pasta_chunks    — caminho da pasta onde estão os .txt
        ids_existentes  — set com IDs já no ChromaDB (para pular)
        colecao         — objeto de coleção do ChromaDB
        modelo          — modelo SentenceTransformer carregado
    """

    # acumuladores do lote atual
    batch_ids:       List[str]            = []
    batch_textos:    List[str]            = []
    batch_metadatas: List[Dict[str, str]] = []

    total_indexados = 0    # chunks novos indexados nesta execução
    total_pulados   = 0    # chunks já existentes, pulados
    total_erros     = 0    # arquivos com erro de leitura ou texto vazio

    def _flush_batch() -> None:
        """Envia o lote acumulado para o ChromaDB e limpa os acumuladores."""
        nonlocal total_indexados

        embeddings = modelo.encode(
            batch_textos,
            show_progress_bar=False,
            convert_to_numpy=True,    # ChromaDB espera numpy arrays ou listas
        ).tolist()                    # converte para lista de listas Python

        # upsert: insere se não existe, atualiza se já existe
        # mais seguro que add() para reexecuções parciais
        colecao.upsert(
            ids       = batch_ids,
            documents = batch_textos,
            embeddings= embeddings,
            metadatas = batch_metadatas,
        )

        total_indexados += len(batch_ids)
        batch_ids.clear()
        batch_textos.clear()
        batch_metadatas.clear()

    # tqdm cria a barra de progresso — desc é o texto que aparece ao lado
    for nome_arquivo in tqdm(arquivos, desc="Indexando chunks", unit="chunk"):

        # o nome do arquivo (sem .txt) é o ID único do chunk no ChromaDB
        chunk_id = nome_arquivo.replace(".txt", "")
        # ex: "ndsp20163386_chunk1.txt" → "ndsp20163386_chunk1"

        # ── pula se já foi indexado ────────────────────────────────────────
        if chunk_id in ids_existentes:
            total_pulados += 1
            continue

        # ── lê o arquivo ──────────────────────────────────────────────────
        caminho = os.path.join(pasta_chunks, nome_arquivo)

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()
        except Exception as e:
            print(f"\n[ERRO] Falha ao ler {nome_arquivo}: {e}")
            total_erros += 1
            continue

        # ── extrai metadata e corpo do chunk ──────────────────────────────
        metadata, texto = extrair_metadata_e_texto(conteudo)

        if not texto:       # chunk vazio não tem o que indexar
            total_erros += 1
            continue

        metadata_limpa = limpar_metadata_para_chroma(metadata)

        # ── adiciona ao lote atual ─────────────────────────────────────────
        batch_ids.append(chunk_id)
        batch_textos.append(texto)
        batch_metadatas.append(metadata_limpa)

        # ── envia o lote quando atinge BATCH_SIZE ─────────────────────────
        if len(batch_ids) >= BATCH_SIZE:
            _flush_batch()

    # ── envia o lote final (pode ter menos que BATCH_SIZE) ────────────────
    if batch_ids:
        _flush_batch()

    # ── resumo final ──────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"[OK]  Chunks indexados agora:  {total_indexados}")
    print(f"[--]  Ja existiam (pulados):   {total_pulados}")
    print(f"[ERR] Erros:                   {total_erros}")
    print(f"[DB]  Total na colecao:        {colecao.count()}")
    print(f"[DIR] Vectorstore salvo em:    {PASTA_VECTORSTORE}/")


# ============================================================
# EXECUÇÃO
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Gera embeddings dos chunks e indexa no ChromaDB."
    )
    parser.add_argument(
        "--chunks-dir",
        default=PASTA_CHUNKS,
        help=f"Pasta com os .txt dos chunks. Padrao: {PASTA_CHUNKS}",
    )
    parser.add_argument(
        "--vectorstore-dir",
        default=PASTA_VECTORSTORE,
        help=f"Pasta onde o ChromaDB persiste os dados. Padrao: {PASTA_VECTORSTORE}",
    )
    parser.add_argument(
        "--colecao",
        default=NOME_COLECAO,
        help=f"Nome da colecao no ChromaDB. Padrao: {NOME_COLECAO}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Chunks por lote de embedding. Padrao: {BATCH_SIZE}",
    )
    args = parser.parse_args()

    os.makedirs(args.vectorstore_dir, exist_ok=True)

    # ── 1. lista todos os chunks disponíveis ──────────────────────────────
    arquivos = listar_chunks(args.chunks_dir)
    print(f"Total de chunks encontrados: {len(arquivos)}")

    if not arquivos:
        print(f"[AVISO] Nenhum .txt encontrado em: {args.chunks_dir}")
        print("        Execute o chunking.py antes deste script.")
        return

    # ── 2. carrega o modelo de embeddings ─────────────────────────────────
    print(f"\nCarregando modelo de embeddings: {MODELO_EMBEDDING}")
    print("(Na primeira vez, fara download de ~1 GB — aguarde)\n")
    modelo = SentenceTransformer(MODELO_EMBEDDING)
    # o modelo fica em cache local após o primeiro download
    # nas próximas execuções carrega do cache em segundos

    # ── 3. conecta ao ChromaDB (cria ou abre o banco existente) ───────────
    print(f"Conectando ao ChromaDB em: {args.vectorstore_dir}/")
    client = chromadb.PersistentClient(path=args.vectorstore_dir)
    # PersistentClient: salva tudo em disco automaticamente
    # se a pasta já tiver dados de uma execução anterior, eles são preservados

    # hnsw:space=cosine → similaridade de cosseno (melhor para embeddings de texto)
    colecao = client.get_or_create_collection(
        name     = args.colecao,
        metadata = {"hnsw:space": "cosine"},
    )

    print(f"Colecao '{args.colecao}' carregada. Chunks ja indexados: {colecao.count()}\n")

    # ── 4. carrega IDs já indexados para evitar retrabalho ────────────────
    print("Verificando chunks ja indexados...")
    ids_existentes = carregar_ids_existentes(colecao)
    novos = len(arquivos) - len(ids_existentes)
    print(f"  Ja indexados: {len(ids_existentes)} | A indexar: {novos}\n")

    # ── 5. indexa os chunks novos ─────────────────────────────────────────
    indexar_chunks(
        arquivos       = arquivos,
        pasta_chunks   = args.chunks_dir,
        ids_existentes = ids_existentes,
        colecao        = colecao,
        modelo         = modelo,
    )


if __name__ == "__main__":
    main()
