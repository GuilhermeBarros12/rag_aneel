"""Testes da rejeição de páginas de bloqueio. Rodam sem rede e sem o índice."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validacao import eh_pagina_de_bloqueio

PAGINA_BLOQUEIO = """<html><head><title>Attention Required! | Cloudflare</title></head>
<body><h1>Sorry, you have been blocked</h1>
<p>You are unable to access aneel.gov.br</p>
<p>Cloudflare Ray ID: 0000000000000000</p></body></html>"""

PAGINA_NORMA = """<html><body><p>AGÊNCIA NACIONAL DE ENERGIA ELÉTRICA – ANEEL</p>
<p>RESOLUÇÃO NORMATIVA Nº 1.000, DE 7 DE DEZEMBRO DE 2021</p>
<p>Art. 1º Esta Resolução estabelece as regras de prestação do serviço.</p></body></html>"""


def test_pagina_de_bloqueio_e_detectada():
    assert eh_pagina_de_bloqueio(PAGINA_BLOQUEIO)


def test_norma_real_nao_e_bloqueio():
    assert not eh_pagina_de_bloqueio(PAGINA_NORMA)


def test_ingestao_recusa_pagina_de_bloqueio():
    # a ingestão cria a pasta de saída ao ser importada; aponta para uma pasta temporária
    import config

    with tempfile.TemporaryDirectory() as pasta:
        config.PASTA_MARKDOWNS = os.path.join(pasta, "chunks_md")
        import ingestao

        bloqueio = os.path.join(pasta, "ren_bloqueio.html")
        norma = os.path.join(pasta, "ren_norma.html")
        with open(bloqueio, "w", encoding="utf-8") as f:
            f.write(PAGINA_BLOQUEIO)
        with open(norma, "w", encoding="utf-8") as f:
            f.write(PAGINA_NORMA)

        assert ingestao.extrair_html_para_markdown(bloqueio) is None
        assert "RESOLUÇÃO NORMATIVA" in ingestao.extrair_html_para_markdown(norma)


if __name__ == "__main__":
    test_pagina_de_bloqueio_e_detectada()
    test_norma_real_nao_e_bloqueio()
    test_ingestao_recusa_pagina_de_bloqueio()
    print("3 testes OK")
