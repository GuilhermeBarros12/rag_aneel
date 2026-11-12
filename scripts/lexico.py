"""
Acervo léxico: um único arquivo SQLite com os textos dos chunks, a metadata dos
documentos e o índice BM25 (FTS5).

A busca vetorial é fraca para números de atos e CNPJs, e o BM25 cobre esse caso.
Como o arquivo também guarda os textos, o modo de busca "lexica" funciona sem o
ChromaDB e sem o modelo de embeddings.

Para construir a partir do índice vetorial: python scripts/lexico.py
"""

import json
import os
import re
import sqlite3
import threading
import unicodedata
from typing import Dict, List, Optional, Tuple

import config

VERSAO = "2"  # muda quando o formato do arquivo muda; arquivos antigos são recriados
LOTE = 5000   # chunks gravados por vez

# Palavras que aparecem em quase toda pergunta e não ajudam a separar documentos
STOPWORDS = {
    "a", "as", "o", "os", "um", "uma", "de", "da", "das", "do", "dos", "e", "em", "na", "nas",
    "no", "nos", "n", "nº", "para", "por", "pela", "pelo", "com", "que", "qual", "quais", "quem",
    "se", "sobre", "ao", "aos", "foi", "fica", "ficam", "segundo", "como", "quando", "ate",
}

# Campos que variam de chunk para chunk e por isso não entram na metadata do documento
CAMPOS_DO_CHUNK = {"chroma:document", "chunk_id", "chunk_total"}

# Uma conexão por thread: o SQLite não deixa uma conexão criada em uma thread ser usada
# em outra, e servidores web como o da demo atendem cada pergunta em uma thread diferente
_local = threading.local()


def caminho() -> str:
    return os.path.join(config.PASTA_LEXICO, config.ARQUIVO_LEXICO)


def normalizar_numeros(texto: str) -> str:
    """Tira o ponto de milhar: '3.683' vira '3683', como no título dos atos."""
    return re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", texto)


def documento_do_chunk(chunk_id: str) -> str:
    """'dsp20163386_chunk4' vira 'dsp20163386'."""
    return re.sub(r"_chunk\d+$", "", chunk_id)


# ============================================================
# CONEXÃO
# ============================================================


def conectar() -> sqlite3.Connection:
    """Abre o acervo em modo somente leitura e reaproveita a conexão desta thread."""
    if getattr(_local, "conexao", None) is None or _local.caminho != caminho():
        fechar()
        _local.conexao = sqlite3.connect(f"file:{caminho().replace(os.sep, '/')}?mode=ro", uri=True)
        _local.caminho = caminho()
    return _local.conexao


def fechar() -> None:
    """Fecha a conexão desta thread, se houver."""
    if getattr(_local, "conexao", None) is not None:
        _local.conexao.close()
    _local.conexao, _local.caminho = None, None


def existe() -> bool:
    """True se o arquivo existe e está no formato atual."""
    if not os.path.exists(caminho()):
        return False
    try:
        linha = conectar().execute("select valor from info where chave = 'versao'").fetchone()
    except sqlite3.Error:
        linha = None
    if linha is None or linha[0] != VERSAO:
        fechar()
        return False
    return True


def total() -> int:
    """Quantos chunks o acervo tem."""
    return int(conectar().execute("select valor from info where chave = 'chunks'").fetchone()[0])


# ============================================================
# CONSTRUÇÃO
# ============================================================


def construir() -> None:
    """Cria o acervo a partir dos chunks e da metadata guardados no ChromaDB."""

    os.makedirs(config.PASTA_LEXICO, exist_ok=True)
    fechar()
    origem = os.path.join(config.PASTA_VECTORSTORE, "chroma.sqlite3").replace("\\", "/")
    leitura = sqlite3.connect(f"file:{origem}?mode=ro&immutable=1", uri=True)

    temporario = caminho() + ".tmp"
    if os.path.exists(temporario):
        os.remove(temporario)
    db = sqlite3.connect(temporario)
    db.execute("pragma synchronous=off")
    db.execute("pragma journal_mode=off")
    db.execute("create table info(chave text primary key, valor text)")
    db.execute("create table documentos(id integer primary key, nome text unique, metadata text)")
    db.execute("create table chunks(rowid integer primary key, chunk_id text unique, documento integer, situacao text, texto text)")
    # content='' guarda só o índice de termos; os textos ficam uma vez só, na tabela chunks
    db.execute(
        "create virtual table busca using fts5("
        "titulo, ementa, texto, content='', tokenize='unicode61 remove_diacritics 2')"
    )

    documentos: Dict[str, int] = {}
    lote_chunks, lote_busca = [], []
    contagem = 0

    def gravar_chunk(chunk_id: str, campos: Dict[str, str]) -> None:
        nonlocal contagem
        contagem += 1
        nome = documento_do_chunk(chunk_id)
        if nome not in documentos:
            metadata = {k: v for k, v in campos.items() if k not in CAMPOS_DO_CHUNK}
            documentos[nome] = len(documentos) + 1
            db.execute("insert into documentos values (?, ?, ?)",
                       (documentos[nome], nome, json.dumps(metadata, ensure_ascii=False)))
        texto = campos.get("chroma:document", "")
        ementa = campos.get("ementa", "")
        ementa = "" if ementa == "None" else ementa
        lote_chunks.append((contagem, chunk_id, documentos[nome], campos.get("situacao"), texto))
        lote_busca.append((contagem, normalizar_numeros(campos.get("titulo", "")),
                           normalizar_numeros(ementa), normalizar_numeros(texto)))
        if len(lote_chunks) >= LOTE:
            descarregar()

    def descarregar() -> None:
        db.executemany("insert into chunks values (?, ?, ?, ?, ?)", lote_chunks)
        db.executemany("insert into busca(rowid, titulo, ementa, texto) values (?, ?, ?, ?)", lote_busca)
        db.commit()
        lote_chunks.clear()
        lote_busca.clear()
        if contagem % 50000 == 0:
            print(f"   {contagem} chunks")

    # O ChromaDB guarda uma linha por campo; as linhas de um mesmo chunk vêm juntas
    linhas = leitura.execute(
        """
        select m.id, e.embedding_id, m.key, coalesce(m.string_value, m.int_value, m.float_value)
        from embedding_metadata m join embeddings e on e.id = m.id
        order by m.id
        """
    )
    atual, chunk_id, campos = None, None, {}
    for id_interno, embedding_id, chave, valor in linhas:
        if id_interno != atual:
            if atual is not None:
                gravar_chunk(chunk_id, campos)
            atual, chunk_id, campos = id_interno, embedding_id, {}
        campos[chave] = "" if valor is None else str(valor)
    if atual is not None:
        gravar_chunk(chunk_id, campos)
    descarregar()

    db.executemany("insert into info values (?, ?)",
                   [("versao", VERSAO), ("chunks", str(contagem)), ("documentos", str(len(documentos)))])
    db.execute("insert into busca(busca) values ('optimize')")
    db.commit()
    db.close()
    leitura.close()
    os.replace(temporario, caminho())
    print(f"[OK] Acervo lexico criado com {contagem} chunks de {len(documentos)} documentos: {caminho()}")


def baixar() -> bool:
    """Tenta baixar o acervo pronto do Hugging Face. Devolve False se ele não estiver publicado."""
    try:
        from huggingface_hub import hf_hub_download

        os.makedirs(config.PASTA_LEXICO, exist_ok=True)
        hf_hub_download(
            repo_id=config.HF_REPO_ID,
            filename=config.ARQUIVO_LEXICO,
            repo_type="dataset",
            local_dir=config.PASTA_LEXICO,
        )
        return existe()
    except Exception:
        return False


# ============================================================
# BUSCA
# ============================================================


def montar_consulta(pergunta: str) -> str:
    """Transforma a pergunta em uma consulta OR do FTS5, sem acentos e sem stopwords."""
    texto = unicodedata.normalize("NFKD", normalizar_numeros(pergunta))
    texto = texto.encode("ascii", "ignore").decode().lower()
    termos = dict.fromkeys(t for t in re.findall(r"\w+", texto) if t not in STOPWORDS)
    return " OR ".join(f'"{t}"' for t in termos)


def buscar(pergunta: str, n: int, excluir_situacao: Optional[str] = None) -> List[str]:
    """Devolve os ids dos n chunks com melhor BM25."""

    consulta = montar_consulta(pergunta)
    if not consulta:
        return []

    peso_titulo, peso_ementa, peso_texto = config.PESOS_BM25
    filtro = "and c.situacao is not ?" if excluir_situacao else ""
    parametros = [consulta] + ([excluir_situacao] if excluir_situacao else []) + [n]
    # No FTS5, bm25() é menor quanto melhor o resultado
    linhas = conectar().execute(
        f"""
        select c.chunk_id
        from busca join chunks c on c.rowid = busca.rowid
        where busca match ? {filtro}
        order by bm25(busca, {peso_titulo}, {peso_ementa}, {peso_texto})
        limit ?
        """,
        parametros,
    ).fetchall()
    return [l[0] for l in linhas]


def carregar(ids: List[str]) -> List[Tuple[str, str, Dict[str, str]]]:
    """Devolve (id, texto, metadata do documento) de cada chunk, na ordem pedida."""

    if not ids:
        return []
    marcas = ",".join("?" * len(ids))
    linhas = conectar().execute(
        f"""
        select c.chunk_id, c.texto, d.metadata
        from chunks c join documentos d on d.id = c.documento
        where c.chunk_id in ({marcas})
        """,
        ids,
    ).fetchall()
    achados = {chunk_id: (chunk_id, texto, json.loads(metadata)) for chunk_id, texto, metadata in linhas}
    return [achados[i] for i in ids if i in achados]


if __name__ == "__main__":
    construir()
