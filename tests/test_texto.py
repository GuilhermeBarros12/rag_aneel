"""Testes da leitura de metadata e do chunking."""

import chunking
import config
import indexar
import ingestao

CABECALHO = """---
titulo: DSP - DESPACHO 3386/2016
autor: SCG/ANEEL
situacao: Situação:NÃO CONSTA REVOGAÇÃO EXPRESSA
ementa: Registra a adequabilidade da PCH São Carlos.
---

AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA

Texto do despacho."""

TABELA = "| Subgrupo | Tarifa |\n|---|---|\n| B1 | 278,12 |\n| B2 | 244,50 |"


def test_metadata_do_cabecalho_preserva_valor_com_dois_pontos():
    metadata = chunking.extrair_metadata_do_header(CABECALHO)
    assert metadata["titulo"] == "DSP - DESPACHO 3386/2016"
    assert metadata["situacao"] == "Situação:NÃO CONSTA REVOGAÇÃO EXPRESSA"
    assert metadata["autor"] == "SCG/ANEEL"


def test_texto_sem_cabecalho():
    texto = chunking.extrair_texto_sem_header(CABECALHO)
    assert texto.startswith("AGÊNCIA NACIONAL") and "titulo:" not in texto


def test_arquivo_sem_cabecalho_devolve_metadata_vazia():
    assert chunking.extrair_metadata_do_header("só texto, sem cabeçalho") == {}


def test_cabecalho_da_ingestao_e_lido_pelo_chunking():
    doc = {"titulo": "REN - RESOLUÇÃO NORMATIVA 756/2016", "situacao": "Situação:REVOGADA", "ementa": None}
    cabecalho = ingestao.montar_metadata(doc, "ren2016756.html", "Texto Integral:")
    metadata = chunking.extrair_metadata_do_header(cabecalho + "corpo")
    assert metadata["titulo"] == "REN - RESOLUÇÃO NORMATIVA 756/2016"
    assert metadata["arquivo_original"] == "ren2016756.html"
    assert metadata["ementa"] == "None"  # ementa ausente vira o texto "None" (limitação conhecida)


def test_cabecalho_do_chunk_e_lido_pela_indexacao():
    metadata = chunking.extrair_metadata_do_header(CABECALHO)
    arquivo = chunking.montar_cabecalho_chunk(metadata, 2, 7) + "Texto do chunk."
    lida, texto = indexar.extrair_metadata_e_texto(arquivo)
    assert texto == "Texto do chunk."
    assert lida["chunk_id"] == "2" and lida["chunk_total"] == "7"
    assert lida["titulo"] == "DSP - DESPACHO 3386/2016"


def test_tabelas_viram_marcadores_e_voltam_iguais():
    texto = f"Antes.\n{TABELA}\nDepois."
    protegido, tabelas = chunking.proteger_tabelas(texto)
    assert "|" not in protegido and len(tabelas) == 1
    assert chunking.restaurar_tabelas([protegido], tabelas) == [texto]


def test_chunks_respeitam_o_tamanho_e_nao_cortam_tabelas():
    paragrafo = "A concessionária deverá observar os prazos regulatórios aplicáveis. " * 30
    chunks = chunking.chunkar_documento(f"{paragrafo}\n\n{TABELA}\n\n{paragrafo}")
    assert len(chunks) > 3
    assert any(TABELA in c for c in chunks)  # a tabela ficou inteira em um chunk
    assert all(len(c) <= config.CHUNK_SIZE for c in chunks if "|" not in c)
    assert all(len(c.strip()) >= config.MIN_CHARS for c in chunks)


def test_ingestao_processa_o_pdf_antes_do_html_de_mesmo_nome():
    versoes = [
        {"tipo": "Texto Integral:", "arquivo": "ren2016756.html"},
        {"tipo": "Texto Integral:", "arquivo": "ren2016756.pdf"},
        {"tipo": "Voto:", "arquivo": "aren2016756_1.pdf"},
    ]
    ordem = [v["arquivo"] for v in ingestao.ordenar_versoes(versoes)]
    assert ordem.index("ren2016756.pdf") < ordem.index("ren2016756.html")


def test_metadata_para_o_chroma_nao_tem_none():
    assert indexar.limpar_metadata_para_chroma({"a": None, "b": 3}) == {"a": "", "b": "3"}
