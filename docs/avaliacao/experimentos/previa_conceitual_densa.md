# Resultados: previa_conceitual_densa

Executado em 2026-11-09T23:19:22.008272+00:00. Conjunto: `conjunto_conceitual_rascunho.json`.
Busca: `densa`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Inclui revogados: False.

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 19 | 0.211 | 0.211 | 0.211 | 0.263 | 0.217 |
| parafrase | 13 | 0.231 | 0.231 | 0.231 | 0.308 | 0.240 |
| sigla | 6 | 0.167 | 0.167 | 0.167 | 0.167 | 0.167 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 19 | 0.158 | 0.158 | 0.158 | 0.211 | 0.164 |
| parafrase | 13 | 0.231 | 0.231 | 0.231 | 0.308 | 0.239 |
| sigla | 6 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
