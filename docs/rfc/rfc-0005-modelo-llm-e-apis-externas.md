---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0005 — Modelo de LLM e APIs externas

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0002-integracao-langsmith]] · [[rfc-0003-banco-postgres-pgvector]] · [[rfc-0004-geracao-de-embeddings]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define requisitos conceituais do uso de modelos de linguagem e das APIs externas. Não é especificação final. Parâmetros finos, como formato de ferramentas e textos de instrução, ficam para RFCs e ADRs próprios.

## 1. Resumo executivo (TL;DR)

Propomos usar o Claude Haiku 5.5 para conduzir a conversa do agente, que é o modelo mais barato da família, e o Claude Opus 5.5 para o papel de juiz, que é mais completo e mais caro. A cotação é uma ferramenta que o modelo chama, e a aplicação garante que todo preço venha da API oficial.

O modelo é fixado por identificador exato de versão. Cada conversa tem um teto de cerca de 50 mil tokens. Erros transitórios têm até três tentativas com espera curta. Se persistirem, a conversa segue para um humano. As respostas são o mais determinísticas possível.

As únicas chamadas externas são a API da Anthropic, o LangSmith e o download único do modelo de embeddings. A chave fica no `.env`.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige que o agente só informe valores vindos da cotação oficial (RF-05), que nenhum preço seja inventado quando a infraestrutura falha (RNF-04) e que dados pessoais não apareçam sem máscara (RNF-01).

A [[rfc-0002-integracao-langsmith]] exige que as avaliações sejam comparáveis entre rodadas. Isso depende de um modelo fixo e de respostas repetíveis.

Esta RFC define qual modelo é usado, como a cotação é acessada e como as falhas da API externa são tratadas.

## 3. Proposta conceitual

### 3.1 Modelo do agente

O agente é conduzido pelo Claude Haiku 5.5. É o modelo mais rápido e barato da família, o que reduz o custo da conversa, que é o caminho mais frequente.

Haiku pode perder qualidade em conversas longas ou em regras mais complexas. Esse risco é tratado na seção 7. Se os testes mostrarem regressão, a troca por um modelo mais forte é uma decisão de nova RFC ou ADR, sem mudar o resto do desenho.

### 3.2 Modelo do juiz

O juiz usa o Claude Opus 5.5, um modelo mais completo que o agente. Ele precisa julgar se uma resposta respeita as regras do PRD, o que exige mais capacidade do que conduzir a conversa.

O juiz e o agente usam modelos diferentes de propósito. Assim, um erro do agente tem menos chance de passar despercebido pelo juiz. O juiz também é avaliado pelos casos de teste da [[rfc-0002-integracao-langsmith]], com o mesmo critério de regressão.

O juiz é mais caro por token. Por isso, o custo por conversa depende do volume de chamadas ao juiz, e isso é acompanhado pelos traces.

### 3.3 Cotação como ferramenta

A cotação é uma ferramenta que o modelo pode chamar. Ela recebe os dados coletados e devolve os três planos, ou uma recusa, ou uma falha.

O modelo decide quando cotar, mas não escreve o preço nem os dados da chamada. A aplicação preenche os argumentos da cotação a partir do estado, inclusive o CEP, que o modelo não recebe sem máscara. O valor vem sempre do resultado da ferramenta, e a aplicação confere que a resposta do agente só cita valores presentes nesse resultado. Isso sustenta o RF-05 do PRD.

No MVP, a aplicação chama a API de cotação diretamente, sem servidor MCP. Um servidor MCP é ponto de melhoria para versões futuras, conforme a [[adr-0019-chamada-direta-cotacao-mcp-futuro]].

### 3.4 Versão fixa

O modelo é usado pelo identificador exato de versão, nunca por alias que muda sozinho. Assim, a mesma conversa ou o mesmo caso de teste roda com o mesmo modelo em rodadas diferentes, e as avaliações no LangSmith ficam comparáveis.

Atualizar a versão é uma mudança deliberada, registrada na rastreabilidade, seguida de nova rodada de avaliação.

### 3.5 Determinismo

As chamadas usam a configuração mais determinística possível, com temperatura baixa. Isso facilita repetir um caso de teste e comparar rodadas.

Determinismo total não é garantido pela API. Por isso, a regressão é medida por casos, e não por uma resposta exata.

### 3.6 Teto de tokens por conversa

Cada conversa tem um teto de cerca de 50 mil tokens, somando entradas e saídas de todas as chamadas do agente e do juiz. Ao atingir o teto, a conversa segue para um humano, com o motivo registrado.

O teto protege contra loops, mas conta tokens, e não custo. Como o juiz é mais caro por token, o teto sozinho não limita o gasto. O custo é acompanhado separadamente para agente e juiz. Ele é um valor inicial, a ajustar nos testes.

### 3.7 Falhas da API da LLM

Erros transitórios, como limite de taxa, timeout e erro 5xx, têm até três tentativas com espera curta e crescente.

Se as tentativas se esgotarem, a conversa segue para um humano. O agente não responde com conteúdo inventado nem troca de modelo sem aviso.

### 3.8 Dados enviados à LLM

Tudo que é enviado à API da Anthropic está mascarado, conforme o RNF-01 do PRD. A chave da API fica no `.env`, nunca no repositório.

### 3.9 APIs externas do projeto

Há três chamadas externas, e nenhuma além delas:

- **API da Anthropic**, para o agente e o juiz.
- **LangSmith**, para traces e avaliações, conforme a [[rfc-0002-integracao-langsmith]].
- **Download do modelo de embeddings**, uma vez por ambiente, conforme a [[rfc-0004-geracao-de-embeddings]].

O serviço de cotação não é externo. Ele roda localmente, no `docker-compose.yml`, e é tratado como dependência interna.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Claude Sonnet 5.5 ou Fable 5.1 para o agente** | Mais capazes, mas mais caros e lentos. Ficam como plano de contingência, caso o Haiku não atenda aos testes. |
| ALT-2 | **Juiz com Fable 5.1** | Julgamento ainda mais forte, mas custo maior. Fica como alternativa se o Opus não atender aos casos de teste do juiz. |
| ALT-3 | **Cotação chamada pela aplicação, fora do modelo** | Tira do modelo a decisão de quando cotar, o que reduz a flexibilidade da conversa. Fica como alternativa se a ferramenta se mostrar instável. |
| ALT-4 | **Alias de versão que acompanha a última** | Compara mal as rodadas de avaliação ao longo do tempo. |
| ALT-5 | **Sem teto de tokens** | Deixa loops e custo sem controle no código. |
| ALT-6 | **Troca automática de modelo quando a API falha** | Muda o comportamento da conversa sem aviso e dificulta a análise dos traces. |
| ALT-7 | **Sem retry** | Transforma qualquer erro transitório em encaminhamento para humano. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Modelo que conduz a conversa | Claude Haiku 5.5, o mais barato da família. |
| QA-2 | Modelo do juiz | Claude Opus 5.5, mais completo e mais caro. |
| QA-3 | Cotação como ferramenta | Sim, ferramenta que o modelo chama, com o valor vindo do resultado oficial. Os argumentos da chamada são preenchidos pela aplicação, a partir do estado. Chamada direta no MVP, sem servidor MCP. |
| QA-4 | Controle de custo | Teto de cerca de 50 mil tokens por conversa. |
| QA-5 | Tratamento de erros da API | Até três tentativas com espera curta. Depois, encaminhamento. |
| QA-6 | Fixação de versão | Identificador exato, fixo. |
| QA-7 | Determinismo | O mais determinístico possível. |

## 6. Premissas assumidas

- O mascaramento acontece antes de qualquer envio à API da Anthropic.
- O teto de tokens conta entradas e saídas de agente e juiz juntos, e não custo.
- O serviço de cotação é interno, mesmo sendo uma API HTTP.
- Trocar a versão do modelo é mudança registrada, com nova rodada de avaliação.

## 7. Impacto e riscos

**Impacto**

- **Código:** o agente expõe a cotação como ferramenta. A aplicação confere que os valores citados existem no resultado oficial.
- **Ambiente:** a chave da API precisa estar no `.env`. Sem ela, o agente não roda.
- **Custo:** o teto de tokens limita o gasto por conversa, mas o total depende do volume de testes.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Haiku perde qualidade em conversas longas | Agente conduz mal a qualificação | Casos de teste de conversas longas no LangSmith. Plano de contingência em ALT-1. |
| Juiz caro eleva o custo por conversa | Gasto acima do esperado | Acompanhar o custo por conversa no LangSmith, separado entre agente e juiz. |
| Teto de tokens corta conversa válida | Encaminhamento indevido | Ajustar o teto pelos testes e registrar o motivo de cada corte. |
| Modelo fixo fica defasado | Desempenho aquém do disponível | Atualização deliberada, com nova rodada de avaliação. |
| Chave da API vazada | Uso indevido da conta | Chave só no `.env`, excluído do git. |

## 8. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: requisitos de preço oficial, falha e privacidade.
- [[rfc-0002-integracao-langsmith]]: avaliação, juiz e regressão.
- [[rfc-0004-geracao-de-embeddings]]: download único do modelo de embeddings.
- [[adr-0015-ferramenta-cotacao-schema-pydantic]]: formato da ferramenta de cotação.
- [[adr-0013-teto-tokens-e-encaminhamento]]: teto de tokens e encaminhamento.
