# Decisões e aprendizados

Este documento reúne as principais escolhas do projeto, o que foi testado e descartado, e o que ficou aprendido. Os números vêm dos conjuntos de ouro, perguntas com documento e resposta esperados, e cada um tem a rodada correspondente em [avaliacao/RESULTADOS.md](avaliacao/RESULTADOS.md).

## Como as decisões foram tomadas

1. **Medir antes de mudar.** A primeira etapa foi escrever um gabarito: 56 perguntas a partir de atos sorteados com semente fixa, cada resposta conferida no texto indexado. O conjunto foi congelado antes dos experimentos, para que nenhuma mudança fosse avaliada em perguntas escolhidas depois.
2. **Uma mudança por rodada.** Cada experimento altera uma coisa só e é comparado com a configuração anterior no mesmo conjunto.
3. **Registrar também o que não funcionou.** Um experimento descartado continua documentado, com os números.

## Decisões adotadas

### Busca léxica (BM25) em vez de vetorial

A primeira versão usava só embeddings. No conjunto de ouro, o documento certo aparecia entre os 5 primeiros trechos em 13% das perguntas. Com BM25 em SQLite FTS5, em 87%.

**Por quê:** as perguntas citam números de atos, nomes de empresas e de usinas, e o modelo de embeddings (`paraphrase-multilingual-mpnet-base-v2`) não lê o título nem o número do ato no chunk, além de considerar só 128 tokens. A busca por palavras acerta esses identificadores.

**Efeito colateral bom:** a busca padrão deixou de precisar do índice vetorial (4,4 GB) e do modelo (1,1 GB). Basta o acervo léxico, de 0,6 GB, e o pico de memória por pergunta caiu de 3,2 GB para 113 MB.

### Política intermediária para atos revogados

Excluir os revogados evita que uma norma antiga responda a uma pergunta sobre a regra atual, mas deixa sem resposta quem pergunta justamente por um ato revogado. Incluir tudo resolve isso e cria o risco oposto.

A política adotada busca só nos vigentes, mas inclui os revogados quando a pergunta cita um ato, pergunta sobre vigência ou quando nada vigente é encontrado. O hit@5 no conjunto v1 subiu de 0,870 para 0,935. Nas 6 perguntas de "regra atual" do conjunto v2, em que a norma vigente e a revogada tratam do mesmo tema, o sistema achou a vigente em todas. O custo aceito: perguntas sobre fatos de um ato revogado que não o citam continuam perdidas.

### Expansão de contexto

Testar seis LLMs em 10 perguntas mostrou que todos recusavam as mesmas perguntas. A causa estava antes do LLM: o documento certo chegava ao prompt em 43 de 46 perguntas, mas o trecho com a resposta só em 36. O BM25 favorece os trechos que repetem as palavras da pergunta, como o cabeçalho com o número do ato, e mandar 20 trechos em vez de 5 resolvia só mais 2.

A solução foi enviar ao LLM o documento inteiro, quando curto, ou os trechos encontrados e seus vizinhos, quando longo. A resposta passou a chegar ao prompt em 43 de 46, e as respostas com os termos esperados subiram de 33 para 41 de 46, sem perder nenhuma recusa correta. O custo é um contexto cerca de 3 vezes maior.

### Reranker opcional

O `rerank-v5.0-pro` da Cohere reordena os 30 primeiros candidatos da busca. No conjunto v2, o hit@5 subiu de 0,835 para 0,870, e a resposta passou a chegar ao LLM em 103 de 115 perguntas, contra 97. Ficou desligado por padrão porque depende de um serviço externo, e o plano gratuito permite 1.000 chamadas por mês.

## Experimentos descartados

| Experimento | Resultado | Por que foi descartado |
|---|---|---|
| Busca híbrida (embeddings + BM25 com RRF) | hit@5 de 0,717 a 0,804, conforme o peso do BM25 | Sempre abaixo da léxica pura (0,870) |
| Mais peso no título no BM25 | hit@5 de 0,848 | Abaixo da léxica com pesos iguais |
| Título e ementa no texto embedado | Nenhuma variante melhorou o hit@5 ou o MRR em um subconjunto de 3.000 documentos | Provavelmente porque o modelo lê só 128 tokens, e o cabeçalho ocupa esse espaço |
| Trocar o LLM | Seis modelos (Groq, Cohere e um local) recusaram as mesmas perguntas | O gargalo era a recuperação, não o modelo |
| Gemini na medição | Erro 503 (alta demanda) em todas as tentativas | Não foi possível medir |

## Em aberto

- **Embedding E5:** em um subconjunto, a busca híbrida com `multilingual-e5-base` superou a léxica por 3 perguntas em 116, com ganho nas conceituais. Adotar exige reindexar 517 mil chunks, cerca de 12 horas em CPU, para um ganho que ainda precisa ser confirmado no corpus inteiro.
- **Perguntas conceituais:** sem citar um ato, a busca léxica encontra a sigla ou o tema em milhares de chunks e raramente no que define o termo. O hit@5 é de 0,500, e o reranker não ajuda, porque o trecho certo não chega a estar entre os candidatos.
- **Variação entre rodadas:** cada medição com LLM foi feita uma vez. Diferenças de 1 ou 2 perguntas estão dentro da variação esperada de uma rodada para outra.

## Aprendizados

- **A métrica também tem bugs.** A conferência de termos não reconhecia hífens tipográficos nem números com espaço como separador de milhar. Uma resposta certa contava como errada, e todos os resultados foram recalculados depois da correção.
- **Uma abstenção de 100% pode esconder um problema.** A primeira versão recusava 10 de 10 perguntas sem resposta, mas também 39 de 46 com resposta. As duas métricas precisam ser lidas juntas.
- **O dado de entrada importava mais do que o modelo.** 153 Resoluções Normativas no índice eram páginas de bloqueio do Cloudflare, e não o texto da norma. Corrigir a ingestão recuperou 152 delas.
- **Segurança faz parte do projeto.** O índice publicado no Hugging Face guardava um dado da conexão de quem o gerou. O repositório foi recriado limpo, para que as versões antigas não pudessem mais ser baixadas.
