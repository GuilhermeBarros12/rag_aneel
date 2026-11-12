# Roadmap: o que falta para o `rag_aneel` ficar robusto

Escrito em 09/11/2026. Prazo do projeto: **17/11/2026** (inscrição no GEN IA 2027 do iFood).

Este documento é para quem vai executar o trabalho, pessoa ou modelo, sem ter acompanhado as sessões anteriores. Cada etapa descreve o objetivo, o motivo e como saber que terminou. A forma de implementar fica a seu critério, desde que respeite as regras abaixo.

## 1. Onde o projeto está

O PR #1 foi mergeado em `main`, com as Fases 0 a 2 completas e a Fase 3 parcial. Comece sempre com `git switch main` e `git pull`, e crie uma branch nova a partir dali.

**Como o sistema funciona hoje**

| Arquivo | Papel |
|---|---|
| `scripts/config.py` | Configuração única: caminhos, modelos, prompt, modo de busca |
| `scripts/nucleo.py` | Recuperação, montagem do prompt e geração com fallback (Gemini, depois Groq) |
| `scripts/lexico.py` | Índice BM25 em SQLite FTS5, criado a partir dos chunks do ChromaDB |
| `scripts/pipeline.py` | Linha de comando do RAG |
| `scripts/avaliar_ouro.py` | Métricas no conjunto de ouro: hit@k, MRR, abstenção, recusa indevida, termos |
| `scripts/avaliar.py` | Benchmark antigo de 100 perguntas, sem gabarito |
| `scripts/exp_cabecalho.py` | Experimento inacabado (ver etapa 2.3) |
| `docs/avaliacao/` | Conjunto de ouro congelado, baseline e experimentos |

A busca padrão é léxica (`MODO_BUSCA=lexica`). Os modos `densa` e `hibrida` existem, mas mediram pior.

**Números medidos** (conjunto v1, 56 perguntas, corpus completo, LLM `groq/openai/gpt-oss-120b`)

| Métrica | Baseline vetorial | Atual (léxica, política intermediária, expansão de contexto) |
|---|---|---|
| hit@5 | 0,130 | 0,935 |
| MRR | 0,100 | 0,870 |
| Resposta presente no contexto enviado | não medido | 43 de 46 |
| Abstenção correta | 1,000 | 1,000 |
| Recusa indevida | 0,848 | 0,130 |
| Termos esperados na resposta | 0,130 | 0,891 |

O índice publicado tem 517.557 chunks de atos de 2016, 2021 e 2022, já sem as páginas de bloqueio e com as Resoluções Normativas recuperadas.

**Andamento em 09/11/2026** (branch `refino/etapas-1-2`, detalhes em `docs/avaliacao/RESULTADOS.md`)

| Etapa | Situação |
|---|---|
| 1.1 Cópia limpa do índice | Feita em 11/11/2026: índice limpo publicado e repositório do Hugging Face recriado, então as versões antigas com o IP não podem mais ser baixadas. Backup local do índice anterior em `backup_indice_publicado/` |
| 1.2 Recusar páginas de bloqueio | Feita, com testes em `tests/test_validacao.py` |
| 1.3 Recuperar as Resoluções Normativas | Feita e publicada: 152 normas reindexadas a partir dos PDFs. Falta `ren2021912`, sem PDF |
| 2.1 Política de revogados | Feita: política intermediária adotada como padrão (hit@5 de 0,935 no conjunto v1) |
| 2.2 Perguntas conceituais | Feita: conjunto v2 revisado e congelado em 12/11/2026, com 127 perguntas. hit@5 de 0,835; nas conceituais, 0,500. Falta a medição com LLM |
| 2.3 Cabeçalho contextual | Concluída e descartada: não melhorou a busca vetorial |
| 2.4 Melhorias da busca vetorial | E5 testado no subconjunto: a híbrida com E5 chegou a 0,914 de hit@5, contra 0,888 da léxica. Falta decidir a reindexação (cerca de 12 h em CPU) |
| 2.5 Fortalecer a medição | Citação de trecho correto e retomada feitas. Falta repetir rodadas para medir a variação |
| 3.1 Falhas de LLM | Feita: nova tentativa em erro temporário, cota esgotada vai direto ao fallback, com testes |
| 3.2 Não carregar o que não é usado | Feita: 113 MB de pico na busca léxica, contra 3,2 GB antes |
| 3.3 Caminho leve | Feita e publicada: o acervo léxico (0,6 GB) está no Hugging Face, e a busca padrão funciona baixando só ele |
| 3.4 Limpeza de comportamento | Feita: sem criação de pastas ao importar, pergunta sem termos responde sem LLM, aviso de acervo desatualizado, `avaliar.py` marcado como legado |
| 4.1 Testes | Feita: 42 testes com pytest |
| 4.2 Lint e CI | Feita: ruff sem erros e CI passando no GitHub |
| 4.3 Instalação reproduzível | Feita: o CI instala tudo do zero em Linux com Python 3.12 e os testes passam |
| 4.4 Docker | Revisado, mas não testado: o Docker não está instalado nesta máquina. O README avisa |
| 5 Demo | Feita: `python scripts/app.py`, testada de ponta a ponta. Falta captura de tela no README e publicação opcional em um Space |
| Comparação de LLMs | Feita para `gpt-oss-120b` e `qwen3.8-27b`, sem vencedor claro. O Gemini não pôde ser medido (erro 503) |
| Expansão de contexto | Feita e adotada: termos esperados de 33 para 41 de 46 no conjunto v1, abstenção mantida |

## 2. Regras de trabalho

Valem para todas as etapas. Elas vêm do dono do projeto e não são negociáveis.

1. **Meça antes e depois.** Toda mudança de recuperação ou geração roda no mesmo conjunto de ouro. Se o número não melhorar, descarte a mudança e registre o resultado. Um descarte com número também é entrega.
2. **Não altere `docs/avaliacao/conjunto_ouro.json`.** Ele está congelado. Perguntas novas vão para um arquivo novo.
3. **Não invente números.** O que não foi medido aparece como "não medido".
4. **Não toque em `vectorstore/`, `dados/` nem no `.env`.** Trabalhe em uma cópia do índice, apontando `VECTORSTORE_DIR` para ela. Nunca imprima chaves.
5. **Pergunte ao Guilherme antes de:** reindexar o corpus inteiro, publicar ou apagar algo no Hugging Face, instalar pacotes pesados (como torch com CUDA), dar push ou apagar arquivos.
6. **Código simples e comentado em português.** O Guilherme é estudante e precisa conseguir explicar cada decisão numa entrevista.
7. **Uma branch por etapa** (`refino/...`), com commits pequenos em português.
8. **Ao terminar uma etapa,** atualize `docs/avaliacao/RESULTADOS.md` e o `README.md` se algum número ou comportamento mudou, e marque a etapa neste roadmap.

## 3. Armadilhas já conhecidas

- **Cota do Groq:** 200 mil tokens por dia. Cerca de três rodadas completas de `avaliar_ouro.py --com-llm` esgotam a cota. Planeje uma ou duas rodadas com LLM por dia e use a medição sem LLM para iterar.
- **Gemini instável:** o `gemini-3.8-flash` já levou 233 s e já deu 503. Por isso as medições usam só o Groq (`LLM_AVALIACAO=groq`).
- **Ambiente:** Windows, Python 3.14.3 em `.venv`, torch sem CUDA (a máquina tem uma RTX 3060 sem uso). O `gh` não está instalado.
- **Índice léxico:** fica em `vectorstore_lexico/` e é criado a partir do índice que `VECTORSTORE_DIR` apontar. Se o conteúdo do índice mudar, o léxico precisa ser recriado.
- **Conjunto de ouro favorece o BM25:** as perguntas citam nomes e números. Nenhuma pergunta conceitual foi medida, então a vantagem da busca léxica pode ser menor do que parece.
- **Verificação de termos é fraca:** ela só confere se os termos aparecem na resposta. Uma resposta pode conter "120" e estar errada.

## 4. Etapas, em ordem de prioridade

### Etapa 1: privacidade e limpeza do corpus

**Por que vem primeiro:** há um endereço IP exposto em um repositório público.

**1.1 Remover as páginas de bloqueio do índice**
- **Problema:** 153 dos 155 arquivos de texto de Resoluções Normativas (prefixo `ren`) são páginas de bloqueio do Cloudflare. Elas geraram 306 chunks de lixo, e 153 deles contêm um IP, provavelmente o da conexão do Guilherme no dia do download. Esses chunks estão no dataset público `guilhermebarros/rag-aneel-vectorstore`.
- **Objetivo:** produzir uma cópia do índice sem esses chunks e recriar o índice léxico a partir dela.
- **Aceite:** nenhuma ocorrência de `Cloudflare` nem de padrão de IP nos textos do índice; contagens do README e do `RESULTADOS.md` atualizadas; métricas do conjunto de ouro repetidas e sem piora.
- **Cuidado:** a troca do índice original e a republicação no Hugging Face são decisões do Guilherme. Apagar o arquivo não remove versões antigas do repositório, então o histórico precisa ser limpo ou o repositório recriado.

**1.2 Impedir que isso se repita**
- **Objetivo:** os scripts de download e de ingestão devem rejeitar páginas de bloqueio e registrar o arquivo em um log de falhas, em vez de salvar a página como se fosse o documento.
- **Aceite:** um teste com um HTML de bloqueio de exemplo mostra que ele é rejeitado.

**1.3 Recuperar as Resoluções Normativas (opcional)**
- **Objetivo:** ter o texto real das 153 normas. Elas são o tipo de ato mais importante do corpus e hoje estão ausentes.
- **Cuidado:** não contorne o bloqueio por script. O Guilherme baixa pelo navegador, e você só ingere, divide em chunks e indexa os arquivos novos.
- **Aceite:** as normas aparecem no índice e ganham perguntas próprias em um conjunto novo (ver 2.2).

### Etapa 2: terminar as medições da Fase 3

**2.1 Política de atos revogados**
- **Situação:** só na recuperação, incluir revogados leva o hit@5 de 0,870 para 0,978 sem piorar os outros grupos. A medição com LLM parou na cota.
- **Objetivo:** rodar `avaliar_ouro.py --com-llm` com `INCLUIR_REVOGADOS=1` e decidir o padrão. O que importa é se o modelo avisa que o ato está revogado e se a abstenção correta continua em 1,000.
- **Aceite:** decisão registrada no `RESULTADOS.md`, com os números, e o padrão do `config.py` coerente com ela.

**2.2 Perguntas conceituais**
- **Objetivo:** descobrir se a busca léxica continua melhor quando a pergunta não cita nomes nem números. Crie um segundo conjunto, de 15 a 20 perguntas (por exemplo: "como a ANEEL trata recurso contra auto de infração?"), com os documentos aceitos como corretos.
- **Cuidado:** o Guilherme revisa as perguntas antes de congelar. Use um arquivo novo, como `conjunto_conceitual.json`.
- **Aceite:** tabela comparando os modos `lexica`, `densa` e `hibrida` nesse conjunto. Se a híbrida ganhar nele, avalie escolher o modo conforme a pergunta (por exemplo, léxica quando a pergunta cita o número de um ato).

**2.3 Cabeçalho contextual nos embeddings**
- **Situação:** `scripts/exp_cabecalho.py` monta um subconjunto de 3.000 documentos (49.091 chunks) e compara o embedding atual com variantes que incluem título e ementa. A execução terminou com código de saída 4, sem mensagem, logo depois de imprimir a contagem de chunks.
- **Objetivo:** descobrir a causa, que provavelmente é memória ou tempo ao recalcular embeddings em CPU, e concluir o experimento. Reduzir o subconjunto ou o lote é aceitável.
- **Aceite:** resultado salvo em `docs/avaliacao/experimentos/`, com a decisão. Só proponha reindexar o corpus inteiro se o ganho for claro, e pergunte antes.

**2.4 Só se 2.2 mostrar que a busca vetorial importa**
- Remover chunks duplicados (34,4% são cópias exatas).
- Testar chunks maiores e tratar tabelas (o modelo lê só 128 tokens, e 30,2% dos chunks passam disso).
- Comparar com um modelo de embedding feito para recuperação, como a família E5 ou o BGE-M3.
- Testar um reranker multilíngue sobre os candidatos.

Cada item segue a regra de medir no subconjunto antes de qualquer reindexação.

**2.5 Fortalecer a própria medição**
- **Objetivo:** tornar os números mais confiáveis. Três melhorias, em ordem de valor:
  1. Medir se a resposta cita o documento esperado, o que pegaria casos como a Q10 do baseline, respondida com base em outro ato.
  2. Salvar o progresso de `avaliar_ouro.py` a cada pergunta, para que um erro de cota não perca a rodada inteira.
  3. Repetir a rodada com LLM para saber quanto os números variam.
- **Aceite:** métrica nova documentada no `RESULTADOS.md` e rodada retomável após interrupção.

### Etapa 3: robustez de execução

**3.1 Falhas de LLM**
- **Objetivo:** o sistema deve sobreviver a erros temporários. Hoje um 429 ou 503 leva direto ao fallback ou ao erro final.
- **Aceite:** nova tentativa com espera para erros temporários, com limite de tentativas, e mensagem clara ao usuário quando a cota acabar.

**3.2 Não carregar o que não é usado**
- **Problema:** `carregar_recursos()` em `nucleo.py` sempre carrega o modelo de embeddings, mesmo no modo léxico, que não precisa dele. Isso custa cerca de 3 GB de RAM e o download de 1,1 GB.
- **Objetivo:** carregar o modelo de embeddings só nos modos `densa` e `hibrida`.
- **Aceite:** pico de memória medido no modo léxico e registrado no README.

**3.3 Caminho leve para quem só quer testar**
- **Problema:** mesmo no modo léxico, o sistema baixa o índice de 4,4 GB, porque os textos e a metadata dos chunks vêm do ChromaDB.
- **Objetivo:** permitir rodar o modo léxico com um único arquivo pequeno, que contenha textos, metadata e o índice BM25.
- **Aceite:** em uma pasta limpa, o sistema responde a uma pergunta sem baixar o índice vetorial. O tamanho do download fica documentado.
- **Cuidado:** publicar esse arquivo no Hugging Face é decisão do Guilherme.

**3.4 Limpeza de comportamento**
- `chunking.py` e `ingestao.py` criam pastas ao serem importados. Mova isso para a função principal.
- Trate pergunta vazia ou sem termos úteis com uma mensagem clara.
- Decida o destino do `avaliar.py`: remover ou marcar como legado no README.
- Detecte índice léxico desatualizado em relação ao índice vetorial e avise.

### Etapa 4: engenharia

**4.1 Testes automatizados**
- **Objetivo:** testes com `pytest` que rodem sem rede, sem chaves e sem o índice real.
- **Cobertura mínima:** leitura da metadata, chunking, montagem do prompt, normalização de números e montagem da consulta léxica, fusão RRF, funções de métrica e a recuperação em uma coleção minúscula criada pelo próprio teste.
- **Aceite:** `pytest` passa em uma instalação limpa.

**4.2 Lint e integração contínua**
- **Objetivo:** `ruff` configurado e um workflow do GitHub Actions que rode lint e testes a cada push.
- **Aceite:** o workflow passa no GitHub.

**4.3 Instalação reproduzível**
- **Objetivo:** confirmar que o projeto instala do zero. O `requirements.txt` só foi conferido contra o `.venv` atual, em Python 3.14.3.
- **Aceite:** instalação testada em ambiente limpo, com a versão de Python suportada declarada no README e em um `pyproject.toml`. Adicione um `.gitattributes` para acabar com os avisos de fim de linha.

**4.4 Docker**
- **Problemas conhecidos:** chave `version` obsoleta no `docker-compose.yml`; `docs/avaliacao/` e `vectorstore_lexico/` não são montados; nunca foi testado.
- **Aceite:** a imagem é construída e responde a uma pergunta. Se não houver tempo, remova as instruções de Docker do README em vez de deixar algo não testado.

### Etapa 5: demo

- **Objetivo:** uma interface simples, em Gradio ou Streamlit, que mostre a resposta, o LLM usado e os documentos citados, com o título e a situação de cada ato.
- **Depende de:** etapa 3.3, para o recrutador testar sem baixar 4,4 GB.
- **Aceite:** um comando sobe a demo localmente, e o README mostra uma captura de tela. Publicar em um Hugging Face Space é opcional e fica com o Guilherme.

### Etapa 6: RAGAS

- **Objetivo:** complementar as métricas próprias com fidelidade e relevância, usando um juiz configurado de forma explícita (Groq ou Gemini), nunca o padrão da biblioteca, que é a OpenAI.
- **Custo estimado:** de 8 a 10 chamadas por pergunta, cerca de 370 a 460 chamadas e de 460 a 600 mil tokens nas 46 perguntas respondíveis. Isso passa da cota diária do Groq, então divida em dias ou use uma amostra, e diga qual foi a escolha.
- **Dependências que faltam no `.venv`:** `datasets`, `tiktoken` e as demais exigidas pelo `ragas` 0.4.3.
- **Aceite:** tabela comparando o baseline (commit `fcb5ea5`) com o sistema final, com a versão do RAGAS e o juiz documentados.
- **Cuidado:** peça aprovação do Guilherme antes de gastar a cota.

### Etapa 7: agente (opcional)

- **Objetivo:** um agente mínimo com ferramentas como `buscar_documentos`, `ler_documento` e `verificar_vigencia`, avaliado nos mesmos conjuntos.
- **Regra de corte:** só comece se as etapas 1 a 5 estiverem prontas. Se o agente não melhorar os números, registre isso e não o inclua.

### Etapa 8: material de portfólio

- README reescrito: problema, arquitetura em diagrama Mermaid, tabela de resultados, decisões tomadas e descartadas, limitações e como reproduzir.
- Rascunho do card do dataset no Hugging Face. O Guilherme publica.
- Três ou quatro linhas para currículo e LinkedIn, só com números medidos.
- Roteiro de um artigo curto. O material mais forte é a história real: o sistema estava fora do ar, a avaliação nunca havia rodado, e a busca léxica simples venceu a vetorial por larga margem.
- Lista de perguntas difíceis de entrevista, com respostas curtas e honestas. Inclua as fraquezas: conjunto pequeno, viés para o BM25 e Resoluções Normativas ausentes.
- Sugestão de descrição e de topics para o repositório no GitHub. O Guilherme aplica.

## 5. Ordem sugerida até 17/11

| Dias | Etapas | Observação |
|---|---|---|
| 1 | 1.1, 1.2, 2.1 | A 2.1 gasta uma rodada da cota do Groq |
| 2 | 2.2, 2.5 | O Guilherme revisa as perguntas conceituais |
| 3 | 3.1 a 3.4 | A 3.3 destrava a demo |
| 4 | 4.1 a 4.3 | Testes e CI |
| 5 | 5 e 4.4 | Demo; Docker só se sobrar tempo |
| 6 | 2.3 e 6 | Experimento do cabeçalho e RAGAS, conforme a cota |
| 7 e 8 | 8 | Portfólio e revisão final |

Se o tempo apertar, corte nesta ordem: etapa 7, etapa 2.4, etapa 4.4, etapa 6, etapa 1.3. As etapas 1.1, 2.1, 2.2, 3, 4.1 e 8 são as que mais pesam para o projeto ser defensável.

## 6. Decisões que cabem ao Guilherme

- Republicar o índice no Hugging Face sem o IP e limpar o histórico do dataset.
- Baixar as Resoluções Normativas pelo navegador.
- Aprovar as perguntas conceituais antes de congelar.
- Autorizar a instalação do torch com CUDA, caso haja reindexação.
- Autorizar o gasto de cota com o RAGAS.
- Escolher o padrão para atos revogados, depois de ver os números da etapa 2.1.
