import os
import json
import time
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

import chromadb
from sentence_transformers import SentenceTransformer
from datasets import Dataset      # formato que o RAGAS espera
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

ROOT              = Path(__file__).resolve().parent.parent
PASTA_VECTORSTORE = str(ROOT / "vectorstore")
PASTA_RESULTADOS  = str(ROOT / "avaliacao")       # onde salvar os resultados
NOME_COLECAO      = "aneel_docs"
MODELO_EMBEDDING  = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
TOP_K             = 5             # chunks recuperados por pergunta
DELAY_ENTRE_PERGUNTAS = 2         # segundos entre chamadas à API — evita rate limit

load_dotenv(dotenv_path=ROOT / ".env")   # carrega GEMINI_API_KEY e GROQ_API_KEY

os.makedirs(PASTA_RESULTADOS, exist_ok=True)  # cria pasta de resultados se não existir

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
# RETRIEVAL
# ============================================================

def recuperar_chunks(
    query: str,
    colecao,
    modelo: SentenceTransformer,
    top_k: int = TOP_K,
) -> List[str]:
    """
    Embeda a query e busca os top_k chunks mais similares.
    Filtra documentos revogados automaticamente.
    """
    embedding = modelo.encode(query, convert_to_numpy=True).tolist()

    resultado = colecao.query(
        query_embeddings = [embedding],
        n_results        = top_k,
        include          = ["documents", "metadatas", "distances"],
        where            = {"situacao": {"$ne": "Situação:REVOGADA"}},
        # filtra documentos revogados — não retorna legislação obsoleta
    )

    return resultado["documents"][0]   # lista de textos dos chunks

# ============================================================
# GERAÇÃO
# ============================================================

PROMPT_TEMPLATE = """Você é um assistente especializado em regulação do setor elétrico brasileiro.
Responda à pergunta usando APENAS as informações dos trechos regulatórios abaixo.
Se a resposta não estiver nos trechos, responda exatamente: "Não encontrei informação suficiente nos documentos disponíveis."
Seja objetivo e cite o documento relevante quando possível.

--- TRECHOS RECUPERADOS ---
{contexto}
--- FIM DOS TRECHOS ---

Pergunta: {query}
Resposta:"""

def montar_prompt(query: str, chunks: List[str]) -> str:
    """Monta o prompt com os chunks como contexto."""
    contexto = "\n\n---\n\n".join(
        f"[Trecho {i+1}]\n{chunk}" for i, chunk in enumerate(chunks)
    )
    return PROMPT_TEMPLATE.format(contexto=contexto, query=query)

def gerar_com_gemini(prompt: str) -> str:
    """Chama o Gemini 1.5 Flash como LLM primário."""
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não configurada no .env")
    genai.configure(api_key=api_key)
    model    = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()

def gerar_com_groq(prompt: str) -> str:
    """Chama o Groq Llama 3.3 70B como fallback."""
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY não configurada no .env")
    client   = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model    = "llama-3.3-70b-versatile",
        messages = [{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

def gerar_resposta(prompt: str) -> str:
    """Tenta Gemini primeiro, usa Groq como fallback."""
    try:
        return gerar_com_gemini(prompt)
    except Exception as e_gemini:
        print(f"   [AVISO] Gemini falhou ({e_gemini}). Usando Groq...")
        try:
            return gerar_com_groq(prompt)
        except Exception as e_groq:
            return f"[ERRO] Nenhum LLM disponível. Gemini: {e_gemini} | Groq: {e_groq}"

# ============================================================
# PIPELINE DE AVALIAÇÃO
# ============================================================

def rodar_benchmark(colecao, modelo: SentenceTransformer) -> List[Dict]:
    """
    Roda todas as 100 perguntas e coleta:
    - pergunta
    - chunks recuperados
    - resposta gerada
    Salva progresso em disco a cada 10 perguntas (retomada se travar).
    """
    resultados    = []
    arquivo_parcial = os.path.join(PASTA_RESULTADOS, "resultados_parciais.json")

    # carrega resultados parciais se existirem (retomada)
    perguntas_feitas = set()
    if os.path.exists(arquivo_parcial):
        with open(arquivo_parcial, "r", encoding="utf-8") as f:
            resultados = json.load(f)
        perguntas_feitas = {r["pergunta"] for r in resultados}
        print(f"[RETOMADA] {len(perguntas_feitas)} perguntas já respondidas — continuando...\n")

    total = len(PERGUNTAS)

    for i, pergunta in enumerate(PERGUNTAS):

        # pula perguntas já respondidas (retomada)
        if pergunta in perguntas_feitas:
            continue

        print(f"[{i+1}/{total}] {pergunta[:70]}...")

        # 1. recupera chunks relevantes
        chunks = recuperar_chunks(pergunta, colecao, modelo)

        # 2. monta o prompt e gera a resposta
        prompt   = montar_prompt(pergunta, chunks)
        resposta = gerar_resposta(prompt)

        print(f"   → {resposta[:100]}...")

        # 3. salva o resultado
        resultados.append({
            "pergunta":  pergunta,
            "contextos": chunks,       # lista de chunks recuperados
            "resposta":  resposta,     # resposta gerada pelo LLM
        })

        # salva progresso a cada 10 perguntas
        if len(resultados) % 10 == 0:
            with open(arquivo_parcial, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            print(f"   [SALVO] Progresso salvo ({len(resultados)}/{total})\n")

        time.sleep(DELAY_ENTRE_PERGUNTAS)   # pausa entre perguntas — evita rate limit

    # salva o arquivo final completo
    arquivo_final = os.path.join(PASTA_RESULTADOS, "resultados_completos.json")
    with open(arquivo_final, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(resultados)} perguntas respondidas.")
    print(f"📁 Resultados salvos em: {arquivo_final}")

    return resultados

# ============================================================
# AVALIAÇÃO COM RAGAS
# ============================================================

def avaliar_com_ragas(resultados: List[Dict]) -> None:
    """
    Roda o RAGAS nas respostas coletadas e imprime os scores.
    Salva o relatório em JSON para análise posterior.
    """
    print("\n" + "=" * 50)
    print("Iniciando avaliação com RAGAS...")
    print("=" * 50 + "\n")

    # monta o dataset no formato que o RAGAS espera
    dataset = Dataset.from_dict({
        "question": [r["pergunta"]  for r in resultados],
        "answer":   [r["resposta"]  for r in resultados],
        "contexts": [r["contextos"] for r in resultados],
        # ground_truth não é obrigatório para as métricas que usamos
    })

    # roda a avaliação — pode demorar alguns minutos
    resultado_ragas = evaluate(
        dataset,
        metrics=[
            faithfulness,      # resposta é fiel aos chunks?
            answer_relevancy,  # resposta é relevante para a pergunta?
            context_precision, # chunks recuperados são precisos?
        ],
    )

    # converte para dicionário para salvar
    scores = {
        "faithfulness":      resultado_ragas["faithfulness"],
        "answer_relevancy":  resultado_ragas["answer_relevancy"],
        "context_precision": resultado_ragas["context_precision"],
    }

    # imprime os scores
    print("\n📊 SCORES RAGAS:")
    print(f"   Faithfulness:      {scores['faithfulness']:.3f}  (fidelidade ao contexto)")
    print(f"   Answer Relevancy:  {scores['answer_relevancy']:.3f}  (relevância da resposta)")
    print(f"   Context Precision: {scores['context_precision']:.3f}  (precisão dos chunks)")

    # interpretação automática dos scores
    print("\n📋 DIAGNÓSTICO:")
    if scores["faithfulness"] < 0.7:
        print("   ⚠️  Faithfulness baixo → LLM está inventando além do contexto. Reforçar o prompt.")
    if scores["answer_relevancy"] < 0.7:
        print("   ⚠️  Answer Relevancy baixo → Respostas não estão respondendo a pergunta. Revisar o prompt.")
    if scores["context_precision"] < 0.7:
        print("   ⚠️  Context Precision baixo → Chunks errados sendo recuperados. Ajustar chunk_size ou embedding.")
    if all(v >= 0.7 for v in scores.values()):
        print("   ✅ Todos os scores acima de 0.7 — pipeline funcionando bem!")

    # salva o relatório
    arquivo_ragas = os.path.join(PASTA_RESULTADOS, "scores_ragas.json")
    with open(arquivo_ragas, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Scores salvos em: {arquivo_ragas}")

# ============================================================
# EXECUÇÃO
# ============================================================

def main() -> None:

    # 1. carrega o modelo de embeddings
    print(f"Carregando modelo de embeddings: {MODELO_EMBEDDING}")
    modelo = SentenceTransformer(MODELO_EMBEDDING)
    print("[OK] Modelo carregado.\n")

    # 2. conecta ao ChromaDB
    print(f"Conectando ao ChromaDB em: {PASTA_VECTORSTORE}")
    client  = chromadb.PersistentClient(path=PASTA_VECTORSTORE)
    colecao = client.get_collection(name=NOME_COLECAO)
    print(f"[OK] ChromaDB conectado. {colecao.count()} chunks indexados.\n")

    # 3. roda o benchmark e coleta respostas
    resultados = rodar_benchmark(colecao, modelo)

    # 4. avalia com RAGAS
    avaliar_com_ragas(resultados)

if __name__ == "__main__":
    main() 