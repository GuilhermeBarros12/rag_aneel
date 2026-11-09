# Resultados: hibrida_111

Executado em 2026-11-09T14:43:25.575849+00:00. Conjunto: `conjunto_ouro.json`.
Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5.

## Recuperação do sistema entregue (exclui revogados)

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.109 | 0.630 | 0.717 | 0.848 | 0.395 |
| ato_citado | 10 | 0.000 | 0.900 | 0.900 | 1.000 | 0.463 |
| fato_com_ato | 12 | 0.083 | 0.417 | 0.583 | 0.833 | 0.305 |
| fato_sem_ato | 18 | 0.222 | 0.833 | 0.944 | 1.000 | 0.544 |
| revogado | 6 | 0.000 | 0.000 | 0.000 | 0.167 | 0.017 |

## Recuperação sem o filtro de revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.130 | 0.739 | 0.848 | 0.957 | 0.463 |
| ato_citado | 10 | 0.000 | 0.900 | 0.900 | 1.000 | 0.463 |
| fato_com_ato | 12 | 0.083 | 0.417 | 0.583 | 0.833 | 0.305 |
| fato_sem_ato | 18 | 0.222 | 0.833 | 0.944 | 1.000 | 0.544 |
| revogado | 6 | 0.167 | 0.833 | 1.000 | 1.000 | 0.533 |
