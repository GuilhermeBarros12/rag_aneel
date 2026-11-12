"""
Recalcula a métrica "termos esperados" de resultados já salvos, usando as respostas
gravadas no JSON, sem chamar o LLM de novo. Útil quando a conferência de termos muda.

Uso: python scripts/recontar_termos.py docs/avaliacao/experimentos/llm_gpt_oss_120b.json [...]
"""

import json
import os
import sys

import config
from avaliar_ouro import contem_termos, escrever_relatorio, resumir_geracao


def main() -> None:
    for caminho in sys.argv[1:]:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        with open(os.path.join(config.PASTA_DOCS_AVALIACAO, dados["conjunto"]), encoding="utf-8") as f:
            termos = {q["id"]: q["termos"] for q in json.load(f)["perguntas"]}
        mudaram = 0
        for linha in dados["geracao"]["detalhe"]:
            if not termos.get(linha["id"]):
                continue
            novo = contem_termos(linha["resposta"], termos[linha["id"]])
            mudaram += novo != linha["termos_ok"]
            linha["termos_ok"] = novo
        dados["geracao"]["resumo"] = resumir_geracao(dados["geracao"]["detalhe"])
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        escrever_relatorio(caminho[:-5] + ".md", dados)
        print(f"{os.path.basename(caminho)}: {mudaram} respostas mudaram de classificação")


if __name__ == "__main__":
    main()
