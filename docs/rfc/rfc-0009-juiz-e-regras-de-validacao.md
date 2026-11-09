---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0009 — Juiz e regras de validação das respostas

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0002-integracao-langsmith]] · [[rfc-0005-modelo-llm-e-apis-externas]] · [[rfc-0007-agente-langgraph-langchain]] · [[rfc-0008-mascaramento-de-dados-pessoais]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define quais regras o juiz verifica, o formato da decisão e o comportamento em caso de falha. Não é especificação final. O texto das instruções ao modelo e o conjunto de casos de teste do juiz ficam para a RFC-0011 e a implementação.

## 1. Resumo executivo (TL;DR)

O juiz é um modelo, o Claude Opus 5.5, que verifica cada resposta do agente que cita valor ou recusa, antes do envio ao lead. Ele aplica quatro regras:

1. todo valor citado existe no resultado oficial da cotação;
2. recusa e encaminhamento são coerentes com o estado da cotação;
3. a resposta não promete venda, boleto, apólice ou emissão;
4. a resposta não contém dado pessoal sem máscara.

A decisão é binária, aprovado ou reprovado, com um motivo curto e o código da regra violada. Se reprovar, o agente reescreve uma vez. Se reprovar de novo, ou se o próprio juiz falhar, a conversa segue para um humano. Nenhuma resposta reprovada chega ao lead.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige que o agente só informe valores vindos da cotação oficial (RF-05), que nunca invente preço quando a cotação falha (RF-08) e que não apresente dado pessoal sem máscara (RNF-01). O juiz é a última verificação dessas exigências antes do lead.

A [[rfc-0007-agente-langgraph-langchain]] define a etapa do juiz no fluxo, com a reescrita e o encaminhamento. A [[rfc-0005-modelo-llm-e-apis-externas]] define o modelo e o tratamento de erros. Esta RFC define o que o juiz verifica e como decide.

## 3. Proposta conceitual

### 3.1 Respostas avaliadas

O juiz avalia apenas as respostas que citam um valor ou uma recusa: preço, franquia, cobertura, motivo de recusa ou falha da cotação. Respostas que só pedem dados ao lead, ou que apenas confirmam o recebimento, não passam pelo juiz.

Essa escolha reduz o custo do modelo mais caro, sem deixar de cobrir a parte sensível da conversa.

### 3.2 Regra R1: valores oficiais

Todo preço, franquia, cobertura e multiplicador citado na resposta existe no resultado da ferramenta de cotação, no plano correto.

Esta verificação é feita em código, comparando os valores da resposta com o resultado oficial, inclusive a associação entre um valor e o plano citado na mesma frase. O modelo não participa dessa verificação.

### 3.3 Regra R2: recusa e encaminhamento coerentes

Se a cotação foi recusada por regra, a resposta comunica o motivo e não apresenta preço. Se a cotação falhou de forma persistente, a resposta informa que a cotação não está disponível e não apresenta preço. Nos dois casos, a conversa precisa estar marcada para encaminhamento.

Se a resposta diz que a conversa foi encaminhada, o estado precisa refletir isso.

### 3.4 Regra R3: sem promessa de venda

A resposta não promete apólice, boleto, contratação, emissão ou ativação de cobertura. O agente pode dizer que um vendedor dará seguimento, porque o MVP só cota e encaminha, conforme o PRD.

### 3.5 Regra R4: sem dado pessoal sem máscara

A resposta não contém CPF, e-mail, telefone, placa ou CEP em texto, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]]. Marcadores como `[CPF]` são aceitos.

O juiz recebe a resposta já mascarada. Esta regra é uma segunda verificação, depois da varredura da saída.

### 3.6 Formato da decisão

A decisão é binária, aprovado ou reprovado, com:

- o motivo, em texto curto;
- o código da regra violada, quando reprovado.

A decisão é registrada no trace da [[rfc-0002-integracao-langsmith]], como feedback. Assim, reprovações podem ser analisadas depois, em avaliação.

### 3.7 Fluxo de decisão

1. A resposta candidata chega ao juiz, com o resultado da cotação e o status da conversa.
2. Se aprovada, segue para o lead.
3. Se reprovada, o agente reescreve uma vez, com o motivo.
4. A reescrita passa de novo pelo juiz.
5. Se reprovar de novo, a conversa é encaminhada para um humano, com o motivo registrado.

### 3.8 Falha do juiz

Se a chamada ao juiz falhar, a regra da [[rfc-0005-modelo-llm-e-apis-externas]] se aplica: até três tentativas. Se todas falharem, a resposta não é enviada, e a conversa é encaminhada.

Essa é uma falha fechada. O juiz falhar nunca libera uma resposta sem verificação.

### 3.9 Dados enviados ao juiz

O juiz recebe a resposta candidata, o resultado da cotação, o status e o motivo de encaminhamento, quando houver. Ele não recebe CPF, CEP, e-mail, telefone nem placa, porque o texto chega mascarado e os valores da cotação não são dados pessoais.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Nota de 0 a 5 por critério** | Mais detalhe, mas menos direto para virar decisão no fluxo. Foi descartada pelo usuário, que escolheu aprovado ou reprovado. |
| ALT-2 | **Juiz avalia todas as respostas** | Mais seguro, mas com custo maior por conversa. Foi descartada pelo usuário, que escolheu avaliar só respostas com valor ou recusa. |
| ALT-3 | **Juiz encaminha direto, sem reescrita** | Foi descartada na RFC-0007. A reescrita corrige falhas pequenas de redação sem encaminhar. |
| ALT-4 | **Juiz avalia tudo por modelo, sem verificação em código** | Mais flexível, mas menos confiável para R1. Os valores são comparados em código sempre que possível. |
| ALT-5 | **Liberar a resposta quando o juiz falha** | Viola o RF-05. Foi descartada: a falha do juiz fecha o fluxo. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Regras verificadas | Valores oficiais, recusa e encaminhamento coerentes, sem promessa de venda, sem dado pessoal na saída. |
| QA-2 | Formato da decisão | Aprovado ou reprovado, com motivo. |
| QA-3 | Respostas avaliadas | Só as que citam valor ou recusa. |

## 6. Premissas assumidas

- A verificação de valores (R1) é feita em código sempre que possível. Isso segue o princípio de determinismo definido para o projeto.
- O juiz é o mesmo modelo para todas as regras, com instruções específicas por regra.
- Uma reprovação de R4 que apareça depois da varredura da saída indica falha da varredura, e deve ser registrada como evento para análise.
- A reescrita não recebe o resultado da cotação de novo. Ela reaproveita o resultado já obtido.

## 7. Impacto e riscos

**Impacto**

- **Código:** surge uma verificação de valores em código, comparando a resposta com o resultado oficial.
- **Custo:** o juiz roda só em respostas com valor ou recusa, o que limita o gasto do modelo mais caro.
- **Fluxo:** a conversa pode ser encaminhada por falha do juiz, o que aumenta o volume de encaminhamentos em um dia ruim da API.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Juiz reprova resposta válida | Reescrita ou encaminhamento desnecessário | Casos de teste de respostas válidas que o juiz precisa aprovar, na RFC-0011. |
| Juiz aprova resposta inválida | Valor ou promessa indevida chega ao lead | Verificação de R1 em código, e casos de teste de respostas inválidas. |
| Falha da API do juiz | Aumento de encaminhamentos | Retry de até três tentativas, e acompanhamento da taxa de falha nos traces. |
| Verificação de valores falha com formatação diferente | Valor correto é reprovado | Normalização de formato antes da comparação, com testes. |
| Custo do juiz cresce com o volume | Gasto acima do esperado | Escopo limitado às respostas com valor ou recusa, e custo acompanhado por etapa. |

## 8. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: RF-05, RF-08 e RNF-01.
- [[rfc-0002-integracao-langsmith]]: registro da decisão como feedback no trace.
- [[rfc-0005-modelo-llm-e-apis-externas]]: modelo do juiz e tratamento de falhas.
- [[rfc-0007-agente-langgraph-langchain]]: etapa do juiz e reescrita.
- [[rfc-0008-mascaramento-de-dados-pessoais]]: varredura de saída e regra R4.
- [[rfc-0011-avaliacao-e-testes]]: casos de teste do juiz.
