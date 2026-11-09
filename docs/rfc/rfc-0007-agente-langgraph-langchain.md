---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0007 — Agente com LangGraph e LangChain

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0002-integracao-langsmith]] · [[rfc-0003-banco-postgres-pgvector]] · [[rfc-0004-geracao-de-embeddings]] · [[rfc-0005-modelo-llm-e-apis-externas]] · [[rfc-0006-servico-de-cotacao]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define a organização conceitual do agente: etapas, estado e papel de cada framework. Não é especificação final. Formato exato do estado, prompts e contratos de ferramenta ficam para RFCs e ADRs próprios.

## 1. Resumo executivo (TL;DR)

O agente é um grafo com etapas fixas, orquestrado pelo LangGraph. As etapas são: entrada, coleta, cotação, juiz e resposta. O LangChain fornece os componentes que cada etapa usa: o cliente do modelo Claude, a ferramenta de cotação e o recuperador de regras sobre o pgvector.

O modelo do agente é o Claude Haiku 5.5, e o juiz é o Claude Opus 5.5. O juiz verifica, antes do envio, cada resposta que cita valor ou recusa. Se reprovar, o agente reescreve uma vez, e depois encaminha.

O estado da conversa é gravado no Postgres a cada etapa. Os dados coletados ficam num estado estruturado, e não apenas no resumo do histórico.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige que o agente conduza a qualificação, cote pelos três planos, encaminhe nos gatilhos definidos e nunca informe um valor que não venha da cotação oficial. Essas exigências pedem um fluxo previsível, que possa ser testado e auditado.

A [[rfc-0005-modelo-llm-e-apis-externas]] define os modelos e a forma de chamar a cotação como ferramenta. A [[rfc-0002-integracao-langsmith]] define a avaliação. Esta RFC organiza essas partes num só agente.

## 3. Proposta conceitual

### 3.1 Papel de cada framework

- **LangGraph** orquestra o agente. Ele define as etapas, a ordem entre elas, as transições condicionais e o estado que atravessa o fluxo.
- **LangChain** fornece os componentes usados dentro das etapas: a integração com o modelo Claude, a ferramenta de cotação e o recuperador de regras sobre o índice vetorial da [[rfc-0003-banco-postgres-pgvector]].

A aplicação controla o fluxo. O modelo conduz a conversa dentro de cada etapa, mas não decide qual etapa vem depois.

### 3.2 Etapas do grafo

| Etapa | O que faz | Quem decide |
| --- | --- | --- |
| **Entrada** | Mascara dados pessoais da mensagem, com regras determinísticas, antes de qualquer chamada ao modelo | Código, sem modelo |
| **Coleta** | Conduz a conversa para obter idade, ano do veículo, CEP e data de início. Depois da cotação, pede o CPF quando o lead escolhe um plano | Modelo Haiku, dentro de regras da aplicação |
| **Cotação** | Chama a ferramenta de cotação com os dados coletados | Modelo, via ferramenta. A aplicação preenche os argumentos a partir do estado |
| **Juiz** | Verifica, antes do envio, as respostas que citam valor ou recusa, conforme o RF-05 e as regras do PRD | Modelo Opus, com resposta binária e motivo |
| **Resposta** | Envia a resposta ao lead, ou reescreve uma vez se o juiz reprovar | Código, conforme o resultado do juiz |
| **Encaminhamento** | Marca a conversa como encaminhada, com o motivo, e encerra as respostas do agente | Código |
| **Encerramento** | Finaliza a conversa com status cotada ou encerrada | Código |

### 3.3 Fluxo da cotação

A cotação acontece depois que os dados mínimos estão completos. O agente chama a ferramenta uma vez para cada um dos três planos. Os argumentos da chamada, inclusive o CEP, são preenchidos pela aplicação a partir do estado. O modelo decide quando chamar, mas não escreve esses dados. No MVP, a chamada é direta à API da cotação, sem servidor MCP, conforme a [[adr-0019-chamada-direta-cotacao-mcp-futuro]].

Os valores da resposta vêm exclusivamente do resultado da ferramenta. Se a ferramenta falhar com erro 5xx, o agente tenta de novo, até o limite da [[rfc-0005-modelo-llm-e-apis-externas]]. Se recusar por regra, o agente comunica o motivo e encaminha. Se as tentativas se esgotarem, encaminha sem informar preço, conforme o [[rfc-0006-servico-de-cotacao]].

### 3.4 Juiz e reescrita

Cada resposta com valor passa pelo juiz antes do envio. O juiz verifica se os valores citados existem no resultado oficial e se a resposta respeita as regras do PRD.

- Se aprovar, a resposta segue para o lead.
- Se reprovar, o agente reescreve uma vez, com o motivo da reprovação.
- Se o juiz reprovar de novo, a conversa é encaminhada para um humano.

O juiz é o último filtro, e não substitui a regra de que o valor vem da cotação.

### 3.5 Estado do grafo

O estado da conversa guarda, conceitualmente:

- os dados coletados, em formato estruturado;
- as cotações recebidas, quando existirem;
- o histórico de mensagens, ou o resumo acumulado;
- o status da conversa;
- o motivo do encaminhamento, quando houver;
- o identificador do trace, para a [[rfc-0002-integracao-langsmith]].

### 3.6 Histórico e resumo

Enquanto a conversa é curta, o histórico vai inteiro ao modelo. Acima de cerca de 20 mil tokens, as mensagens mais antigas são substituídas por um resumo acumulado.

O resumo nunca é a fonte dos dados da cotação. Idade, ano, CEP, data de início e CPF ficam no estado estruturado. Assim, um resumo impreciso não altera o valor cotado.

### 3.7 Teto de tokens

Ao atingir o teto de cerca de 50 mil tokens, a conversa é encaminhada para um humano, com o motivo registrado, conforme a [[rfc-0005-modelo-llm-e-apis-externas]].

### 3.8 Persistência e retomada

O LangGraph grava o estado no Postgres a cada etapa, em área própria do banco. Isso permite retomar uma conversa interrompida e auditar cada passo.

A persistência do estado é separada do registro de conversas da [[rfc-0003-banco-postgres-pgvector]]. O registro guarda o histórico para o avaliador. O estado guarda o que o agente precisa para continuar.

### 3.9 Dados pessoais

O mascaramento da etapa de entrada é determinístico, por regras em código. O modelo nunca recebe a mensagem original. O mesmo critério vale para o que é enviado aos traces, conforme a [[rfc-0002-integracao-langsmith]].

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Fluxo livre, guiado pelo modelo** | Mais flexível, mas menos previsível para testar e auditar. Os gatilhos de encaminhamento ficariam dependentes da decisão do modelo. |
| ALT-2 | **Juiz encaminha direto, sem reescrever** | Mais seguro, mas aumenta encaminhamentos por falhas pequenas de redação. Foi descartado pelo usuário, que preferiu uma reescrita. |
| ALT-3 | **Envio com aviso, mesmo quando o juiz reprova** | Viola o RF-05 do PRD, que exige que só valores oficiais cheguem ao lead. Foi descartado pelo usuário. |
| ALT-4 | **Sem checkpoint no Postgres** | Impede retomar conversas e auditar cada etapa. Foi descartado pelo usuário. |
| ALT-5 | **Histórico completo sem resumo** | Simples e fiel, mas o custo cresce com a conversa. Foi descartado pelo usuário, que escolheu resumo acumulado acima de 20 mil tokens. |
| ALT-6 | **Só LangChain, sem LangGraph** | Reverte a decisão de orquestração. O fluxo ficaria menos explícito. Foi descartado pelo usuário. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Papel do LangChain | Componentes, com o LangGraph na orquestração. |
| QA-2 | Organização do fluxo | Etapas fixas: entrada, coleta, cotação, juiz, resposta. |
| QA-3 | Reprova do juiz | Reescreve uma vez, depois encaminha. |
| QA-4 | Persistência do estado | Checkpoint no Postgres, com retomada. |
| QA-5 | Histórico enviado ao modelo | Resumo acumulado. |
| QA-6 | Limiar do resumo | Acima de cerca de 20 mil tokens. |

## 6. Premissas assumidas

- O mascaramento da entrada é a única etapa que trata o texto bruto. As demais recebem o texto já mascarado.
- A reescrita do juiz não chama a ferramenta de cotação de novo. Ela reaproveita o resultado já recebido.
- Os nomes das etapas são conceituais e podem mudar na implementação, sem mudar o fluxo.

## 7. Impacto e riscos

**Impacto**

- **Código:** surge o grafo com as etapas, o estado estruturado e a integração com o LangChain.
- **Banco:** o checkpoint ocupa área própria no Postgres local.
- **Testes:** cada etapa pode ser testada isoladamente, e o fluxo completo é avaliado no LangSmith.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Resumo perde um detalhe relevante | Agente conduz mal a conversa | Dados da cotação ficam no estado estruturado, fora do resumo. Casos de teste de conversas longas. |
| Juiz reprova respostas válidas | Encaminhamentos desnecessários | Casos de teste que o juiz precisa aprovar, além dos que precisa reprovar. |
| Mascaramento falha antes do modelo | Dado pessoal chega ao modelo | Mascaramento determinístico na entrada, com redaction nos traces, conforme a [[rfc-0002-integracao-langsmith]]. |
| Checkpoint cresce sem limite | Banco local lento | Retenção definida na implementação, sem limpeza automática nesta fase. |
| Versões do LangGraph e do LangChain mudam | Comportamento muda sem aviso | Versões fixadas no projeto, registradas em ADR. |
| Custo do juiz por resposta | Gasto maior por conversa | Acompanhar o custo por etapa no LangSmith. |

## 8. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: requisitos de preço oficial, encaminhamento e privacidade.
- [[rfc-0005-modelo-llm-e-apis-externas]]: modelos, ferramenta de cotação, retry e teto de tokens.
- [[rfc-0006-servico-de-cotacao]]: contrato da cotação e distinção de 422.
- [[rfc-0002-integracao-langsmith]]: traces, avaliação e regressão.
- [[adr-0001-python-e-gerenciador]]: versões fixadas de LangGraph e LangChain, pelo lock.
- [[adr-0006-estado-do-grafo-pydantic]]: formato do estado do grafo.
