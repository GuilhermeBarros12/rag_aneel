# Resultados: mini_local_gpt_oss_20b

Executado em 2026-11-12T03:30:16.123875+00:00. Conjunto: `conjunto_mini_llm.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 8 | 0.750 | 0.750 | 0.875 | 0.875 | 0.781 |
| ato_citado | 2 | 0.500 | 0.500 | 1.000 | 1.000 | 0.625 |
| fato_com_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| fato_sem_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 2 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 |

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 8 | 0.625 | 0.625 | 0.750 | 0.750 | 0.656 |
| ato_citado | 2 | 0.500 | 0.500 | 1.000 | 1.000 | 0.625 |
| fato_com_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| fato_sem_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 8 | 0.875 | 0.875 | 1.000 | 1.000 | 0.906 |
| ato_citado | 2 | 0.500 | 0.500 | 1.000 | 1.000 | 0.625 |
| fato_com_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| fato_sem_ato | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Geração

LLM: `local/openai/gpt-oss-20b`.

| Métrica | Valor |
|---|---|
| Abstenção correta (deve recusar) | 1.000 |
| Recusa indevida (deve responder) | 0.500 |
| Termos esperados presentes | 0.500 |
| Citou um trecho correto | 0.500 |
| Segundos por resposta (média) | 153.6 |
