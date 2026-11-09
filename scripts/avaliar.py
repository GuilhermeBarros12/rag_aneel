"""
Benchmark de 100 perguntas: roda o mesmo código do pipeline (nucleo.py) e salva,
para cada pergunta, a resposta, o LLM que respondeu e os documentos usados.

As métricas ainda não fazem parte deste script. Para elas é preciso um conjunto
de perguntas com documento e resposta esperados.
"""

import argparse
import collections
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List

import config
from nucleo import carregar_recursos, responder

DELAY_ENTRE_PERGUNTAS = 2  # segundos entre chamadas à API, para evitar rate limit

# ============================================================
# PERGUNTAS DO BENCHMARK
# ============================================================

PERGUNTAS = [
    # CATEGORIA 1 — Identificação de Documentos
    "O que é o Despacho ANEEL nº 3.284 de 2016?",
    "Qual o assunto da Resolução Normativa ANEEL nº 756 de 2016?",
    "O que determina o Despacho nº 3.683 de 2022?",
    "Qual órgão da ANEEL assinou o Despacho nº 3.386 de 2016?",
    "Qual é a ementa da Resolução Normativa nº 754 de 2016?",
    "O que é o Despacho nº 3.398 de 2016 da SCG/ANEEL?",
    "Qual o número do processo administrativo relacionado ao Despacho 3.284/2016?",
    "O que determina a Portaria ANEEL nº 4.241 de 2016?",
    "Qual a data de publicação da Resolução Normativa nº 749 de 2016?",
    "O que é a Resolução Homologatória ANEEL nº 2.014 de 2016?",

    # CATEGORIA 2 — Dados Técnicos e Numéricos
    "Qual a potência declarada das Centrais Geradoras Solares Fotovoltaicas alteradas pelo Despacho 3.683/2022?",
    "Quantas unidades geradoras foram alteradas pelo Despacho 3.683/2022?",
    "Qual o município onde estão localizadas as usinas solares do Despacho 3.683/2022?",
    "Qual a potência unitária das centrais solares mencionadas no Despacho 3.683/2022?",
    "Qual o número de processo administrativo do Despacho 3.683/2022?",
    "Quais são as coordenadas geográficas alteradas pelo Despacho 3.683/2022?",
    "Qual a tensão nominal do sistema de transmissão de interesse restrito mencionado no Despacho 3.683/2022?",
    "Qual o valor da multa mencionada no Despacho 3.400/2016 antes da reconsideração?",
    "Qual o resultado financeiro do leilão mencionado na Resolução Homologatória 2.014/2016?",
    "Quantos módulos compõem o anexo da Resolução Normativa 756/2016?",

    # CATEGORIA 3 — Titularidade e Empresas
    "Quem é o titular das Centrais Geradoras Solares Fotovoltaicas mencionadas no Despacho 3.683/2022?",
    "Quem é o titular da PCH São Carlos mencionada no Despacho 3.386/2016?",
    "Quem foi hierarquizado em primeiro lugar para implantação da PCH COR 125?",
    "Quem detinha o registro ativo do projeto básico da PCH COR 125 antes do Despacho 3.398/2016?",
    "Qual empresa é titular da PCH Cachoeira Alegre mencionada no Despacho 3.408/2016?",
    "Quem é a Boa Vista Energia S.A. no contexto do Despacho 3.400/2016?",
    "Quem são os sócios da Tradener Ltda mencionados nos despachos de 2016?",
    "Qual empresa recebeu o registro de intenção à outorga da PCH Eixo 1?",
    "Quem assinou o Despacho 3.284/2016 como Diretor-Geral da ANEEL?",
    "Quais são os municípios de localização da PCH COR 125?",

    # CATEGORIA 4 — Localização e Corpos Hídricos
    "Em qual rio está localizada a PCH São Carlos?",
    "Em quais municípios está localizada a PCH São Carlos?",
    "Em qual estado está localizada a PCH São Carlos?",
    "Em qual rio está localizada a PCH Cachoeira Alegre?",
    "Em qual município está localizada a PCH Cachoeira Alegre?",
    "Em qual ribeirão está localizada a PCH Eixo 1?",
    "Em quais municípios está localizada a PCH Eixo 1?",
    "Em qual estado está localizada a PCH Eixo 1?",
    "Em qual rio está localizada a PCH COR 125?",
    "Em quais municípios está localizada a PCH COR 125?",

    # CATEGORIA 5 — Situação Normativa e Vigência
    "A Resolução Normativa ANEEL nº 756/2016 está vigente ou foi revogada?",
    "O Despacho 3.407/2016 está vigente?",
    "Quais resoluções de 2016 foram expressamente revogadas?",
    "O Despacho 3.386/2016 consta alguma revogação expressa?",
    "A Portaria ANEEL nº 3.936/2016 está vigente?",
    "Qual documento revogou o Despacho SCG/ANEEL 4.471 de 2014?",
    "O Despacho 3.398/2016 revogou algum ato anterior?",
    "Quais documentos de 2021 constam como revogados na base?",
    "O Despacho 3.400/2016 está vigente?",
    "Qual a situação normativa da Resolução Normativa 731/2016?",

    # CATEGORIA 6 — Procedimentos e Decisões Administrativas
    "O que significa acatar a recomendação da Comissão Permanente de Procedimentos Administrativos Disciplinares?",
    "Quais não conformidades do Auto de Infração SFF/ANEEL 051/2016 foram convertidas em advertência?",
    "O que aconteceu com o recurso administrativo da Boa Vista Energia no Despacho 3.400/2016?",
    "O que é um Auto de Infração no contexto da regulação da ANEEL?",
    "O que significa hierarquizar em primeiro lugar no contexto de outorga de PCH?",
    "O que é o registro de intenção à outorga de autorização de PCH?",
    "Qual é a diferença entre Texto Integral e Nota Técnica nos despachos da ANEEL?",
    "O que é adequabilidade aos estudos de inventário no contexto de PCH?",
    "O que significa uso do potencial hidráulico nos despachos de autorização?",
    "Qual é o papel da SCG/ANEEL nos despachos de registro de PCH?",

    # CATEGORIA 7 — Múltiplas Respostas
    "Liste todas as PCHs mencionadas nos despachos de dezembro de 2016.",
    "Quais empresas tiveram registros de PCH concedidos em 2016?",
    "Quais municípios do estado de Goiás aparecem nos documentos da base?",
    "Liste todos os despachos publicados em 30 de dezembro de 2016.",
    "Quais são os tipos de documentos presentes na base da ANEEL?",
    "Quais empresas sofreram autuações da ANEEL em 2016?",
    "Liste todas as resoluções normativas de 2016 presentes na base.",
    "Quais PCHs estão localizadas em Santa Catarina?",
    "Quais são os diferentes assuntos dos despachos de 2016?",
    "Liste todos os documentos relacionados à Resolução Normativa 756/2016.",

    # CATEGORIA 8A — Teste de Alucinação
    "Qual a tarifa de energia cobrada pela ANEEL em janeiro de 2016?",
    "Quem é o presidente da ANEEL em 2026?",
    "Qual o valor do megawatt-hora no leilão de energia de 2023?",
    "Qual a multa máxima que a ANEEL pode aplicar a uma distribuidora?",
    "Quantos funcionários tem a ANEEL atualmente?",

    # CATEGORIA 8B — Precisão entre Documentos Similares
    "Qual a diferença entre o Despacho 3.398/2016 e o Despacho 3.399/2016?",
    "Qual PCH foi registrada pelo Despacho 3.386/2016 e qual foi registrada pelo 3.408/2016?",
    "Quais são as diferenças entre os projetos PCH COR 125 e PCH Cachoeira Alegre?",
    "O Despacho 3.399/2016 e o 3.408/2016 envolvem o mesmo corpo hídrico?",
    "Qual a diferença entre os titulares da PCH São Carlos e da PCH Cachoeira Alegre?",

    # CATEGORIA 8C — Contexto Temporal
    "Quais documentos foram assinados em 28 de dezembro de 2016?",
    "Quais documentos foram publicados antes de 25 de dezembro de 2016?",
    "Qual foi o último despacho publicado em 2016 na base?",
    "Quais documentos de 2021 tratam de resolução homologatória?",
    "Quantos documentos de 2022 estão presentes na base?",

    # CATEGORIA 8D — Documentos Revogados
    "O que diz o Despacho 3.407/2016 sobre a PCH Eixo 1?",
    "O Despacho SCG/ANEEL 4.471 de 2014 ainda está em vigor?",
    "Qual era o conteúdo do registro ativo revogado pelo Despacho 3.398/2016?",
    "A Agrícola Sete Campos Ltda ainda tem direito sobre a PCH Eixo 1?",
    "O que aconteceu com o projeto da PCH COR 125 da Optigera S.A.?",

    # CATEGORIA 8E — Qualidade do Chunking (contexto amplo)
    "Descreva o processo completo de autorização de uma Pequena Central Hidrelétrica segundo os documentos da ANEEL.",
    "Quais são todas as etapas para regularização de uma usina solar fotovoltaica segundo os documentos?",
    "Como a ANEEL trata recursos administrativos contra autos de infração com base nos documentos disponíveis?",
    "Quais são os critérios para hierarquização de interessados na implantação de PCHs?",
    "Descreva o papel da Nota Técnica no processo de decisão da ANEEL.",

    # CATEGORIA 8F — Raciocínio Multi-documento
    "Com base nos documentos disponíveis, qual estado brasileiro tem mais PCHs registradas?",
    "Qual o padrão de nomenclatura dos arquivos de Texto Integral dos despachos da ANEEL?",
    "Com base nos documentos, quais são os diferentes tipos de penalidade que a ANEEL pode aplicar?",
    "Comparando os despachos de 2016 e 2022, houve mudança no tipo de empreendimento mais frequente?",
    "Com base em todos os documentos disponíveis, qual é o setor de geração de energia mais regulado pela ANEEL?",
]

# ============================================================
# BENCHMARK
# ============================================================


def salvar_json(caminho: str, dados) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def rodar_benchmark(colecao, modelo, limite: int) -> List[Dict]:
    """
    Roda as perguntas e salva o progresso a cada 10, permitindo retomar.
    Para na primeira pergunta em que nenhum LLM responder, para que erro
    de API nunca seja salvo como se fosse resposta do sistema.
    """

    os.makedirs(config.PASTA_RESULTADOS, exist_ok=True)
    arquivo_parcial = os.path.join(config.PASTA_RESULTADOS, "resultados_parciais.json")

    resultados: List[Dict] = []
    if os.path.exists(arquivo_parcial):
        with open(arquivo_parcial, "r", encoding="utf-8") as f:
            resultados = json.load(f)
        print(f"[RETOMADA] {len(resultados)} perguntas ja respondidas.\n")
    feitas = {r["pergunta"] for r in resultados}

    perguntas = PERGUNTAS[:limite]
    for i, pergunta in enumerate(perguntas, 1):
        if pergunta in feitas:
            continue

        print(f"[{i}/{len(perguntas)}] {pergunta[:70]}")
        r = responder(pergunta, colecao, modelo)

        if r.llm is None:
            salvar_json(arquivo_parcial, resultados)
            print(r.resposta)
            raise SystemExit("[ERRO] Benchmark interrompido; progresso salvo.")

        print(f"   [{r.llm}] {r.resposta[:100]}")
        resultados.append(r.para_dict())

        if len(resultados) % 10 == 0:
            salvar_json(arquivo_parcial, resultados)
            print(f"   [SALVO] {len(resultados)}/{len(perguntas)}\n")

        time.sleep(DELAY_ENTRE_PERGUNTAS)

    salvar_json(arquivo_parcial, resultados)
    return resultados


def main() -> None:

    parser = argparse.ArgumentParser(description="Roda o benchmark de perguntas do RAG ANEEL.")
    parser.add_argument(
        "--limite",
        type=int,
        default=len(PERGUNTAS),
        help=f"Quantas perguntas rodar. Padrao: todas ({len(PERGUNTAS)})",
    )
    args = parser.parse_args()

    colecao, modelo = carregar_recursos()
    resultados = rodar_benchmark(colecao, modelo, args.limite)

    arquivo_final = os.path.join(config.PASTA_RESULTADOS, "resultados_completos.json")
    salvar_json(arquivo_final, {
        "configuracao": {
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "modelo_embedding": config.MODELO_EMBEDDING,
            "gemini": config.GEMINI_MODELO,
            "groq": config.GROQ_MODELO,
            "temperatura": config.TEMPERATURA,
            "top_k": config.TOP_K,
            "filtro": config.FILTRO_PADRAO,
        },
        "resultados": resultados,
    })

    print(f"\n{len(resultados)} perguntas respondidas.")
    print("Respostas por LLM:", dict(collections.Counter(r["llm"] for r in resultados)))
    print(f"Resultados salvos em: {arquivo_final}")


if __name__ == "__main__":
    main()
