"""
Sorteia um grupo pequeno de perguntas do conjunto de ouro congelado, para testar LLMs
gastando pouca cota: 2 perguntas de cada tipo, incluindo 2 que devem ser recusadas.

Uso: python scripts/mini_conjunto.py
"""

import json
import os
import random

import config

SEMENTE = 2027
POR_GRUPO = 2
GRUPOS = ["ato_citado", "fato_com_ato", "fato_sem_ato", "revogado", "recusar"]


def main() -> None:
    with open(os.path.join(config.PASTA_DOCS_AVALIACAO, "conjunto_ouro.json"), encoding="utf-8") as f:
        perguntas = json.load(f)["perguntas"]

    rng = random.Random(SEMENTE)
    escolhidas = []
    for grupo in GRUPOS:
        candidatas = [q for q in perguntas if (q["deve_recusar"] if grupo == "recusar" else q["categoria"] == grupo)]
        escolhidas += rng.sample(candidatas, POR_GRUPO)

    destino = os.path.join(config.PASTA_DOCS_AVALIACAO, "conjunto_mini_llm.json")
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"status": "derivado do conjunto_ouro.json congelado", "semente": SEMENTE,
                   "perguntas": escolhidas}, f, ensure_ascii=False, indent=1)
    for q in escolhidas:
        print(q["id"], q["categoria"], "|", q["pergunta"])


if __name__ == "__main__":
    main()
