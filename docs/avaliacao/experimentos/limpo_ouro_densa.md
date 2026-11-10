# Resultados: limpo_ouro_densa

Executado em 2026-11-09T23:17:19.589506+00:00. Conjunto: `conjunto_ouro.json`.
Busca: `densa`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Inclui revogados: False.

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.087 | 0.087 | 0.130 | 0.152 | 0.100 |
| ato_citado | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fato_com_ato | 12 | 0.000 | 0.000 | 0.083 | 0.083 | 0.021 |
| fato_sem_ato | 18 | 0.222 | 0.222 | 0.278 | 0.333 | 0.242 |
| revogado | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.109 | 0.109 | 0.174 | 0.196 | 0.126 |
| ato_citado | 10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fato_com_ato | 12 | 0.000 | 0.000 | 0.083 | 0.083 | 0.021 |
| fato_sem_ato | 18 | 0.222 | 0.222 | 0.278 | 0.333 | 0.242 |
| revogado | 6 | 0.167 | 0.167 | 0.333 | 0.333 | 0.200 |
