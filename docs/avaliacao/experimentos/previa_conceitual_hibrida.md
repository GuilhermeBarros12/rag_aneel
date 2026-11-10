# Resultados: previa_conceitual_hibrida

Executado em 2026-11-09T23:20:09.318663+00:00. Conjunto: `conjunto_conceitual_rascunho.json`.
Busca: `hibrida`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Inclui revogados: False.

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 19 | 0.105 | 0.368 | 0.368 | 0.579 | 0.264 |
| parafrase | 13 | 0.154 | 0.462 | 0.462 | 0.615 | 0.330 |
| sigla | 6 | 0.000 | 0.167 | 0.167 | 0.500 | 0.121 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 19 | 0.105 | 0.368 | 0.421 | 0.526 | 0.264 |
| parafrase | 13 | 0.154 | 0.538 | 0.538 | 0.615 | 0.359 |
| sigla | 6 | 0.000 | 0.000 | 0.167 | 0.333 | 0.058 |
