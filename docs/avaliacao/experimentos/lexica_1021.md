# Resultados: lexica_1021

Executado em 2026-11-09T14:42:37.197778+00:00. Conjunto: `conjunto_ouro.json`.
Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5.

## Recuperação do sistema entregue (exclui revogados)

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.739 | 0.826 | 0.848 | 0.870 | 0.790 |
| ato_citado | 10 | 0.800 | 1.000 | 1.000 | 1.000 | 0.900 |
| fato_com_ato | 12 | 0.917 | 0.917 | 0.917 | 0.917 | 0.917 |
| fato_sem_ato | 18 | 0.833 | 0.944 | 1.000 | 1.000 | 0.903 |
| revogado | 6 | 0.000 | 0.000 | 0.000 | 0.167 | 0.019 |

## Recuperação sem o filtro de revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.848 | 0.957 | 0.978 | 0.978 | 0.908 |
| ato_citado | 10 | 0.800 | 1.000 | 1.000 | 1.000 | 0.900 |
| fato_com_ato | 12 | 0.917 | 0.917 | 0.917 | 0.917 | 0.917 |
| fato_sem_ato | 18 | 0.833 | 0.944 | 1.000 | 1.000 | 0.903 |
| revogado | 6 | 0.833 | 1.000 | 1.000 | 1.000 | 0.917 |
