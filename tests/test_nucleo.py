"""Testes do núcleo: recuperação, prompt e geração com fallback. Nenhum LLM real é chamado."""

import pytest

import config
import nucleo
from conftest import REVOGADA, ModeloFalso


class ErroDeApi(Exception):
    """Imita o erro de um provedor, que traz o código HTTP."""

    def __init__(self, mensagem, status_code=None):
        super().__init__(mensagem)
        self.status_code = status_code


@pytest.fixture
def sem_espera(monkeypatch):
    """Tira a espera entre tentativas e conta quantas vezes ela foi pedida."""
    esperas = []
    monkeypatch.setattr(nucleo.time, "sleep", lambda s: esperas.append(s))
    return esperas


def provedor(monkeypatch, nome, respostas):
    """Troca um provedor por uma fila de respostas; exceções na fila são lançadas."""
    chamadas = []

    def falso(prompt):
        chamadas.append(prompt)
        item = respostas[min(len(chamadas), len(respostas)) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    if nome == "groq":
        monkeypatch.setattr(nucleo, "gerar_com_groq", falso)
    else:
        anterior = nucleo.gerar_com_compativel

        def compativel(p, prompt):
            return falso(prompt) if p == nome else anterior(p, prompt)

        monkeypatch.setattr(nucleo, "gerar_com_compativel", compativel)
    return chamadas


@pytest.fixture(autouse=True)
def ordem_dos_llms(monkeypatch):
    """Os testes de geração usam só dois provedores falsos: Cohere e Groq."""
    monkeypatch.setattr(config, "LLMS", ["cohere", "groq"])


# ---------- fusão e prompt ----------


def test_fusao_rrf_premia_quem_aparece_nas_duas_listas():
    assert nucleo.fundir_rrf([["a", "b", "c"], ["b", "d"]], [1.0, 1.0])[0] == "b"


def test_fusao_rrf_respeita_o_peso():
    assert nucleo.fundir_rrf([["a"], ["b"]], [1.0, 4.0])[0] == "b"


def test_prompt_identifica_o_documento_de_cada_trecho():
    trecho = nucleo.Trecho(
        id="dsp1_chunk1", texto="x" * 10000, distancia=None,
        metadata={"titulo": "DSP - DESPACHO 1/2016", "situacao": REVOGADA, "arquivo_original": "dsp1.pdf"},
    )
    prompt = nucleo.montar_prompt("Qual o prazo?", [trecho])
    assert "[Trecho 1] DSP - DESPACHO 1/2016" in prompt
    assert REVOGADA in prompt and "Arquivo: dsp1.pdf" in prompt
    assert "Pergunta: Qual o prazo?" in prompt
    assert "x" * (config.MAX_CHARS_TRECHO + 1) not in prompt  # trecho longo é cortado


# ---------- recuperação em um índice minúsculo ----------


def test_busca_lexica_nao_precisa_de_colecao_nem_de_modelo(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    trechos = nucleo.recuperar_trechos("Despacho 3.683 de 2022", None, None, top_k=2)
    assert trechos[0].titulo == "DSP - DESPACHO 3683/2022"
    assert trechos[0].arquivo == "dsp20223683ti.pdf"
    assert trechos[0].distancia is None


def test_busca_densa_usa_o_vetor_da_pergunta(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "densa")
    trechos = nucleo.recuperar_trechos("Quem recebeu licença?", acervo, ModeloFalso(), top_k=1)
    assert trechos[0].id == "prt2022092_chunk1"
    assert trechos[0].distancia is not None


def test_busca_hibrida_junta_as_duas(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "hibrida")
    trechos = nucleo.recuperar_trechos("licença para capacitação", acervo, ModeloFalso(), top_k=2)
    assert trechos[0].id == "prt2022092_chunk1"


def test_filtro_exclui_revogados_nos_tres_modos(acervo, monkeypatch):
    for modo in ("lexica", "densa", "hibrida"):
        monkeypatch.setattr(config, "MODO_BUSCA", modo)
        trechos = nucleo.recuperar_trechos(
            "Procedimentos de Rede", acervo, ModeloFalso(), top_k=4, filtro=config.FILTRO_SEM_REVOGADOS)
        assert all(t.metadata["situacao"] != REVOGADA for t in trechos), modo


# ---------- geração ----------


def test_tipo_de_erro():
    assert nucleo.tipo_de_erro(ErroDeApi("503 UNAVAILABLE high demand", 503)) == "temporario"
    assert nucleo.tipo_de_erro(ErroDeApi("Rate limit reached on tokens per day (TPD)", 429)) == "cota"
    assert nucleo.tipo_de_erro(ErroDeApi("Rate limit reached on tokens per minute", 429)) == "temporario"
    assert nucleo.tipo_de_erro(ErroDeApi("504 DEADLINE_EXCEEDED", 504)) == "definitivo"
    assert nucleo.tipo_de_erro(ErroDeApi("model not found", 404)) == "definitivo"


def test_primeiro_provedor_responde(monkeypatch, sem_espera):
    provedor(monkeypatch, "cohere", ["resposta da cohere"])
    groq = provedor(monkeypatch, "groq", ["resposta do groq"])
    g = nucleo.gerar_resposta("prompt")
    assert g.texto == "resposta da cohere" and g.llm.startswith("cohere/")
    assert groq == [] and g.erros == []


def test_erro_temporario_ganha_nova_tentativa(monkeypatch, sem_espera):
    cohere = provedor(monkeypatch, "cohere", [ErroDeApi("503 UNAVAILABLE", 503), "agora foi"])
    g = nucleo.gerar_resposta("prompt")
    assert g.texto == "agora foi" and len(cohere) == 2 and len(sem_espera) == 1
    assert "(temporario)" in g.erros[0]


def test_cota_esgotada_vai_direto_para_o_fallback(monkeypatch, sem_espera):
    cohere = provedor(monkeypatch, "cohere", [ErroDeApi("quota exceeded: tokens per day", 429)])
    provedor(monkeypatch, "groq", ["resposta do groq"])
    g = nucleo.gerar_resposta("prompt")
    assert g.llm.startswith("groq/") and len(cohere) == 1 and sem_espera == []


def test_resposta_vazia_conta_como_falha(monkeypatch, sem_espera):
    provedor(monkeypatch, "cohere", ["   "])
    provedor(monkeypatch, "groq", ["resposta do groq"])
    assert nucleo.gerar_resposta("prompt").llm.startswith("groq/")


def test_todos_falham(monkeypatch, sem_espera):
    provedor(monkeypatch, "cohere", [ErroDeApi("model not found", 404)])
    provedor(monkeypatch, "groq", [ErroDeApi("Rate limit: tokens per day", 429)])
    g = nucleo.gerar_resposta("prompt")
    assert g.texto is None and g.llm is None and len(g.erros) == 2


def test_lista_de_provedores_restringe_a_um_llm(monkeypatch, sem_espera):
    cohere = provedor(monkeypatch, "cohere", ["resposta da cohere"])
    provedor(monkeypatch, "groq", ["resposta do groq"])
    assert nucleo.gerar_resposta("prompt", provedores=["groq"]).llm.startswith("groq/")
    assert cohere == []


# ---------- pipeline completo ----------


def test_responder_registra_llm_e_documentos(acervo, monkeypatch, sem_espera):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    chamadas = provedor(monkeypatch, "cohere", ["Altera coordenadas [Trecho 1]."])
    r = nucleo.responder("O que determina o Despacho 3.683 de 2022?", None, None)
    assert r.llm.startswith("cohere/")
    assert r.documentos[0]["titulo"] == "DSP - DESPACHO 3683/2022"
    assert "DSP - DESPACHO 3683/2022" in chamadas[0]  # o título foi para o prompt
    assert set(r.para_dict()) == {"pergunta", "resposta", "llm", "erros", "documentos", "trechos"}


def test_busca_sem_resultado_nao_chama_llm(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    chamadas = provedor(monkeypatch, "cohere", ["não deveria ser chamado"])
    for pergunta in ("", "   ", "de da do"):
        r = nucleo.responder(pergunta, None, None)
        assert r.llm == config.SEM_LLM and r.trechos == []
        assert r.resposta == config.RESPOSTA_SEM_TRECHOS
    assert chamadas == []


def test_falha_de_todos_os_llms_avisa_sobre_a_cota(acervo, monkeypatch, sem_espera):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    provedor(monkeypatch, "cohere", [ErroDeApi("model not found", 404)])
    provedor(monkeypatch, "groq", [ErroDeApi("Rate limit: tokens per day", 429)])
    r = nucleo.responder("Despacho 3.683", None, None)
    assert r.llm is None and "cota diaria" in r.resposta


# ---------- política de atos revogados ----------


def test_motivo_para_incluir_revogados():
    m = nucleo.motivo_para_incluir_revogados
    assert m("O que determina o Despacho nº 3.683 de 2022?") == "pergunta cita um ato"
    assert m("Qual a diferença entre o 3.386/2016 e o 3.408/2016?") == "pergunta cita um ato"
    assert m("Para quais anos a Resolução Autorizativa nº 10.230 fixou limites?") == "pergunta cita um ato"
    assert m("A Portaria 3.936 ainda está em vigor?") == "pergunta sobre vigência"
    assert m("Quais resoluções de 2016 foram revogadas?") == "pergunta sobre vigência"
    assert m("Qual empresa foi autorizada a explorar a UFV Olho do Sol 5?") is None
    assert m("O que significa a sigla TUSD?") is None


def test_politica_intermediaria(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    monkeypatch.setattr(config, "POLITICA_REVOGADOS", "intermediaria")

    def ids(pergunta):
        return [t.id for t in nucleo.recuperar_com_politica(pergunta, None, None, top_k=4)]

    # sem citar o ato, e havendo resultado vigente ("usinas"), a norma revogada fica de fora
    assert "ren2016756_chunk1" not in ids("Procedimentos de Rede das usinas")
    # citando o ato, ela entra
    assert ids("Resolução Normativa nº 756 Procedimentos de Rede")[0] == "ren2016756_chunk1"
    # quando nada vigente é encontrado, ela também entra
    assert ids("Aprova a revisão")[0] == "ren2016756_chunk1"


def test_politicas_excluir_e_incluir(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    pergunta = "Resolução Normativa nº 756 Procedimentos de Rede"
    monkeypatch.setattr(config, "POLITICA_REVOGADOS", "excluir")
    assert all(t.metadata["situacao"] != REVOGADA for t in nucleo.recuperar_com_politica(pergunta, None, None, 4))
    monkeypatch.setattr(config, "POLITICA_REVOGADOS", "incluir")
    assert nucleo.recuperar_com_politica("Procedimentos de Rede", None, None, 4)[0].id == "ren2016756_chunk1"


# ---------- provedores compatíveis com a API da OpenAI ----------


class RespostaHttpFalsa:
    def __init__(self, status_code, corpo):
        self.status_code = status_code
        self._corpo = corpo
        self.text = str(corpo)

    def json(self):
        return self._corpo


def test_provedor_compativel_monta_a_chamada(monkeypatch):
    import httpx

    chamadas = []

    def post_falso(url, headers, json, timeout):
        chamadas.append((url, headers, json))
        return RespostaHttpFalsa(200, {"choices": [{"message": {"content": "resposta"}}]})

    monkeypatch.setattr(httpx, "post", post_falso)
    monkeypatch.setenv("MISTRAL_API_KEY", "chave-de-teste")
    assert nucleo.gerar_com_compativel("mistral", "prompt") == "resposta"
    url, cabecalhos, corpo = chamadas[0]
    assert url == "https://api.mistral.ai/v1/chat/completions"
    assert cabecalhos["Authorization"] == "Bearer chave-de-teste"
    assert corpo["messages"][0]["content"] == "prompt" and corpo["temperature"] == config.TEMPERATURA


def test_provedor_compativel_sem_chave_e_erro_http(monkeypatch):
    import httpx

    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        nucleo.gerar_com_compativel("cohere", "prompt")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: RespostaHttpFalsa(429, "rate limit"))
    monkeypatch.setenv("COHERE_API_KEY", "x")
    with pytest.raises(nucleo.ErroDeApi) as erro:
        nucleo.gerar_com_compativel("cohere", "prompt")
    assert nucleo.tipo_de_erro(erro.value) == "temporario"


def test_provedor_local_nao_exige_chave(monkeypatch, sem_espera):
    import httpx

    monkeypatch.setattr(httpx, "post", lambda *a, **k: RespostaHttpFalsa(200, {"choices": [{"message": {"content": "ok"}}]}))
    g = nucleo.gerar_resposta("prompt", provedores=["local"])
    assert g.texto == "ok" and g.llm.startswith("local/")


# ---------- expansão de contexto ----------


def test_sem_expansao_o_contexto_nao_muda(acervo, monkeypatch):
    monkeypatch.setattr(config, "EXPANSAO_CONTEXTO", "nenhuma")
    trechos = [nucleo.Trecho(id="dsp20223683ti_chunk1", texto="x", distancia=None, metadata={})]
    assert nucleo.expandir_contexto(trechos) == trechos


def test_documento_curto_entra_inteiro_e_na_ordem(acervo, monkeypatch):
    monkeypatch.setattr(config, "EXPANSAO_CONTEXTO", "documento")
    trechos = [nucleo.Trecho(id="dsp20223683ti_chunk2", texto="x", distancia=None, metadata={})]
    ids = [t.id for t in nucleo.expandir_contexto(trechos)]
    assert ids == ["dsp20223683ti_chunk1", "dsp20223683ti_chunk2"]


def test_documento_longo_recebe_so_os_vizinhos(acervo, monkeypatch):
    monkeypatch.setattr(config, "EXPANSAO_CONTEXTO", "documento")
    monkeypatch.setattr(config, "LIMITE_DOC_CURTO_CHARS", 10)  # força o documento a ser "longo"
    monkeypatch.setattr(config, "VIZINHOS", 0)
    trechos = [nucleo.Trecho(id="dsp20223683ti_chunk2", texto="x", distancia=None, metadata={})]
    assert [t.id for t in nucleo.expandir_contexto(trechos)] == ["dsp20223683ti_chunk2"]


def test_contexto_respeita_o_teto(acervo, monkeypatch):
    monkeypatch.setattr(config, "EXPANSAO_CONTEXTO", "documento")
    monkeypatch.setattr(config, "MAX_CHARS_CONTEXTO", 1)
    trechos = [nucleo.Trecho(id="dsp20223683ti_chunk2", texto="x", distancia=None, metadata={}),
               nucleo.Trecho(id="prt2022092_chunk1", texto="y", distancia=None, metadata={})]
    assert len(nucleo.expandir_contexto(trechos)) == 1  # mantém só o primeiro


# ---------- reranker ----------


@pytest.fixture
def com_reranker(monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    monkeypatch.setattr(config, "RERANKER", "cohere")
    monkeypatch.setattr(nucleo, "CACHE_RERANK", {})
    monkeypatch.setattr(nucleo, "FALHAS_RERANK", [])


def test_reranker_reordena_e_guarda_em_cache(acervo, com_reranker, monkeypatch):
    chamadas = []

    def rerank_falso(query, trechos):
        chamadas.append([t.id for t in trechos])
        return [t.id for t in reversed(trechos)]

    monkeypatch.setattr(nucleo, "rerank_cohere", rerank_falso)
    primeira = nucleo.recuperar_trechos("usinas", None, None, top_k=1)
    segunda = nucleo.recuperar_trechos("usinas", None, None, top_k=1)
    assert len(chamadas) == 1 and len(chamadas[0]) == 2  # a segunda busca veio do cache
    assert primeira[0].id == chamadas[0][-1] == segunda[0].id


def test_falha_do_reranker_mantem_a_ordem_da_busca(acervo, com_reranker, monkeypatch):
    def rerank_quebrado(query, trechos):
        raise ErroDeApi("500 erro", 500)

    monkeypatch.setattr(nucleo, "rerank_cohere", rerank_quebrado)
    monkeypatch.setattr(config, "RERANKER", "nenhum")
    esperado = [t.id for t in nucleo.recuperar_trechos("usinas", None, None, top_k=2)]
    monkeypatch.setattr(config, "RERANKER", "cohere")
    obtido = [t.id for t in nucleo.recuperar_trechos("usinas", None, None, top_k=2)]
    assert obtido == esperado
    assert len(nucleo.FALHAS_RERANK) == 1


def test_rerank_cohere_monta_a_chamada_e_espera_no_limite(monkeypatch):
    import httpx

    respostas = [RespostaHttpFalsa(429, {}), RespostaHttpFalsa(200, {"results": [{"index": 1}, {"index": 0}]})]
    chamadas = []

    def post_falso(url, headers, json, timeout):
        chamadas.append((url, json))
        return respostas.pop(0)

    monkeypatch.setattr(httpx, "post", post_falso)
    monkeypatch.setattr(nucleo.time, "sleep", lambda s: None)
    monkeypatch.setenv("COHERE_API_KEY", "chave-de-teste")
    trechos = [nucleo.Trecho(id="a", texto="texto a", distancia=None, metadata={"titulo": "DSP 1"}),
               nucleo.Trecho(id="b", texto="texto b", distancia=None, metadata={"titulo": "DSP 2"})]
    assert nucleo.rerank_cohere("pergunta", trechos) == ["b", "a"]
    url, corpo = chamadas[1]
    assert url == "https://api.cohere.com/v2/rerank"
    assert corpo["model"] == config.COHERE_RERANK_MODELO and corpo["query"] == "pergunta"
    assert corpo["documents"][0].endswith("texto a")
