"""
Validação do conteúdo baixado.

Em abril de 2026, 153 arquivos de Resoluções Normativas foram salvos como página
de bloqueio do Cloudflare e indexados como se fossem a norma. Estas funções
permitem recusar esse tipo de página no download e na ingestão.
"""

# Trechos que só aparecem em páginas de bloqueio, nunca em um ato da ANEEL
MARCAS_BLOQUEIO = (
    "Attention Required! | Cloudflare",
    "Sorry, you have been blocked",
    "Cloudflare Ray ID",
)


def eh_pagina_de_bloqueio(texto: str) -> bool:
    """True se o texto é uma página de bloqueio em vez do documento pedido."""
    return any(marca in texto for marca in MARCAS_BLOQUEIO)
