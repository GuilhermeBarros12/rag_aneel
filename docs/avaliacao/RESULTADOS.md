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

## Limites desta medição

- Resoluções Normativas ficaram de fora: 153 dos 155 arquivos de texto com prefixo `ren` são páginas de bloqueio do Cloudflare.
- O conjunto reflete o corpus, com muitas outorgas de usinas. Perguntas conceituais não foram incluídas.
- "Termos esperados" só verifica se os termos aparecem na resposta. Não avalia a resposta inteira.
- Com 46 perguntas respondíveis, cada pergunta vale 2,2 pontos percentuais. Diferenças pequenas não são conclusivas.
- O RAGAS ainda não foi executado.
