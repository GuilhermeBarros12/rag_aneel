# Resultados: previa_reranker_cohere

Executado em 2026-11-13T01:54:26.967693+00:00. Conjunto: `conjunto_previa_reranker.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`. Reranker: `cohere/rerank-v5.0-pro, 30 candidatos`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 8 | 0.500 | 0.875 | 0.875 | 0.875 | 0.667 |
| conceitual_sigla | 1 | 0.000 | 1.000 | 1.000 | 1.000 | 0.500 |
| fato_com_ato | 1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fato_sem_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| norma_citada | 2 | 0.500 | 1.000 | 1.000 | 1.000 | 0.667 |
| norma_por_tema | 2 | 0.500 | 1.000 | 1.000 | 1.000 | 0.750 |

Expansão de contexto: `documento`. Resposta presente no contexto enviado ao LLM: 8 de 8. Tamanho médio do contexto: 6290 caracteres.

## Geração

LLM: `cohere/command-a-03-2025` (10).

| Métrica | Valor |
|---|---|
| Abstenção correta (deve recusar) | 1.000 |
| Recusa indevida (deve responder) | 0.125 |
| Termos esperados presentes | 0.875 |
| Citou um trecho correto | 0.875 |
| Segundos por resposta (média) | 4.5 |
