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

Incluir atos revogados elevaria o hit@5 da busca léxica para 0,978, sem piorar os outros grupos. Essa política continua desligada porque seu efeito nas respostas ainda não foi medido.

**Ainda não concluído:** cabeçalho contextual nos embeddings, outros tamanhos de chunk, troca do modelo de embedding e o efeito da busca léxica em perguntas conceituais.

## Limites desta medição

- Resoluções Normativas ficaram de fora: 153 dos 155 arquivos de texto com prefixo `ren` são páginas de bloqueio do Cloudflare.
- O conjunto reflete o corpus, com muitas outorgas de usinas. Perguntas conceituais não foram incluídas.
- "Termos esperados" só verifica se os termos aparecem na resposta. Não avalia a resposta inteira.
- Com 46 perguntas respondíveis, cada pergunta vale 2,2 pontos percentuais. Diferenças pequenas não são conclusivas.
- O RAGAS ainda não foi executado.
