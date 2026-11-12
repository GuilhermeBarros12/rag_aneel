# Resultados: v2_recuperacao

Executado em 2026-11-12T14:17:10.125356+00:00. Conjunto: `conjunto_ouro_v2.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 115 | 0.678 | 0.757 | 0.835 | 0.852 | 0.734 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 12 | 0.250 | 0.333 | 0.500 | 0.500 | 0.315 |
| conceitual_sigla | 6 | 0.000 | 0.167 | 0.500 | 0.667 | 0.177 |
| fato_com_ato | 16 | 0.875 | 0.875 | 0.875 | 0.875 | 0.875 |
| fato_sem_ato | 29 | 0.759 | 0.862 | 0.897 | 0.897 | 0.819 |
| norma_citada | 18 | 0.611 | 0.722 | 0.833 | 0.889 | 0.686 |
| norma_por_tema | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| regra_atual | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 15 | 0.667 | 0.800 | 0.867 | 0.867 | 0.750 |

Expansão de contexto: `documento`. Resposta presente no contexto enviado ao LLM: 97 de 115. Tamanho médio do contexto: 6278 caracteres.

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 115 | 0.609 | 0.670 | 0.739 | 0.765 | 0.656 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 12 | 0.250 | 0.333 | 0.500 | 0.500 | 0.315 |
| conceitual_sigla | 6 | 0.000 | 0.167 | 0.500 | 0.667 | 0.177 |
| fato_com_ato | 16 | 0.875 | 0.875 | 0.875 | 0.875 | 0.875 |
| fato_sem_ato | 29 | 0.759 | 0.862 | 0.897 | 0.897 | 0.819 |
| norma_citada | 18 | 0.611 | 0.722 | 0.833 | 0.944 | 0.698 |
| norma_por_tema | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| regra_atual | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 15 | 0.133 | 0.133 | 0.133 | 0.133 | 0.133 |

## Recuperação incluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 115 | 0.687 | 0.774 | 0.843 | 0.861 | 0.744 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 12 | 0.333 | 0.417 | 0.500 | 0.500 | 0.378 |
| conceitual_sigla | 6 | 0.000 | 0.167 | 0.333 | 0.500 | 0.144 |
| fato_com_ato | 16 | 0.875 | 0.875 | 0.875 | 0.875 | 0.875 |
| fato_sem_ato | 29 | 0.759 | 0.862 | 0.897 | 0.897 | 0.819 |
| norma_citada | 18 | 0.611 | 0.722 | 0.833 | 0.889 | 0.686 |
| norma_por_tema | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| regra_atual | 6 | 0.667 | 0.833 | 1.000 | 1.000 | 0.764 |
| revogado | 15 | 0.800 | 0.933 | 1.000 | 1.000 | 0.883 |
