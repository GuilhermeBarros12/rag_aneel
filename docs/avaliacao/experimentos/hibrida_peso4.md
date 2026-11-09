# Resultados: hibrida_peso4

Executado em 2026-11-09T14:52:10.906696+00:00. Conjunto: `conjunto_ouro.json`.
Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5.

## Recuperação do sistema entregue (exclui revogados)

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.565 | 0.674 | 0.804 | 0.870 | 0.659 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| fato_com_ato | 12 | 0.417 | 0.500 | 0.833 | 0.917 | 0.544 |
| fato_sem_ato | 18 | 0.667 | 0.889 | 0.944 | 1.000 | 0.801 |
| revogado | 6 | 0.000 | 0.000 | 0.000 | 0.167 | 0.019 |

## Recuperação sem o filtro de revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.674 | 0.804 | 0.935 | 0.978 | 0.776 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| fato_com_ato | 12 | 0.417 | 0.500 | 0.833 | 0.917 | 0.544 |
| fato_sem_ato | 18 | 0.667 | 0.889 | 0.944 | 1.000 | 0.801 |
| revogado | 6 | 0.833 | 1.000 | 1.000 | 1.000 | 0.917 |
