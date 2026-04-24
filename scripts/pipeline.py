import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Carrega as variáveis do .env (GEMINI_API_KEY, GROQ_API_KEY, etc.)
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

import chromadb
from sentence_transformers import SentenceTransformer

# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_VECTORSTORE = str(ROOT / "vectorstore")

# Mesmo modelo usado na indexação — NUNCA trocar, senão os vetores ficam incompatíveis
MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

NOME_COLECAO = "aneel_docs"

# Quantos chunks recuperar por query (ajustável via .env ou argparse)
TOP_K = int(os.getenv("TOP_K", "5"))

# Repositório HF com o vectorstore pré-construído
HF_REPO_ID = os.getenv("HF_REPO_ID", "")

# ============================================================
# DOWNLOAD AUTOMÁTICO DO VECTORSTORE (Hugging Face Hub)
# ============================================================

def garantir_vectorstore() -> None:
    """
    Verifica se o vectorstore local existe e está populado.
    Se não existir, baixa automaticamente do Hugging Face Hub.

    O vectorstore contém o índice ChromaDB com ~168K chunks do corpus ANEEL,
    já embedados com paraphrase-multilingual-mpnet-base-v2.
    """

    chroma_db_path = os.path.join(PASTA_VECTORSTORE, "chroma.sqlite3")

    if os.path.exists(chroma_db_path):
        print("[OK] Vectorstore encontrado localmente.")
        return

    if not HF_REPO_ID:
        print("[ERRO] Vectorstore nao encontrado localmente.")
        print("       Configure HF_REPO_ID no .env ou baixe manualmente.")
        print("       Exemplo: HF_REPO_ID=seu-usuario/aneel-vectorstore")
        sys.exit(1)

    print(f"Vectorstore nao encontrado. Baixando de: {HF_REPO_ID}")
    print("(Primeira execucao: pode demorar alguns minutos dependendo da conexao)\n")

    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id    = HF_REPO_ID,
            repo_type  = "dataset",
            local_dir  = PASTA_VECTORSTORE,
        )
        print("[OK] Vectorstore baixado com sucesso.\n")

    except Exception as e:
        print(f"[ERRO] Falha ao baixar o vectorstore: {e}")
        print("       Verifique sua conexao e o valor de HF_REPO_ID no .env")
        sys.exit(1)


# ============================================================
# RETRIEVER — busca os chunks mais relevantes no ChromaDB
# ============================================================

def recuperar_chunks(
    query: str,
    colecao,
    modelo: SentenceTransformer,
    top_k: int = TOP_K,
    filtro: Optional[dict] = None,
) -> List[str]:
    """
    Embeda a query e busca os top_k chunks mais similares no ChromaDB.

    Parametros:
        query   — pergunta do usuário em texto livre
        colecao — coleção ChromaDB já conectada
        modelo  — modelo SentenceTransformer (mesmo da indexação)
        top_k   — quantos chunks retornar
        filtro  — dict de filtros de metadata (ex: {"tipo_documento": "Resolucao"})

    Retorna:
        lista de strings com os textos dos chunks recuperados
    """

    # Embeda a query com o mesmo modelo usado na indexação
    query_embedding = modelo.encode(query, convert_to_numpy=True).tolist()

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results":        top_k,
        "include":          ["documents", "metadatas", "distances"],
    }

    # Filtro opcional por metadata (ex: tipo de documento, ano)
    if filtro:
        kwargs["where"] = filtro

    resultado = colecao.query(**kwargs)

    # resultado["documents"] é uma lista de listas (uma por query)
    chunks = resultado["documents"][0]   # pega a lista da única query enviada
    return chunks


# ============================================================
# GERADOR — monta o prompt e chama o LLM
# ============================================================

PROMPT_TEMPLATE = """Você é um assistente especializado em regulação do setor elétrico brasileiro.
Responda à pergunta usando APENAS as informações dos trechos regulatórios abaixo.
Se a resposta não estiver nos trechos, responda: "Não encontrei informação suficiente nos documentos disponíveis."
Seja objetivo e cite o trecho relevante quando possível.

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
    """
    Chama a API do Gemini 1.5 Flash (LLM primário, gratuito).
    Lança exceção se a key não estiver configurada ou o limite for atingido.
    """

    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nao configurada no .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()


def gerar_com_groq(prompt: str) -> str:
    """
    Chama a API do Groq com Llama 3.1 70B (fallback gratuito).
    Ativado automaticamente se o Gemini falhar.
    """

    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "sua_chave_groq_aqui":
        raise ValueError("GROQ_API_KEY nao configurada no .env")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model    = "llama-3.3-70b-versatile",
        messages = [{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def gerar_resposta(prompt: str) -> str:
    """
    Tenta Gemini primeiro. Se falhar (limite, erro de key, etc.),
    usa Groq automaticamente como fallback.
    """

    try:
        resposta = gerar_com_gemini(prompt)
        print("[LLM] Gemini 1.5 Flash")
        return resposta

    except Exception as e_gemini:
        print(f"[AVISO] Gemini falhou ({e_gemini}). Tentando Groq como fallback...")

        try:
            resposta = gerar_com_groq(prompt)
            print("[LLM] Groq / Llama 3.1 70B (fallback)")
            return resposta

        except Exception as e_groq:
            return (
                f"[ERRO] Nenhum LLM disponivel.\n"
                f"  Gemini: {e_gemini}\n"
                f"  Groq:   {e_groq}\n\n"
                f"Verifique as chaves de API no arquivo .env"
            )


# ============================================================
# PIPELINE COMPLETO
# ============================================================

def responder(query: str, colecao, modelo: SentenceTransformer) -> str:
    """
    Pipeline RAG completo: query → retrieve → generate → resposta.

    Parametros:
        query   — pergunta em texto livre
        colecao — coleção ChromaDB
        modelo  — modelo de embeddings
    Retorna:
        string com a resposta gerada pelo LLM
    """

    # 1. Recupera os chunks mais relevantes
    chunks = recuperar_chunks(query, colecao, modelo)

    # 2. Monta o prompt com os chunks como contexto
    prompt = montar_prompt(query, chunks)

    # 3. Gera a resposta via LLM (Gemini → Groq)
    resposta = gerar_resposta(prompt)

    return resposta


# ============================================================
# EXECUÇÃO
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description="Pipeline RAG ANEEL — faça perguntas sobre regulação do setor elétrico."
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Pergunta a responder. Se omitida, entra no modo interativo.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help=f"Numero de chunks a recuperar por query. Padrao: {TOP_K}",
    )
    args = parser.parse_args()

    # ── 1. Garante que o vectorstore existe (baixa do HF se necessário) ───
    garantir_vectorstore()

    # ── 2. Carrega o modelo de embeddings ─────────────────────────────────
    print(f"Carregando modelo de embeddings...")
    modelo = SentenceTransformer(MODELO_EMBEDDING)
    print("[OK] Modelo carregado.\n")

    # ── 3. Conecta ao ChromaDB ─────────────────────────────────────────────
    client  = chromadb.PersistentClient(path=PASTA_VECTORSTORE)
    colecao = client.get_collection(name=NOME_COLECAO)
    print(f"[OK] ChromaDB conectado. {colecao.count()} chunks indexados.\n")

    # ── 4. Modo de execução ────────────────────────────────────────────────
    if args.query:
        # Modo direto: responde uma pergunta e encerra
        print(f"Pergunta: {args.query}\n")
        print("=" * 60)
        resposta = responder(args.query, colecao, modelo)
        print(resposta)

    else:
        # Modo interativo: loop de perguntas até o usuário sair
        print("=" * 60)
        print(" RAG ANEEL — Modo Interativo")
        print(" Digite sua pergunta ou 'sair' para encerrar.")
        print("=" * 60)

        while True:
            try:
                query = input("\nPergunta: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando.")
                break

            if not query:
                continue

            if query.lower() in {"sair", "exit", "quit", "q"}:
                print("Encerrando.")
                break

            print()
            resposta = responder(query, colecao, modelo)
            print("-" * 60)
            print(resposta)
            print("-" * 60)


if __name__ == "__main__":
    main()
