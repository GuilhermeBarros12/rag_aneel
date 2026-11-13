# Resultados: v2_frases_numeral

Executado em 2026-11-13T01:35:56.360602+00:00. Conjunto: `conjunto_ouro_v2.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`. Reranker: `nenhum`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 115 | 0.713 | 0.774 | 0.835 | 0.852 | 0.755 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 12 | 0.250 | 0.333 | 0.500 | 0.500 | 0.315 |
| conceitual_sigla | 6 | 0.000 | 0.167 | 0.500 | 0.667 | 0.177 |
| fato_com_ato | 16 | 0.875 | 0.875 | 0.875 | 0.875 | 0.875 |
| fato_sem_ato | 29 | 0.862 | 0.897 | 0.897 | 0.897 | 0.874 |
| norma_citada | 18 | 0.667 | 0.778 | 0.833 | 0.889 | 0.730 |
| norma_por_tema | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| regra_atual | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 15 | 0.667 | 0.800 | 0.867 | 0.867 | 0.750 |

Expansão de contexto: `documento`. Resposta presente no contexto enviado ao LLM: 98 de 115. Tamanho médio do contexto: 6147 caracteres.
