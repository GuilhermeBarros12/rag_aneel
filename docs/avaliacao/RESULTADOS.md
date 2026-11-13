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
| Léxica (BM25) | 0,870 | 0,815 | 0,326 | 0,609 | Mantida |
| Léxica com documento identificado no prompt | 0,870 | 0,815 | 0,239 | 0,674 | Substituída pela política intermediária |

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
| Termos esperados na resposta | 0,674 (31 de 46) | 0,717 (33 de 46) |
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

## Conjunto de ouro v2 (congelado em 12/11/2026)

[127 perguntas congeladas](conjunto_ouro_v2.md). O rascunho tinha 128 ([conjunto_ouro_v2_rascunho.md](conjunto_ouro_v2_rascunho.md)); na revisão, a C07 saiu porque a evidência aparece no rodapé de mais de 10 mil chunks, e quatro perguntas passaram a exigir termos mais estritos (C04, C08, C10) ou menos literais (Q082). Antes da primeira medição com LLM, seis perguntas passaram a aceitar formas equivalentes, escritas como `A|B`: "CCEE" na C12, a data numérica na Q098, os valores em MW na Q083, Q102 e Q105, e "art. 33" na Q067, onde o termo "33" sozinho sempre aparecia dentro de "1.033". As métricas de recuperação não mudaram.

As 56 da versão 1 continuam iguais. O rascunho trazia 72 novas: 18 sobre Resoluções Normativas citadas pelo número, 3 pelo tema, 6 de regra atual (a norma vigente e a revogada tratam do mesmo tema), 9 sobre atos revogados, 16 de outros atos sorteados, 19 conceituais revisadas e 2 de recusa. Cada resposta foi conferida no texto indexado.

Prévia da recuperação com a política intermediária ([previa_v2_lexica.md](experimentos/previa_v2_lexica.md)): hit@5 de 0,836 nas 116 perguntas com documento ou evidência esperada. Nas 6 de regra atual, o hit@5 foi 1,000: o sistema achou a norma vigente, e não a revogada.

Recuperação no conjunto congelado, com o sistema padrão: busca léxica, política intermediária e expansão de contexto ([v2_recuperacao.md](experimentos/v2_recuperacao.md)).

| Grupo | n | hit@5 | MRR |
|---|---|---|---|
| Todas com documento ou evidência esperada | 115 | 0,835 | 0,734 |
| Ato citado pelo número | 10 | 1,000 | 0,925 |
| Resolução Normativa citada pelo número | 18 | 0,833 | 0,686 |
| Resolução Normativa pelo tema | 3 | 1,000 | 1,000 |
| Regra atual | 6 | 1,000 | 1,000 |
| Ato revogado | 15 | 0,867 | 0,750 |
| Fato específico, citando o ato | 16 | 0,875 | 0,875 |
| Fato específico, sem citar o ato | 29 | 0,897 | 0,819 |
| Conceitual: paráfrase | 12 | 0,500 | 0,315 |
| Conceitual: sigla | 6 | 0,500 | 0,177 |

A resposta chega ao LLM em 97 das 115 perguntas, com contexto médio de 6,3 mil caracteres. O ponto fraco são as conceituais: sem citar um ato, a busca léxica acha a sigla ou o tema em milhares de chunks e raramente no que define o termo. A medição com LLM nas 127 perguntas ainda não foi feita.

## Nome seguido de numeral como frase (12/11/2026)

Investigação da Q28 ("para qual empresa foi transferida a autorização da Central Geradora Eólica Chuí V?"), a única pergunta que piorou com a expansão de contexto. O ato certo, a REA 10.536/2021, estava só na posição 34 da busca. Os 5 primeiros trechos eram de atos vizinhos, com texto quase idêntico: Chuí II, Chuí IV, Chuí IX e Minuano I e II, todos transferidos para a Omega Geração. Como o BM25 trata o "V" como uma palavra solta e comum, ele não distingue Chuí II, IV e V.

O gabarito aceita esses atos vizinhos como documento esperado, e o termo "Omega Geração" aparece neles. Por isso a métrica dizia que a resposta estava no contexto, e a recusa do modelo contava como indevida. Na verdade, sem nenhum documento sobre a Chuí V, recusar era o comportamento correto. Na rodada antiga, sem expansão, o modelo tinha respondido com a empresa de outra usina. O conjunto v1 está congelado e não foi alterado, mas este caso mostra que a métrica de recuperação é otimista em grupos de atos quase idênticos.

A correção: quando uma palavra é seguida de um numeral romano ou de um número de até 3 dígitos, a consulta inclui também a frase ("chui v", "martina 13"), além das palavras soltas (`FRASES_COM_NUMERAL=1`, o novo padrão). Conjunto v2, só recuperação ([v2_frases_numeral.md](experimentos/v2_frases_numeral.md)):

| Métrica (115 perguntas) | Antes | Com a frase |
|---|---|---|
| hit@1 | 0,678 | 0,713 |
| hit@5 | 0,835 | 0,835 |
| MRR | 0,734 | 0,755 |
| Resposta presente no contexto enviado | 97 | 98 |

Cinco perguntas subiram para a posição 1 (Q23, Q25, Q28, Q066 e Q101), e a Q28 passou a trazer a REA 10.536 em primeiro lugar. Só a Q33 caiu, da posição 1 para a 3, e continuou com a resposta no contexto.

## Conjunto v2 com LLM (12/11/2026)

Conjunto v2 congelado (127 perguntas), busca léxica, política intermediária, expansão de contexto e sem reranker ([v2_llm_gpt_oss_120b.md](experimentos/v2_llm_gpt_oss_120b.md)). O `gpt-oss-120b` esgotou o limite diário de tokens do Groq na pergunta 56. A medição continuou com fallback, registrando o modelo de cada resposta: 58 vieram do `gpt-oss-120b`, 59 do `gpt-oss-20b` e 10 do `qwen3.8-27b`, quando o segundo também esgotou a cota.

| Métrica | Todas | Versão 1 (56) | Novas (71) |
|---|---|---|---|
| Termos esperados na resposta | **94 de 115 (0,817)** | 40 de 46 | 54 de 69 |
| Recusa indevida | 19 de 115 (0,165) | 6 de 46 | 13 de 69 |
| Citou um trecho correto | 90 de 115 (0,783) | 38 de 46 | 52 de 69 |
| Abstenção correta | 12 de 12 | 10 de 10 | 2 de 2 |

| Grupo | Termos esperados | Recusa indevida |
|---|---|---|
| Ato citado pelo número | 10 de 10 | 0 |
| Resolução Normativa citada, pelo tema ou regra atual | 27 de 27 | 0 |
| Ato revogado | 13 de 15 | 1 |
| Fato específico, citando o ato | 13 de 16 | 4 |
| Fato específico, sem citar o ato | 22 de 29 | 6 |
| Conceitual: paráfrase | 7 de 12 | 5 |
| Conceitual: sigla | 2 de 6 | 3 |

Nas 46 perguntas da versão 1, o resultado (40 de 46) ficou a uma pergunta da rodada com só o `gpt-oss-120b` (41 de 46), dentro da variação esperada. As perguntas conceituais concentram 8 das 19 recusas indevidas, o que confirma a recuperação como ponto fraco. A comparação entre modelos dentro desta rodada não é válida, porque cada um respondeu a um bloco diferente de perguntas.

## Reranker da Cohere (12/11/2026)

Conjunto v2 congelado, só recuperação, busca léxica, política intermediária e expansão de contexto. O reranker `rerank-v5.0-pro` reordena os 30 primeiros candidatos da busca antes de escolher os 5 ([v2_rerank_cohere.md](experimentos/v2_rerank_cohere.md), comparado com [v2_recuperacao.md](experimentos/v2_recuperacao.md)). Foram 115 chamadas, uma por pergunta, guardadas em cache.

| Métrica (115 perguntas) | Sem reranker | Com reranker |
|---|---|---|
| hit@1 | 0,678 | 0,774 |
| hit@5 | 0,835 | **0,870** |
| MRR | 0,734 | **0,808** |
| Resposta presente no contexto enviado | 97 | **103** |
| Tamanho médio do contexto | 6,3 mil caracteres | 6,4 mil caracteres |

| Grupo | hit@5 sem | hit@5 com |
|---|---|---|
| Resolução Normativa citada pelo número (18) | 0,833 | 0,944 |
| Fato específico, sem citar o ato (29) | 0,897 | 0,931 |
| Conceitual: sigla (6) | 0,500 | 0,667 |
| Conceitual: paráfrase (12) | 0,500 | 0,500 |

Nenhuma pergunta perdeu o documento certo no top 5. A resposta passou a chegar ao LLM em mais 7 perguntas (Q23, Q085, Q086, Q095, Q099, Q100, C03) e deixou de chegar em 1 (Q28). Nas 46 respondíveis do conjunto v1, o hit@5 ficou em 0,935 e o MRR subiu de 0,870 para 0,908.

O reranker só reordena: as conceituais por paráfrase não melhoraram porque o trecho certo não está entre os 30 candidatos da busca léxica. O custo é uma chamada externa por pergunta, e o plano gratuito da Cohere limita a 1.000 chamadas por mês e 10 por minuto. Por isso o padrão continua `RERANKER=nenhum`.

## Comparação de LLMs (11/11/2026)

Conjunto de ouro v1, busca léxica, política intermediária, uma rodada por modelo.

| Métrica | `openai/gpt-oss-120b` (Groq) | `qwen/qwen3.8-27b` (Groq) |
|---|---|---|
| Abstenção correta | 1,000 (10 de 10) | 1,000 (10 de 10) |
| Recusa indevida | 0,174 (8 de 46) | 0,217 (10 de 46) |
| Termos esperados na resposta | 0,717 (33 de 46) | 0,739 (34 de 46) |
| Citou um trecho correto | 0,783 (36 de 46) | 0,804 (37 de 46) |

As diferenças são de 1 a 2 perguntas, dentro da variação de uma rodada para outra, então não há vencedor claro. O `gemini-3.8-flash` não pôde ser medido: devolveu erro 503 (alta demanda) em todas as tentativas da noite de 11/11. Detalhes em [llm_gpt_oss_120b.md](experimentos/llm_gpt_oss_120b.md) e [llm_qwen3_8_27b.md](experimentos/llm_qwen3_8_27b.md).

## Teste de LLMs com 10 perguntas (12/11/2026)

Grupo de 10 perguntas sorteado do conjunto v1 com a semente 2027 (`scripts/mini_conjunto.py`): 2 de cada tipo, incluindo 2 que devem ser recusadas. Mesma busca e mesma política para todos os modelos.

| Modelo | Onde roda | Recusa indevida | Termos esperados | Citou trecho correto | Abstenção correta | Segundos por resposta |
|---|---|---|---|---|---|---|
| `openai/gpt-oss-120b` (atual) | Groq | 4 de 8 | 4 de 8 | 5 de 8 | 2 de 2 | 2,2 |
| `openai/gpt-oss-20b` | Groq | 4 de 8 | 4 de 8 | 4 de 8 | 2 de 2 | 2,0 |
| `qwen/qwen3.8-27b` | Groq | 4 de 8 | 5 de 8 | 5 de 8 | 2 de 2 | 1,8 |
| `openai/gpt-oss-20b` | Local (LM Studio, RTX 3060 de 8 GB) | 4 de 8 | 4 de 8 | 4 de 8 | 2 de 2 | 153,6 |

Os quatro modelos recusaram exatamente as mesmas 4 perguntas. Nelas, o problema está antes do LLM:
- Em 3 delas (Q02, Q12 e Q33), a busca trouxe o documento certo, mas não o trecho com a resposta. Na Q12 o trecho certo chegou ao prompt, e mesmo assim os quatro recusaram.
- A Q46 pergunta sobre um ato revogado sem citá-lo, e a política intermediária o exclui por decisão de projeto.

Conclusão: neste grupo, trocar de LLM quase não muda o resultado. O gargalo é a recuperação do trecho certo. O `qwen3.8-27b` empatou ou superou o modelo atual e foi o mais rápido, mas a diferença é de uma pergunta. O modelo local responde com a mesma qualidade do `gpt-oss-20b` na nuvem, mas é cerca de 75 vezes mais lento nesta máquina, porque o modelo de 12 GB não cabe nos 8 GB da placa de vídeo.

Depois, com a conta gratuita da Cohere, entraram dois modelos feitos para RAG:

| Modelo | Recusa indevida | Termos esperados | Citou trecho correto | Abstenção correta | Segundos por resposta |
|---|---|---|---|---|---|
| `command-a-03-2025` (Cohere) | 3 de 8 | 5 de 8 | 6 de 8 | 2 de 2 | 9,7 |
| `command-a-plus-05-2026` (Cohere) | 4 de 8 | 5 de 8 | 4 de 8 | 2 de 2 | 2,9 |

O padrão se repetiu. A única diferença foi o `command-a-03-2025` na Q02: em vez de recusar, respondeu com informações secundárias dos trechos e não trouxe a resposta esperada, porque o trecho com ela não estava no prompt.

### O gargalo: a busca acha o documento, mas não o trecho

Nas 46 perguntas respondíveis do conjunto v1, com o sistema atual:

| Medida | Resultado |
|---|---|
| Documento certo entre os 5 trechos enviados ao LLM | 43 de 46 |
| Trecho com a resposta entre os 5 enviados | 36 de 46 |
| Trecho com a resposta entre os 20 primeiros | 38 de 46 |
| O trecho com a resposta existe no documento certo | 46 de 46 |

Em 7 perguntas o documento certo é encontrado, mas o pedaço dele que responde não chega ao LLM. Aumentar o número de trechos quase não resolve, porque o BM25 favorece os trechos que repetem as palavras da pergunta, como o cabeçalho com o número do ato.

**Correção na medição:** os testes revelaram que a conferência de termos não reconhecia hífens tipográficos (‑) nem números com espaço como separador de milhar ("5 821 551,62"), formatos que alguns modelos usam. A normalização foi corrigida e todos os resultados salvos foram recalculados com `scripts/recontar_termos.py`, sem chamar os LLMs de novo. Cada rodada antiga ganhou uma resposta certa, e os números de "termos esperados" neste arquivo já estão corrigidos: busca léxica de 0,587 para 0,609, citação de 0,630 para 0,674, revogados de 0,674 para 0,717 e a rodada do `gpt-oss-120b` de 0,696 para 0,717. O baseline não mudou.

## Expansão de contexto com LLM (12/11/2026)

Conjunto v1 completo, `groq/openai/gpt-oss-120b`, busca léxica e política intermediária. A única diferença entre as rodadas é a expansão de contexto ([llm_gpt_oss_120b_expansao.md](experimentos/llm_gpt_oss_120b_expansao.md)).

| Métrica | Sem expansão | Com expansão |
|---|---|---|
| Resposta presente no contexto enviado | 36 de 46 | 43 de 46 |
| Termos esperados na resposta | 0,717 (33 de 46) | **0,891 (41 de 46)** |
| Recusa indevida | 0,174 (8 de 46) | 0,130 (6 de 46) |
| Citou um trecho correto | 0,783 (36 de 46) | 0,848 (39 de 46) |
| Abstenção correta | 1,000 (10 de 10) | 1,000 (10 de 10) |
| Tamanho médio do contexto | 1,9 mil caracteres | 6,2 mil caracteres |

Nove perguntas passaram a ter a resposta certa, e uma piorou: na Q28, a resposta estava no contexto e o modelo recusou mesmo assim. A expansão passou a ser o padrão (`EXPANSAO_CONTEXTO=documento`). O custo é um contexto cerca de 3 vezes maior, o que gasta mais cota e exigiu espaçar as perguntas da medição em 20 segundos, por causa do limite por minuto do Groq.

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
