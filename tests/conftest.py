"""
Preparação comum dos testes.

Os testes rodam sem rede, sem chaves de API e sem o índice real: a fixture
`acervo` cria um índice minúsculo em uma pasta temporária.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import config
import lexico

VIGENTE = "Situação:NÃO CONSTA REVOGAÇÃO EXPRESSA"
REVOGADA = "Situação:REVOGADA"

# (documento, título, situação, ementa, textos dos chunks, vetor de cada chunk)
DOCUMENTOS = [
    ("dsp20223683ti", "DSP - DESPACHO 3683/2022", VIGENTE, "Altera coordenadas geográficas de usinas fotovoltaicas.",
     ["DESPACHO Nº 3.683, DE 28 DE DEZEMBRO DE 2022. Altera as coordenadas geográficas das usinas.",
      "As usinas ficam no município de Janaúba, no estado de Minas Gerais."],
     [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]]),
    ("ren2016756", "REN - RESOLUÇÃO NORMATIVA 756/2016", REVOGADA, "Aprova os Procedimentos de Rede.",
     ["RESOLUÇÃO NORMATIVA Nº 756. Aprova a revisão dos Procedimentos de Rede."],
     [[0.0, 1.0, 0.0]]),
    ("prt2022092", "PRT - PORTARIA 092/2022", VIGENTE, "None",
     ["Concede Licença para Capacitação à servidora pelo período de trinta dias."],
     [[0.0, 0.0, 1.0]]),
]


class ModeloFalso:
    """Imita o modelo de embeddings: devolve um vetor fixo conforme uma palavra da pergunta."""

    def encode(self, texto, convert_to_numpy=True):
        texto = texto.lower()
        if "licença" in texto:
            return np.array([0.0, 0.0, 1.0])
        if "rede" in texto:
            return np.array([0.0, 1.0, 0.0])
        return np.array([1.0, 0.0, 0.0])


@pytest.fixture
def acervo(tmp_path, monkeypatch):
    """Cria um ChromaDB e um acervo léxico minúsculos e aponta a configuração para eles."""
    import chromadb

    pasta_indice = tmp_path / "vectorstore"
    monkeypatch.setattr(config, "PASTA_VECTORSTORE", str(pasta_indice))
    monkeypatch.setattr(config, "PASTA_LEXICO", str(tmp_path / "lexico"))

    cliente = chromadb.PersistentClient(path=str(pasta_indice))
    colecao = cliente.create_collection(config.NOME_COLECAO, metadata={"hnsw:space": "cosine"})
    for documento, titulo, situacao, ementa, textos, vetores in DOCUMENTOS:
        for n, (texto, vetor) in enumerate(zip(textos, vetores), 1):
            colecao.upsert(
                ids=[f"{documento}_chunk{n}"],
                documents=[texto],
                embeddings=[vetor],
                metadatas=[{
                    "titulo": titulo, "situacao": situacao, "ementa": ementa,
                    "publicacao": "Publicação:30/12/2022", "arquivo_original": f"{documento}.pdf",
                    "chunk_id": str(n), "chunk_total": str(len(textos)),
                }],
            )

    lexico.construir()
    yield colecao
    lexico.fechar()
