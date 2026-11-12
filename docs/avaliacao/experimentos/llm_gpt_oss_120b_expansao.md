# Resultados: llm_gpt_oss_120b_expansao

Executado em 2026-11-12T13:21:53.021928+00:00. Conjunto: `conjunto_ouro.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 46 | 0.826 | 0.891 | 0.935 | 0.935 | 0.870 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| fato_com_ato | 12 | 0.917 | 0.917 | 0.917 | 0.917 | 0.917 |
| fato_sem_ato | 18 | 0.833 | 0.944 | 1.000 | 1.000 | 0.903 |
| revogado | 6 | 0.500 | 0.667 | 0.667 | 0.667 | 0.583 |

Expansão de contexto: `nenhuma`. Resposta presente no contexto enviado ao LLM: 43 de 46. Tamanho médio do contexto: 6230 caracteres.

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

## Geração

LLM: `groq/openai/gpt-oss-120b`.

| Métrica | Valor |
|---|---|
| Abstenção correta (deve recusar) | 1.000 |
| Recusa indevida (deve responder) | 0.130 |
| Termos esperados presentes | 0.891 |
| Citou um trecho correto | 0.848 |
| Segundos por resposta (média) | 4.4 |
