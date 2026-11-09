# Resultados: hibrida_1021

Executado em 2026-11-09T14:45:37.642253+00:00. Conjunto: `conjunto_ouro.json`.
Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5.

## Recuperação do sistema entregue (exclui revogados)

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.130 | 0.630 | 0.739 | 0.848 | 0.414 |
| ato_citado | 10 | 0.000 | 0.800 | 1.000 | 1.000 | 0.450 |
| fato_com_ato | 12 | 0.083 | 0.500 | 0.583 | 0.917 | 0.340 |
| fato_sem_ato | 18 | 0.278 | 0.833 | 0.944 | 1.000 | 0.581 |
| revogado | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Recuperação sem o filtro de revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.152 | 0.739 | 0.870 | 0.978 | 0.485 |
| ato_citado | 10 | 0.000 | 0.800 | 1.000 | 1.000 | 0.450 |
| fato_com_ato | 12 | 0.083 | 0.500 | 0.583 | 0.917 | 0.340 |
| fato_sem_ato | 18 | 0.278 | 0.833 | 0.944 | 1.000 | 0.581 |
| revogado | 6 | 0.167 | 0.833 | 1.000 | 1.000 | 0.542 |
