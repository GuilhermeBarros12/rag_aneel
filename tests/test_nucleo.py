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

    monkeypatch.setattr(nucleo, f"gerar_com_{nome}", falso)
    return chamadas


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
    provedor(monkeypatch, "gemini", ["resposta do gemini"])
    groq = provedor(monkeypatch, "groq", ["resposta do groq"])
    g = nucleo.gerar_resposta("prompt")
    assert g.texto == "resposta do gemini" and g.llm.startswith("gemini/")
    assert groq == [] and g.erros == []


def test_erro_temporario_ganha_nova_tentativa(monkeypatch, sem_espera):
    gemini = provedor(monkeypatch, "gemini", [ErroDeApi("503 UNAVAILABLE", 503), "agora foi"])
    g = nucleo.gerar_resposta("prompt")
    assert g.texto == "agora foi" and len(gemini) == 2 and len(sem_espera) == 1
    assert "(temporario)" in g.erros[0]


def test_cota_esgotada_vai_direto_para_o_fallback(monkeypatch, sem_espera):
    gemini = provedor(monkeypatch, "gemini", [ErroDeApi("quota exceeded: tokens per day", 429)])
    provedor(monkeypatch, "groq", ["resposta do groq"])
    g = nucleo.gerar_resposta("prompt")
    assert g.llm.startswith("groq/") and len(gemini) == 1 and sem_espera == []


def test_resposta_vazia_conta_como_falha(monkeypatch, sem_espera):
    provedor(monkeypatch, "gemini", ["   "])
    provedor(monkeypatch, "groq", ["resposta do groq"])
    assert nucleo.gerar_resposta("prompt").llm.startswith("groq/")


def test_todos_falham(monkeypatch, sem_espera):
    provedor(monkeypatch, "gemini", [ErroDeApi("model not found", 404)])
    provedor(monkeypatch, "groq", [ErroDeApi("Rate limit: tokens per day", 429)])
    g = nucleo.gerar_resposta("prompt")
    assert g.texto is None and g.llm is None and len(g.erros) == 2


def test_lista_de_provedores_restringe_a_um_llm(monkeypatch, sem_espera):
    gemini = provedor(monkeypatch, "gemini", ["resposta do gemini"])
    provedor(monkeypatch, "groq", ["resposta do groq"])
    assert nucleo.gerar_resposta("prompt", provedores=["groq"]).llm.startswith("groq/")
    assert gemini == []


# ---------- pipeline completo ----------


def test_responder_registra_llm_e_documentos(acervo, monkeypatch, sem_espera):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    chamadas = provedor(monkeypatch, "gemini", ["Altera coordenadas [Trecho 1]."])
    r = nucleo.responder("O que determina o Despacho 3.683 de 2022?", None, None)
    assert r.llm.startswith("gemini/")
    assert r.documentos[0]["titulo"] == "DSP - DESPACHO 3683/2022"
    assert "DSP - DESPACHO 3683/2022" in chamadas[0]  # o título foi para o prompt
    assert set(r.para_dict()) == {"pergunta", "resposta", "llm", "erros", "documentos", "trechos"}


def test_busca_sem_resultado_nao_chama_llm(acervo, monkeypatch):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    chamadas = provedor(monkeypatch, "gemini", ["não deveria ser chamado"])
    for pergunta in ("", "   ", "de da do"):
        r = nucleo.responder(pergunta, None, None)
        assert r.llm == config.SEM_LLM and r.trechos == []
        assert r.resposta == config.RESPOSTA_SEM_TRECHOS
    assert chamadas == []


def test_falha_de_todos_os_llms_avisa_sobre_a_cota(acervo, monkeypatch, sem_espera):
    monkeypatch.setattr(config, "MODO_BUSCA", "lexica")
    provedor(monkeypatch, "gemini", [ErroDeApi("model not found", 404)])
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
