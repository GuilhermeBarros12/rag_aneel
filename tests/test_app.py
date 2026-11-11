"""Testes da formatação da demo. Não abrem o servidor nem chamam LLM."""

import app
import config
from nucleo import RespostaRAG, Trecho


def trecho(id_, titulo, situacao, arquivo, texto="texto do trecho"):
    return Trecho(id=id_, texto=texto, distancia=None, metadata={
        "titulo": titulo, "situacao": situacao, "publicacao": "Publicação:30/12/2022", "arquivo_original": arquivo,
    })


def resposta(trechos, llm="groq/x", erros=None):
    return RespostaRAG(pergunta="p", resposta="r", llm=llm, erros=erros or [], trechos=trechos)


def test_documentos_sem_repeticao_e_sem_prefixos():
    r = resposta([
        trecho("a_chunk1", "DSP - DESPACHO 1/2022", "Situação:REVOGADA", "a.pdf"),
        trecho("a_chunk2", "DSP - DESPACHO 1/2022", "Situação:REVOGADA", "a.pdf"),
        trecho("b_chunk1", "PRT - PORTARIA 2/2022", "Situação:NÃO CONSTA REVOGAÇÃO EXPRESSA", "b.pdf"),
    ])
    linhas = app.linhas_de_documentos(r)
    assert linhas == [
        ["DSP - DESPACHO 1/2022", "REVOGADA", "30/12/2022", "a.pdf"],
        ["PRT - PORTARIA 2/2022", "NÃO CONSTA REVOGAÇÃO EXPRESSA", "30/12/2022", "b.pdf"],
    ]


def test_trechos_numerados_como_no_prompt():
    r = resposta([trecho("a_chunk1", "DSP - DESPACHO 1/2022", "", "a.pdf", "conteúdo")])
    assert app.texto_dos_trechos(r).startswith("**[Trecho 1] DSP - DESPACHO 1/2022**")
    assert "conteúdo" in app.texto_dos_trechos(r)


def test_descricao_do_llm():
    assert "fallback" in app.descrever_llm(resposta([], erros=["gemini: 503"]))
    assert "Nenhum LLM foi chamado" in app.descrever_llm(resposta([], llm=config.SEM_LLM))
    assert "Nenhum LLM respondeu" in app.descrever_llm(resposta([], llm=None))


def test_app_monta_sem_abrir_servidor():
    assert app.criar_app(None, None) is not None
