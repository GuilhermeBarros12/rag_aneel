# Resultados da avaliação

## Como reproduzir

```bash
python scripts/avaliar_ouro.py --com-llm --rotulo baseline
```

Sem `--com-llm`, mede só a recuperação e não consome cota de API. Os números completos desta execução estão em [baseline.md](baseline.md) e [baseline.json](baseline.json).

## Conjunto de ouro

[56 perguntas congeladas](conjunto_ouro.md), escritas a partir de atos sorteados com a semente 2027 entre os que têm Texto Integral. Cada resposta foi conferida no texto indexado.

| Categoria | Perguntas |
|---|---|
| Ato citado pelo número | 10 |
| Fato específico, citando o ato | 12 |
| Fato específico, sem citar o ato | 18 |
| Ato revogado | 6 |
| Deve recusar (ato inexistente, fora do período ou domínio, dado ausente) | 10 |

## Baseline

Sistema de 09/11/2026: busca vetorial, top-5, filtro de revogados. LLM único na medição: `groq/openai/gpt-oss-120b`.

| Métrica | Valor |
|---|---|
| hit@1 | 0,087 |
| hit@5 | 0,130 |
| hit@10 | 0,152 |
| MRR | 0,100 |
| Abstenção correta | 1,000 (10 de 10) |
| Recusa indevida | 0,848 (39 de 46) |
| Termos esperados na resposta | 0,130 (6 de 46) |

**Como ler a abstenção:** os 100% não indicam qualidade. O sistema recusa quase tudo porque quase nunca recupera o documento certo. Abstenção correta e recusa indevida precisam ser lidas juntas.

## Melhorias medidas

Mesmo conjunto, no corpus completo e excluindo atos revogados. Os detalhes de cada linha estão em [experimentos/](experimentos/).

| Configuração | hit@5 | MRR | Recusa indevida | Termos esperados | Decisão |
|---|---|---|---|---|---|
| Baseline (vetorial) | 0,130 | 0,100 | 0,848 | 0,130 | Substituído |
| Híbrida, pesos iguais | 0,717 | 0,395 | Não medido | Não medido | Descartada |
| Híbrida, peso 2 no BM25 | 0,739 | 0,639 | Não medido | Não medido | Descartada |
| Híbrida, peso 4 no BM25 | 0,804 | 0,659 | Não medido | Não medido | Descartada |
| Léxica, com mais peso no título | 0,848 | 0,790 | Não medido | Não medido | Descartada |
| Léxica (BM25) | 0,870 | 0,815 | 0,326 | 0,587 | Mantida |
| Léxica com documento identificado no prompt | 0,870 | 0,815 | 0,239 | 0,630 | **Atual** |

A abstenção correta ficou em 1,000 nas três configurações medidas com LLM. A última etapa também corta trechos longos em 4.000 caracteres ao montar o prompt.

Para reproduzir a configuração atual:

```bash
python scripts/avaliar_ouro.py --com-llm --rotulo atual
```

## Política de atos revogados

Medido em 09/11/2026 com `INCLUIR_REVOGADOS=1`, busca léxica e o mesmo LLM. Detalhes em [experimentos/etapa3_revogados_llm.md](experimentos/etapa3_revogados_llm.md).

| Métrica | Excluindo revogados (atual) | Incluindo revogados |
|---|---|---|
| hit@5 | 0,870 | 0,978 |
| MRR | 0,815 | 0,913 |
| Abstenção correta | 1,000 (10 de 10) | 1,000 (10 de 10) |
| Recusa indevida | 0,239 (11 de 46) | 0,174 (8 de 46) |
| Termos esperados na resposta | 0,630 (29 de 46) | 0,674 (31 de 46) |
| Termos esperados nas 6 perguntas sobre atos revogados | 2 de 6 | 5 de 6 |
| Citou um trecho correto | Não medido | 0,848 (39 de 46) |

Nas 6 perguntas sobre atos revogados, a resposta avisou a revogação em todas. Fora desse grupo, uma pergunta (Q40) passou de certa para errada entre as duas rodadas, o que é compatível com a variação do LLM de uma execução para outra.

O padrão do sistema continua excluindo revogados até o dono do projeto decidir.

## Limpeza do índice

153 arquivos de Resoluções Normativas eram páginas de bloqueio do Cloudflare e geraram 306 chunks sem conteúdo. `scripts/limpar_indice.py` cria uma cópia do índice sem eles, com 507.850 chunks. Na cópia limpa, as métricas de recuperação ficaram idênticas às do índice original, tanto na busca léxica quanto na vetorial ([limpo_ouro_lexica.md](experimentos/limpo_ouro_lexica.md), [limpo_ouro_densa.md](experimentos/limpo_ouro_densa.md)). As medições a partir desta seção usam a cópia limpa.

## Perguntas conceituais (prévia)

O conjunto de ouro favorece perguntas com nomes e números. Para testar o outro caso, há um [rascunho de 19 perguntas](conjunto_conceitual_rascunho.md) que não citam o número de um ato. Nelas, um trecho conta como correto quando contém a evidência esperada. O rascunho ainda não foi revisado nem congelado, então estes números são uma prévia.

| Busca | hit@1 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|
| Léxica | 0,211 | 0,526 | 0,579 | 0,307 |
| Vetorial | 0,211 | 0,211 | 0,263 | 0,217 |
| Híbrida (pesos iguais) | 0,105 | 0,368 | 0,579 | 0,264 |

A busca léxica continua à frente, mas acerta bem menos do que no conjunto de ouro (hit@5 de 0,526 contra 0,870). Perguntas conceituais são o ponto fraco atual da recuperação.

## Cabeçalho contextual nos embeddings (descartado)

Hipótese: incluir o título e a ementa do ato no texto de cada chunk, antes de calcular o embedding, ajudaria a busca vetorial a achar o documento certo. Testado com `scripts/exp_cabecalho.py` em um subconjunto de 3.000 documentos (49.263 chunks), com busca exata, excluindo revogados. Como o subconjunto é menor que o corpus, só a diferença entre as linhas é comparável.

| Texto embedado | hit@1 | hit@5 | hit@10 | MRR |
|---|---|---|---|---|
| Só o chunk (atual) | 0,152 | 0,261 | 0,283 | 0,199 |
| Título + chunk | 0,152 | 0,174 | 0,304 | 0,181 |
| Título + ementa + chunk | 0,109 | 0,217 | 0,283 | 0,156 |

Nenhuma variante melhorou o hit@5 nem o MRR, então a ideia foi descartada e o corpus não será reindexado por esse motivo. Uma explicação provável, não testada, é que o modelo lê só 128 tokens, e o cabeçalho ocupa parte desse espaço. Cada variante levou cerca de 55 minutos em CPU. Dados em [experimentos/cabecalho_subconjunto.json](experimentos/cabecalho_subconjunto.json).

## Caminho leve e robustez (10/11/2026)

O acervo léxico passou a guardar também os textos e a metadata dos chunks. Com isso, a busca padrão não usa mais o ChromaDB nem o modelo de embeddings.

| Medida | Antes | Depois |
|---|---|---|
| Arquivos necessários para a busca padrão | Índice vetorial (4,4 GB) e modelo (1,1 GB) | Acervo léxico (0,6 GB) |
| Pico de memória em uma pergunta | 3,2 GB | 113 MB |
| hit@5 e MRR no conjunto de ouro | 0,870 e 0,815 | 0,870 e 0,815 |

As métricas de recuperação ficaram idênticas, medidas apontando o sistema para uma pasta de índice vetorial que não existe. Desde 11/11/2026 o acervo está publicado no Hugging Face. Em uma pasta vazia e sem token, a primeira pergunta baixou só esse arquivo e foi respondida em 19 segundos.

Outras mudanças desta etapa, cobertas por testes: erros temporários de LLM (como 503) ganham uma nova tentativa antes do fallback, cota diária esgotada vai direto para o próximo LLM, e uma busca sem resultados responde sem chamar o LLM.

## Resoluções Normativas recuperadas (11/11/2026)

Das 153 normas que eram páginas de bloqueio, 152 tinham o PDF real em `dados/pdfs`. Elas eram ignoradas por um conflito de nomes: o HTML e o PDF de cada norma geravam o mesmo arquivo `.md`, e o HTML, processado primeiro, impedia o PDF de entrar. A ingestão agora processa o PDF primeiro.

`scripts/atualizar_documentos.py` reindexou só essas 152 normas na cópia limpa do índice, em cerca de 17 minutos de CPU, gerando 9.707 chunks. A cópia passou a ter 517.557 chunks. Nenhum chunk tem marca de bloqueio.

No conjunto de ouro, a recuperação não mudou (hit@5 de 0,870 e MRR de 0,815, em [com_normas_recuperadas.md](experimentos/com_normas_recuperadas.md)). Isso era esperado, porque o conjunto não tem perguntas sobre Resoluções Normativas. Em um teste avulso, a pergunta sobre a REN 1.018/2022 recuperou a norma certa, mas a resposta do LLM foi pobre. Medir a qualidade nessas normas exige perguntas novas no conjunto de avaliação.

## Política intermediária de revogados (11/11/2026)

Decisão do dono do projeto: buscar só nos atos vigentes, mas incluir os revogados quando a pergunta cita um ato específico, pergunta sobre vigência ou revogação, ou quando a busca nos vigentes não acha nada. O prompt sempre pede para avisar a situação do ato. É o novo padrão (`POLITICA_REVOGADOS=intermediaria`).

Recuperação no conjunto de ouro v1, busca léxica ([politica_intermediaria.md](experimentos/politica_intermediaria.md)):

| Política | hit@5 | MRR | hit@5 nas 6 perguntas sobre revogados |
|---|---|---|---|
| Excluir revogados | 0,870 | 0,815 | 1 de 6 |
| Intermediária | 0,935 | 0,870 | 4 de 6 |
| Incluir tudo | 0,978 | 0,913 | 6 de 6 |

As perguntas sobre revogados que continuam perdidas não citam o ato, como "qual empresa foi autorizada a explorar a UFV Paranaíba 10?". É o custo aceito da política: evitar que um ato revogado responda a uma pergunta sobre a regra atual.

## Conjunto de ouro v2 (rascunho, 11/11/2026)

[128 perguntas](conjunto_ouro_v2_rascunho.md), ainda não congeladas. As 56 da versão 1 continuam iguais. Entram 72 novas: 18 sobre Resoluções Normativas citadas pelo número, 3 pelo tema, 6 de regra atual (a norma vigente e a revogada tratam do mesmo tema), 9 sobre atos revogados, 16 de outros atos sorteados, 19 conceituais revisadas e 2 de recusa. Cada resposta foi conferida no texto indexado.

Prévia da recuperação com a política intermediária ([previa_v2_lexica.md](experimentos/previa_v2_lexica.md)): hit@5 de 0,836 nas 116 perguntas com documento ou evidência esperada. Nas 6 de regra atual, o hit@5 foi 1,000: o sistema achou a norma vigente, e não a revogada.

## Comparação de LLMs (11/11/2026)

Conjunto de ouro v1, busca léxica, política intermediária, uma rodada por modelo.

| Métrica | `openai/gpt-oss-120b` (Groq) | `qwen/qwen3.8-27b` (Groq) |
|---|---|---|
| Abstenção correta | 1,000 (10 de 10) | 1,000 (10 de 10) |
| Recusa indevida | 0,174 (8 de 46) | 0,217 (10 de 46) |
| Termos esperados na resposta | 0,696 (32 de 46) | 0,739 (34 de 46) |
| Citou um trecho correto | 0,783 (36 de 46) | 0,804 (37 de 46) |

As diferenças são de 1 a 2 perguntas, dentro da variação de uma rodada para outra, então não há vencedor claro. O `gemini-3.8-flash` não pôde ser medido: devolveu erro 503 (alta demanda) em todas as tentativas da noite de 11/11. Detalhes em [llm_gpt_oss_120b.md](experimentos/llm_gpt_oss_120b.md) e [llm_qwen3_8_27b.md](experimentos/llm_qwen3_8_27b.md).

## Modelo de embedding E5 no subconjunto (11/11/2026)

Hipótese: um modelo treinado para busca (`intfloat/multilingual-e5-base`) recupera melhor que o atual, que foi treinado para paráfrase e lê só 128 tokens. Testado com `scripts/exp_embedding.py` em 2.000 documentos (39.153 chunks), busca exata, sem filtro de revogados, nas 116 perguntas do rascunho v2 ([embedding_e5_subconjunto.json](experimentos/embedding_e5_subconjunto.json)). Como o subconjunto é menor que o corpus, só a diferença entre as colunas é comparável.

| Grupo (hit@5) | n | Léxica | Vetorial atual | Vetorial E5 | Híbrida BM25 + E5 |
|---|---|---|---|---|---|
| Todas | 116 | 0,888 | 0,328 | 0,724 | **0,914** |
| Conceitual: paráfrase | 13 | 0,538 | 0,231 | 0,538 | 0,615 |
| Conceitual: sigla | 6 | 0,500 | 0,333 | 0,833 | 0,667 |
| Fato, citando o ato | 16 | 0,938 | 0,062 | 0,500 | 0,812 |
| Fato, sem citar o ato | 29 | 0,931 | 0,517 | 0,966 | 1,000 |
| Norma citada pelo número | 18 | 0,944 | 0,222 | 0,500 | 1,000 |
| MRR (todas) | 116 | 0,827 | 0,270 | 0,571 | 0,824 |

O E5 mais que dobra a busca vetorial. Com ele, a busca híbrida passa a superar a léxica no hit@5, mas por 3 perguntas em 116, com o MRR praticamente igual: ganha nas conceituais e perde 2 perguntas de fato citando o ato. É um ganho pequeno, que precisaria ser confirmado no corpus inteiro.

Custo de adotar: reindexar os 517.557 chunks com o E5. Pelo ritmo medido em CPU (39.153 chunks em 56 minutos), isso levaria cerca de 12 horas. Com a placa de vídeo seria bem menos, mas exige instalar o PyTorch com CUDA, e esse tempo não foi medido.

## Métrica de citação

A partir de 09/11/2026, a medição com LLM também verifica se a resposta citou, pela marcação `[Trecho N]`, um trecho correto para a pergunta. A medição salva o progresso a cada pergunta e pode ser retomada com o mesmo comando se a cota da API acabar.

Em 7 das 46 perguntas, a resposta citou um trecho correto mas não continha os termos esperados. Isso sugere que a verificação por termos é rigorosa demais em alguns casos, e essas respostas ainda não foram revisadas uma a uma.

**Ainda não concluído:** congelar o conjunto v2 depois da revisão, medir o Gemini, decidir a reindexação com o E5, outros tamanhos de chunk e repetir as rodadas com LLM para medir a variação.

## Limites desta medição

- Resoluções Normativas ficaram de fora: 153 dos 155 arquivos de texto com prefixo `ren` são páginas de bloqueio do Cloudflare.
- O conjunto reflete o corpus, com muitas outorgas de usinas. Perguntas conceituais não foram incluídas.
- "Termos esperados" só verifica se os termos aparecem na resposta. Não avalia a resposta inteira.
- Com 46 perguntas respondíveis, cada pergunta vale 2,2 pontos percentuais. Diferenças pequenas não são conclusivas.
- O RAGAS ainda não foi executado.
