"""Testes do acervo léxico (BM25)."""

import lexico
from conftest import REVOGADA


def test_normalizar_numeros_tira_so_o_ponto_de_milhar():
    assert lexico.normalizar_numeros("Despacho nº 3.683") == "Despacho nº 3683"
    assert lexico.normalizar_numeros("R$ 25.588.427,00") == "R$ 25588427,00"
    assert lexico.normalizar_numeros("art. 2º e 3.5 kW") == "art. 2º e 3.5 kW"


def test_montar_consulta_remove_acentos_stopwords_e_repeticoes():
    consulta = lexico.montar_consulta("O que determina o Despacho nº 3.683 de 2022?")
    assert consulta == '"determina" OR "despacho" OR "3683" OR "2022"'
    assert lexico.montar_consulta("usina Usina USINA") == '"usina"'


def test_nome_seguido_de_numeral_vira_frase():
    consulta = lexico.montar_consulta("Usina Eólica Chuí V e UFV Santa Martina 13")
    assert '"chui v"' in consulta and '"martina 13"' in consulta
    assert '"v"' in consulta  # as palavras soltas continuam na consulta
    assert '"usina eolica"' not in consulta  # só quando a segunda palavra é um numeral


def test_pergunta_sem_termos_uteis_gera_consulta_vazia(acervo):
    assert lexico.montar_consulta("de da do") == ""
    assert lexico.buscar("de da do", 5) == []


def test_busca_acha_o_ato_pelo_numero(acervo):
    ids = lexico.buscar("O que determina o Despacho nº 3.683 de 2022?", 5)
    assert ids[0].startswith("dsp20223683ti_chunk")


def test_busca_pode_excluir_revogados(acervo):
    pergunta = "Resolução Normativa 756 Procedimentos de Rede"
    assert lexico.buscar(pergunta, 5)[0] == "ren2016756_chunk1"
    assert "ren2016756_chunk1" not in lexico.buscar(pergunta, 5, excluir_situacao=REVOGADA)


def test_carregar_devolve_texto_e_metadata_na_ordem_pedida(acervo):
    itens = lexico.carregar(["prt2022092_chunk1", "dsp20223683ti_chunk2"])
    assert [i[0] for i in itens] == ["prt2022092_chunk1", "dsp20223683ti_chunk2"]
    _, texto, metadata = itens[1]
    assert "Janaúba" in texto
    assert metadata["titulo"] == "DSP - DESPACHO 3683/2022"
    assert metadata["arquivo_original"] == "dsp20223683ti.pdf"
    assert "chunk_id" not in metadata


def test_busca_funciona_em_outra_thread(acervo):
    # a demo atende cada pergunta em uma thread diferente da que abriu o acervo
    import threading

    lexico.buscar("Despacho 3.683", 1)
    resultado = []
    t = threading.Thread(target=lambda: resultado.append(lexico.buscar("Despacho 3.683", 1)))
    t.start()
    t.join()
    assert resultado and resultado[0][0].startswith("dsp20223683ti_chunk")


def test_acervo_informa_total_e_formato(acervo):
    assert lexico.existe()
    assert lexico.total() == 4
