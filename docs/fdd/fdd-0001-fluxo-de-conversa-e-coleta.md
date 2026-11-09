---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0001 — Fluxo de conversa e regras de coleta

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0001-simulador-de-conversa]] · [[rfc-0006-servico-de-cotacao]] · [[rfc-0007-agente-langgraph-langchain]] · [[rfc-0008-mascaramento-de-dados-pessoais]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Este FDD descreve o comportamento funcional da conversa: a ordem de coleta, as regras de cada campo, as tentativas e os gatilhos de encaminhamento. Ele não define componentes técnicos, que ficam nas RFCs.

## 1. Resumo

O agente coleta quatro dados, nesta ordem fixa: idade, ano do veículo, CEP e data de início da vigência. Com esses dados, cota os três planos. Depois que o lead escolhe um plano, pede o CPF, com consentimento.

Cada dado tem uma regra de formato. Um dado inválido é pedido de novo, até duas vezes. Se a terceira resposta também for inválida, a conversa é encaminhada para um humano.

As mensagens seguem um roteiro fixo por etapa. O modelo adapta o tom, mas não muda o dado pedido.

## 2. Ordem de coleta

| Ordem | Dado | Obrigatório para cotar | Fonte da regra de negócio |
| --- | --- | --- | --- |
| 1 | Idade | Sim | Faixa etária, decidida pela cotação |
| 2 | Ano do veículo | Sim | Idade do veículo, decidida pela cotação |
| 3 | CEP | Sim | Região de risco, decidida pela cotação |
| 4 | Data de início | Sim | Pro-rata, decidido pela cotação |

O CPF não entra na cotação. Ele é pedido depois que o lead escolhe um plano, conforme a seção 4.

## 3. Regras de cada campo

### 3.1 Idade

- Aceita apenas número inteiro, entre 1 e 120.
- Valor fora desse formato é dado inválido, e entra na regra de tentativas.
- A faixa aceita pela cotação (18 a 75 anos) não é checada pelo agente. Se a idade estiver fora dela, a cotação recusa, e o agente comunica o motivo.

### 3.2 Ano do veículo

- Aceita apenas número inteiro de quatro dígitos, entre 1950 e o ano atual.
- A idade do veículo é decidida pela cotação. Veículo com mais de 20 anos é recusado.

### 3.3 CEP

- Aceita oito dígitos, com ou sem hífen.
- O CEP é guardado no estado com o valor original. O modelo só vê o marcador, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]].
- A região de risco é decidida pela cotação.

### 3.4 Data de início

- Obrigatória. O agente não cota sem ela.
- Aceita data no formato dia, mês e ano.
- Só aceita datas a partir de hoje. Data anterior a hoje é dado inválido, com pedido de nova data.
- Se a data for o dia 1 do mês, a cotação é integral. Se não for, a cotação mostra o pro-rata do primeiro pagamento.

### 3.5 CPF

- Aceita onze dígitos, com ou sem pontuação.
- Não há validação do dígito verificador, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]].
- O CPF só é pedido depois que o lead escolhe um plano, e depois do consentimento.

## 4. Tentativas

Um dado inválido recebe uma explicação curta e um novo pedido. Essa regra vale para qualquer campo.

- Após a primeira resposta inválida, o agente pede de novo, até duas vezes.
- Se a terceira resposta também for inválida, a conversa é encaminhada para um humano, com o motivo "dado inválido após tentativas".

O contador de tentativas é por campo, e não por conversa. Quando um campo válido é recebido, o contador daquele campo volta a zero.

## 5. Mensagens

Cada etapa tem um roteiro fixo, com três partes:

- o dado pedido;
- o formato esperado, com um exemplo;
- o que fazer se o dado vier inválido.

O modelo escreve a mensagem a partir do roteiro, adaptando o tom à conversa. Ele não pode mudar o dado pedido nem o formato esperado.

## 6. Escolha do plano e CPF

Depois da cotação, o agente apresenta os três planos, com prêmio mensal, franquia e coberturas. Ele pergunta ao lead qual plano quer.

Quando o lead escolhe um plano, o agente explica a finalidade do CPF, que é entregá-lo ao vendedor, e pede o consentimento. Se o lead autorizar, o agente pede o CPF. Se recusar, a conversa é encaminhada sem o CPF, e a cotação continua registrada.

Se o lead não escolher um plano, o agente não pede o CPF.

## 7. Encaminhamento

A conversa é encaminhada para um humano nos seguintes casos:

| Gatilho | Motivo registrado |
| --- | --- |
| Cotação recusada por regra | Cotação recusada, com o motivo da regra |
| Cotação falha de forma persistente | Cotação indisponível |
| Pedido do lead para falar com humano | Pedido do lead |
| Consentimento do CPF recusado | CPF não autorizado |
| Dado inválido após tentativas | Dado inválido após tentativas |
| Teto de tokens atingido | Limite da conversa atingido |

Ao encaminhar, o agente avisa o lead em uma mensagem do roteiro, e não responde mais. Esse comportamento segue a [[rfc-0001-simulador-de-conversa]].

## 8. Status da conversa

| Status | Quando |
| --- | --- |
| Em andamento | Conversa aberta, sem cotação e sem encaminhamento |
| Cotada | Os três planos foram apresentados ao lead |
| Encaminhada | Algum gatilho da seção 7 foi acionado |
| Encerrada | O lead desiste, ou não responde por 30 minutos, sem cotação nem encaminhamento |

## 9. Critérios de aceitação funcionais

1. **Ordem fixa.** Dado um lead novo, o agente pergunta idade, ano, CEP e data de início, nessa ordem.
2. **Dado inválido.** Dado um ano de 1800, o agente pede o ano de novo, sem cotar.
3. **Tentativas esgotadas.** Dado que o lead informa três datas passadas seguidas, a conversa é encaminhada com o motivo de dado inválido.
4. **Data no dia 1.** Dada a data 1º do mês, a cotação não mostra pro-rata.
5. **Data no meio do mês.** Dada uma data no dia 15, a cotação mostra o pro-rata do primeiro pagamento.
6. **CPF após a escolha.** Dado que o lead ainda não escolheu um plano, o agente não pede o CPF.
7. **Recusa do CPF.** Dado que o lead recusa o consentimento, a conversa é encaminhada, e a cotação continua registrada.

## 10. Condição de encerramento

A conversa passa para encerrada quando o lead diz que não quer mais, ou quando passam 30 minutos sem resposta do lead, sem cotação nem encaminhamento.

## 11. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: requisitos de coleta, cotação e encaminhamento.
- [[rfc-0001-simulador-de-conversa]]: campo desativado após o encaminhamento.
- [[rfc-0006-servico-de-cotacao]]: faixas, regras de cotação e erros do serviço.
- [[rfc-0007-agente-langgraph-langchain]]: etapas do grafo e teto de tokens.
- [[rfc-0008-mascaramento-de-dados-pessoais]]: tratamento do CEP e do CPF.
