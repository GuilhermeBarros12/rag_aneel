# Resultados: limpo_ouro_lexica

Executado em 2026-11-09T23:16:34.382610+00:00. Conjunto: `conjunto_ouro.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Inclui revogados: False.

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.783 | 0.826 | 0.870 | 0.870 | 0.815 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| fato_com_ato | 12 | 0.917 | 0.917 | 0.917 | 0.917 | 0.917 |
| fato_sem_ato | 18 | 0.833 | 0.944 | 1.000 | 1.000 | 0.903 |
| revogado | 6 | 0.167 | 0.167 | 0.167 | 0.167 | 0.167 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.870 | 0.935 | 0.978 | 0.978 | 0.913 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| fato_com_ato | 12 | 0.917 | 0.917 | 0.917 | 0.917 | 0.917 |
| fato_sem_ato | 18 | 0.833 | 0.944 | 1.000 | 1.000 | 0.903 |
| revogado | 6 | 0.833 | 1.000 | 1.000 | 1.000 | 0.917 |
