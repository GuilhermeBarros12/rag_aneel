"""
Demo web do RAG ANEEL, feita com Gradio.

Mostra a resposta, o LLM que respondeu, os documentos usados (com a situação de
cada ato) e os trechos enviados ao modelo. Usa o mesmo núcleo do pipeline.

Uso: python scripts/app.py   (abre em http://127.0.0.1:7860)
"""

from typing import List

import gradio as gr

import config
from nucleo import RespostaRAG, carregar_recursos, responder

EXEMPLOS = [
    "O que determina o Despacho nº 3.683 de 2022?",
    "Para qual empresa foi transferida a autorização da Central Geradora Eólica Chuí V?",
    "O que é o registro de intenção à outorga de autorização de PCH?",
    "Quem foi o campeão da Copa do Mundo de 2022?",
]

SOBRE = (
    "Perguntas sobre atos da ANEEL de 2016, 2021 e 2022. "
    f"Busca: `{config.MODO_BUSCA}`. "
    "As respostas citam os trechos usados. Confira sempre o documento original antes de usar a informação."
)


def sem_prefixo(valor: str) -> str:
    """'Situação:REVOGADA' vira 'REVOGADA'; 'Publicação:30/12/2022' vira '30/12/2022'."""
    return (valor or "").split(":", 1)[-1].strip()


def linhas_de_documentos(r: RespostaRAG) -> List[List[str]]:
    """Uma linha por documento usado: título, situação, publicação e arquivo."""
    vistos, linhas = set(), []
    for t in r.trechos:
        if t.arquivo in vistos:
            continue
        vistos.add(t.arquivo)
        linhas.append([
            t.titulo,
            sem_prefixo(t.metadata.get("situacao", "")),
            sem_prefixo(t.metadata.get("publicacao", "")),
            t.arquivo,
        ])
    return linhas


def texto_dos_trechos(r: RespostaRAG) -> str:
    """Os trechos enviados ao LLM, em Markdown, na mesma numeração do prompt."""
    if not r.trechos:
        return "Nenhum trecho foi recuperado para esta pergunta."
    partes = []
    for i, t in enumerate(r.trechos, 1):
        texto = t.texto[:config.MAX_CHARS_TRECHO]
        partes.append(f"**[Trecho {i}] {t.titulo}** · `{t.arquivo}`\n\n{texto}")
    return "\n\n---\n\n".join(partes)


def descrever_llm(r: RespostaRAG) -> str:
    if r.llm == config.SEM_LLM:
        return "Nenhum LLM foi chamado: a busca não devolveu trechos."
    if r.llm is None:
        return "Nenhum LLM respondeu."
    aviso = " (o primeiro LLM falhou e o fallback respondeu)" if r.erros else ""
    return f"Respondido por `{r.llm}`{aviso}."


def criar_app(colecao, modelo) -> gr.Blocks:
    def perguntar(pergunta: str):
        r = responder(pergunta, colecao, modelo)
        return r.resposta, descrever_llm(r), linhas_de_documentos(r), texto_dos_trechos(r)

    with gr.Blocks(title="RAG ANEEL") as app:
        gr.Markdown("# RAG ANEEL\n" + SOBRE)
        pergunta = gr.Textbox(label="Pergunta", placeholder="Ex.: O que determina o Despacho nº 3.683 de 2022?")
        enviar = gr.Button("Perguntar", variant="primary")
        gr.Examples(EXEMPLOS, inputs=pergunta, label="Exemplos")
        resposta = gr.Markdown(label="Resposta")
        llm = gr.Markdown()
        documentos = gr.Dataframe(
            headers=["Documento", "Situação", "Publicação", "Arquivo"],
            label="Documentos usados",
            interactive=False,
            wrap=True,
        )
        with gr.Accordion("Trechos enviados ao modelo", open=False):
            trechos = gr.Markdown()

        saidas = [resposta, llm, documentos, trechos]
        enviar.click(perguntar, inputs=pergunta, outputs=saidas)
        pergunta.submit(perguntar, inputs=pergunta, outputs=saidas)
    return app


def main() -> None:
    colecao, modelo = carregar_recursos()
    criar_app(colecao, modelo).launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
