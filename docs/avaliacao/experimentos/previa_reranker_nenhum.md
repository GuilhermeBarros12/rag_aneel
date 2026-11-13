# Resultados: previa_reranker_nenhum

Executado em 2026-11-13T01:52:50.036688+00:00. Conjunto: `conjunto_previa_reranker.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`. Reranker: `nenhum`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 8 | 0.375 | 0.375 | 0.375 | 0.625 | 0.403 |
| conceitual_sigla | 1 | 0.000 | 0.000 | 0.000 | 1.000 | 0.111 |
| fato_com_ato | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fato_sem_ato | 2 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |
| norma_citada | 2 | 0.000 | 0.000 | 0.000 | 0.500 | 0.056 |
| norma_por_tema | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Expansão de contexto: `documento`. Resposta presente no contexto enviado ao LLM: 2 de 8. Tamanho médio do contexto: 5316 caracteres.

## Geração

LLM: `cohere/command-a-03-2025` (10).

| Métrica | Valor |
|---|---|
| Abstenção correta (deve recusar) | 1.000 |
| Recusa indevida (deve responder) | 0.375 |
| Termos esperados presentes | 0.625 |
| Citou um trecho correto | 0.375 |
| Segundos por resposta (média) | 4.1 |
