# Resultados: v2_frases_rerank_cohere

Executado em 2026-11-13T01:41:01.348201+00:00. Conjunto: `conjunto_ouro_v2.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`. Reranker: `cohere/rerank-v5.0-pro, 30 candidatos`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 115 | 0.783 | 0.826 | 0.870 | 0.870 | 0.812 |
| ato_citado | 10 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| conceitual_parafrase | 12 | 0.250 | 0.250 | 0.500 | 0.500 | 0.304 |
| conceitual_sigla | 6 | 0.500 | 0.667 | 0.667 | 0.667 | 0.583 |
| fato_com_ato | 16 | 0.812 | 0.812 | 0.875 | 0.875 | 0.828 |
| fato_sem_ato | 29 | 0.897 | 0.931 | 0.931 | 0.931 | 0.914 |
| norma_citada | 18 | 0.889 | 0.944 | 0.944 | 0.944 | 0.907 |
| norma_por_tema | 3 | 0.667 | 1.000 | 1.000 | 1.000 | 0.833 |
| regra_atual | 6 | 0.833 | 0.833 | 1.000 | 1.000 | 0.867 |
| revogado | 15 | 0.800 | 0.867 | 0.867 | 0.867 | 0.833 |

Expansão de contexto: `documento`. Resposta presente no contexto enviado ao LLM: 104 de 115. Tamanho médio do contexto: 6396 caracteres.
