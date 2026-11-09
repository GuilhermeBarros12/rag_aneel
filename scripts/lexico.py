"""
Índice léxico (BM25) sobre os chunks, em SQLite FTS5.

A busca vetorial é fraca para números de atos e CNPJs. Este índice cobre esse
caso e não exige recalcular embeddings: ele lê os textos do chroma.sqlite3.

Para construir: python scripts/lexico.py
"""

import os
import re
import sqlite3
import unicodedata
from typing import List, Optional

import config

CAMINHO = os.path.join(config.PASTA_LEXICO, "lexico.sqlite3")

# Palavras que aparecem em quase toda pergunta e não ajudam a separar documentos
STOPWORDS = {
    "a", "as", "o", "os", "um", "uma", "de", "da", "das", "do", "dos", "e", "em", "na", "nas",
    "no", "nos", "n", "nº", "para", "por", "pela", "pelo", "com", "que", "qual", "quais", "quem",
    "se", "sobre", "ao", "aos", "foi", "fica", "ficam", "segundo", "como", "quando", "ate",
}

_conexao: Optional[sqlite3.Connection] = None


def normalizar_numeros(texto: str) -> str:
    """Tira o ponto de milhar: '3.683' vira '3683', como no título dos atos."""
    return re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", texto)


def existe() -> bool:
    return os.path.exists(CAMINHO)


def construir() -> None:
    """Cria o índice a partir dos chunks já guardados no ChromaDB."""

    os.makedirs(config.PASTA_LEXICO, exist_ok=True)
    origem = os.path.join(config.PASTA_VECTORSTORE, "chroma.sqlite3").replace("\\", "/")
    leitura = sqlite3.connect(f"file:{origem}?mode=ro&immutable=1", uri=True)

    temporario = CAMINHO + ".tmp"
    if os.path.exists(temporario):
        os.remove(temporario)
    db = sqlite3.connect(temporario)
    db.execute("pragma synchronous=off")
    db.execute("pragma journal_mode=off")
    db.execute("create table chunks(rowid integer primary key, chunk_id text, situacao text)")
    # content='' guarda só o índice, sem duplicar os textos no disco
    db.execute(
        "create virtual table busca using fts5("
        "titulo, ementa, texto, content='', tokenize='unicode61 remove_diacritics 2')"
    )

    linhas = leitura.execute(
        """
        select e.embedding_id, d.string_value, t.string_value, em.string_value, s.string_value
        from embeddings e
        join embedding_metadata d on d.id = e.id and d.key = 'chroma:document'
        left join embedding_metadata t on t.id = e.id and t.key = 'titulo'
        left join embedding_metadata em on em.id = e.id and em.key = 'ementa'
        left join embedding_metadata s on s.id = e.id and s.key = 'situacao'
        """
    )

    total = 0
    for chunk_id, texto, titulo, ementa, situacao in linhas:
        total += 1
        db.execute("insert into chunks values (?, ?, ?)", (total, chunk_id, situacao))
        ementa = "" if ementa in (None, "None") else ementa
        db.execute(
            "insert into busca(rowid, titulo, ementa, texto) values (?, ?, ?, ?)",
            (total, normalizar_numeros(titulo or ""), normalizar_numeros(ementa), normalizar_numeros(texto)),
        )
        if total % 50000 == 0:
            db.commit()
            print(f"   {total} chunks")

    db.commit()
    db.execute("insert into busca(busca) values ('optimize')")
    db.commit()
    db.close()
    leitura.close()
    os.replace(temporario, CAMINHO)
    print(f"[OK] Indice lexico criado com {total} chunks: {CAMINHO}")


def montar_consulta(pergunta: str) -> str:
    """Transforma a pergunta em uma consulta OR do FTS5, sem acentos e sem stopwords."""
    texto = unicodedata.normalize("NFKD", normalizar_numeros(pergunta))
    texto = texto.encode("ascii", "ignore").decode().lower()
    termos = dict.fromkeys(t for t in re.findall(r"\w+", texto) if t not in STOPWORDS)
    return " OR ".join(f'"{t}"' for t in termos)


def buscar(pergunta: str, n: int, excluir_situacao: Optional[str] = None) -> List[str]:
    """Devolve os ids dos n chunks com melhor BM25."""

    global _conexao
    if _conexao is None:
        _conexao = sqlite3.connect(f"file:{CAMINHO.replace(chr(92), '/')}?mode=ro", uri=True)

    consulta = montar_consulta(pergunta)
    if not consulta:
        return []

    peso_titulo, peso_ementa, peso_texto = config.PESOS_BM25
    filtro = "and c.situacao is not ?" if excluir_situacao else ""
    parametros = [consulta] + ([excluir_situacao] if excluir_situacao else []) + [n]
    # No FTS5, bm25() é menor quanto melhor o resultado
    linhas = _conexao.execute(
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


if __name__ == "__main__":
    construir()
