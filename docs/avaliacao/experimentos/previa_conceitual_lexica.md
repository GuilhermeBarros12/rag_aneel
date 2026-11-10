# Resultados: previa_conceitual_lexica

Executado em 2026-11-09T23:18:57.400581+00:00. Conjunto: `conjunto_conceitual_rascunho.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Inclui revogados: False.

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 19 | 0.211 | 0.316 | 0.526 | 0.579 | 0.307 |
| parafrase | 13 | 0.308 | 0.385 | 0.538 | 0.538 | 0.368 |
| sigla | 6 | 0.000 | 0.167 | 0.500 | 0.667 | 0.175 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 19 | 0.211 | 0.368 | 0.474 | 0.526 | 0.311 |
| parafrase | 13 | 0.308 | 0.462 | 0.538 | 0.538 | 0.387 |
| sigla | 6 | 0.000 | 0.167 | 0.333 | 0.500 | 0.144 |
