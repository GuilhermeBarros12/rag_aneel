# Resultados: previa_v2_lexica

Executado em 2026-11-11T15:16:59.104423+00:00. Conjunto: `conjunto_ouro_v2_rascunho.json`.
Busca: `lexica`. Embedding: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`. Chunks recuperados pelo sistema: 5. Política de revogados: `intermediaria`.

## Recuperação com a política de revogados do sistema

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 116 | 0.681 | 0.759 | 0.836 | 0.853 | 0.737 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 13 | 0.308 | 0.385 | 0.538 | 0.538 | 0.368 |
| conceitual_sigla | 6 | 0.000 | 0.167 | 0.500 | 0.667 | 0.177 |
| fato_com_ato | 16 | 0.875 | 0.875 | 0.875 | 0.875 | 0.875 |
| fato_sem_ato | 29 | 0.759 | 0.862 | 0.897 | 0.897 | 0.819 |
| norma_citada | 18 | 0.611 | 0.722 | 0.833 | 0.889 | 0.686 |
| norma_por_tema | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| regra_atual | 6 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| revogado | 15 | 0.667 | 0.800 | 0.867 | 0.867 | 0.750 |

## Recuperação excluindo revogados

| Grupo | n | hit@1 | hit@3 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|---|---|
| Todas com documento esperado | 116 | 0.612 | 0.672 | 0.741 | 0.767 | 0.659 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 13 | 0.308 | 0.385 | 0.538 | 0.538 | 0.368 |
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
| Todas com documento esperado | 116 | 0.681 | 0.776 | 0.845 | 0.862 | 0.742 |
| ato_citado | 10 | 0.900 | 0.900 | 1.000 | 1.000 | 0.925 |
| conceitual_parafrase | 13 | 0.308 | 0.462 | 0.538 | 0.538 | 0.387 |
| conceitual_sigla | 6 | 0.000 | 0.167 | 0.333 | 0.500 | 0.144 |
| fato_com_ato | 16 | 0.875 | 0.875 | 0.875 | 0.875 | 0.875 |
| fato_sem_ato | 29 | 0.759 | 0.862 | 0.897 | 0.897 | 0.819 |
| norma_citada | 18 | 0.611 | 0.722 | 0.833 | 0.889 | 0.686 |
| norma_por_tema | 3 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| regra_atual | 6 | 0.667 | 0.833 | 1.000 | 1.000 | 0.764 |
| revogado | 15 | 0.800 | 0.933 | 1.000 | 1.000 | 0.883 |
