"""Interface de linha de comando do RAG ANEEL. A lógica fica em nucleo.py."""

import argparse

import config
from nucleo import RespostaRAG, carregar_recursos, responder


def exibir(r: RespostaRAG) -> None:
    """Mostra a resposta, qual LLM respondeu e os documentos usados."""

    print("-" * 60)
    print(r.resposta)
    print("-" * 60)

    print(f"LLM: {r.llm or 'nenhum'}")
    if r.llm and r.erros:
        print("Fallback acionado:")
        for erro in r.erros:
            print(f"  {erro[:200]}")

    print("\nDocumentos usados:")
    for d in r.documentos:
        print(f"  - {d['titulo']} ({d['arquivo']})")

    print("\nReferências:")
    for i, t in enumerate(r.trechos, 1):
        distancia = "busca lexica" if t.distancia is None else f"distancia {t.distancia:.3f}"
        print(f"\n[Trecho {i}] {t.titulo} | {t.arquivo} | {distancia}")
        print(t.texto)


def main() -> None:

    parser = argparse.ArgumentParser(
        description="Pipeline RAG ANEEL: perguntas sobre regulação do setor elétrico."
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
        default=config.TOP_K,
        help=f"Numero de chunks a recuperar por pergunta. Padrao: {config.TOP_K}",
    )
    args = parser.parse_args()

    colecao, modelo = carregar_recursos()

    if args.query:
        print(f"Pergunta: {args.query}\n")
        exibir(responder(args.query, colecao, modelo, top_k=args.top_k))
        return

    print("=" * 60)
    print(" RAG ANEEL - Modo Interativo")
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
        exibir(responder(query, colecao, modelo, top_k=args.top_k))


if __name__ == "__main__":
    main()
