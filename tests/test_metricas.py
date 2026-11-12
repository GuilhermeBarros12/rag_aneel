"""Testes das funções de métrica. Rodam sem rede, sem chaves e sem o índice."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import avaliar_ouro as a


def trecho(id_, texto=""):
    return SimpleNamespace(id=id_, texto=texto)


def test_documento_do_trecho():
    assert a.documento_do_trecho("dsp20163386_chunk4") == "dsp20163386"
    assert a.documento_do_trecho("adsp2016711_1_chunk106") == "adsp2016711_1"


def test_hit_e_mrr():
    r = a.resumir_posicoes([1, 2, None, 10])
    assert r["hit@1"] == 0.25 and r["hit@3"] == 0.5 and r["hit@10"] == 0.75
    assert abs(r["mrr"] - (1 + 0.5 + 0.1) / 4) < 1e-9


def test_acerto_por_documento():
    q = {"documentos_esperados": ["y"]}
    assert a.posicao_primeiro_correto([trecho("x_chunk1"), trecho("y_chunk2")], q) == 2
    assert a.posicao_primeiro_correto([trecho("x_chunk1")], q) is None


def test_acerto_por_evidencia_ignora_acentos_e_caixa():
    q = {"documentos_esperados": [], "evidencia": ["subsidiar as decisões"]}
    certo = trecho("n_chunk9", "A Nota Técnica destina-se a SUBSIDIAR  as decisoes da Agência.")
    assert a.posicao_primeiro_correto([trecho("x_chunk1", "outro texto"), certo], q) == 2


def test_recusa_e_termos():
    assert a.recusou("Não encontrei  informação suficiente nos documentos.")
    assert not a.recusou("O prazo é de 10 dias.")
    assert a.contem_termos("A usina fica em Assu.", ["Assú"])
    assert a.contem_termos("Foi a REN 1045/2022.", ["1.045"])
    assert a.contem_termos("Multa de R$ 25.588.427,00.", ["25.588.427"])
    assert not a.contem_termos("Submódulo 9.12", ["9.2"])
    assert not a.contem_termos("A usina fica em Natal.", ["Assú"])


def test_trechos_citados():
    assert a.trechos_citados("Conforme o DSP 1/2016 [Trecho 2].") == [2]
    assert a.trechos_citados("Ver [Trechos 1 e 3] e também [Trecho 5].") == [1, 3, 5]
    assert a.trechos_citados("Não encontrei informação suficiente.") == []


def test_resumo_da_geracao_sem_perguntas_de_recusa():
    linhas = [{"deve_recusar": False, "llm": "x", "recusou": False, "termos_ok": True, "citou_correto": True}]
    r = a.resumir_geracao(linhas)
    assert r["abstencao_correta"] is None and r["citou_trecho_correto"] == 1.0


if __name__ == "__main__":
    testes = [f for nome, f in sorted(globals().items()) if nome.startswith("test_")]
    for teste in testes:
        teste()
    print(f"{len(testes)} testes OK")
