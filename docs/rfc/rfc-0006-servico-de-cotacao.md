---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0006 — Serviço de cotação (quote-service) rodando localmente

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0001-simulador-de-conversa]] · [[rfc-0005-modelo-llm-e-apis-externas]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define como o serviço de cotação é usado, configurado e consumido localmente. Não é especificação final. Mudanças no serviço, se vierem a ser necessárias, exigem RFC própria.

## 1. Resumo executivo (TL;DR)

O `quote-service` é tratado como caixa-preta nesta fase. Ele roda localmente, no `docker-compose.yml`, na porta 8000, e não é alterado. As regras de preço vêm de `plans.json`, e a cotação é a fonte oficial de todo valor que o agente informa.

Falhas e lentidão são configuradas por variáveis de ambiente do serviço. Mudar essas taxas exige reiniciar o serviço. O agente espera até 5 segundos por cotação. Erros 5xx são retentados, e erros de negócio ou de payload não são.

Como o serviço responde 422 tanto para cotação recusada quanto para payload inválido, o agente distingue os dois pelo corpo da resposta.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige que o agente só informe valores oficiais (RF-05), que trate falhas sem inventar preço (RF-08) e que cubra a recusa por regra (RF-06). Tudo isso depende do comportamento do serviço de cotação.

A [[rfc-0001-simulador-de-conversa]] precisa testar falhas e lentidão, mas não controla o serviço pela tela. Esta RFC define como esse teste acontece pelas variáveis de ambiente.

## 3. Proposta conceitual

### 3.1 Papel do serviço

O serviço expõe três endpoints:

- `GET /health`, para verificar se está no ar;
- `GET /planos`, com a tabela de planos e as regras;
- `POST /quote`, que calcula a cotação dos três planos para um lead.

O agente usa `POST /quote` como ferramenta, conforme a [[rfc-0005-modelo-llm-e-apis-externas]]. No MVP, a chamada é direta, sem servidor MCP, conforme a [[adr-0019-chamada-direta-cotacao-mcp-futuro]].

### 3.2 Configuração local

O serviço sobe com o `docker-compose.yml`, na porta 8000. Ele não tem autenticação, porque só é acessível na máquina local.

### 3.3 Controle de falhas e lentidão

Três variáveis de ambiente controlam o comportamento:

- a fração de chamadas que falham com erro 5xx;
- a fração de chamadas lentas;
- a duração da espera nas chamadas lentas.

Há também uma semente opcional para tornar as falhas reproduzíveis. Com a semente fixa, a sequência de falhas se repete. Como o gerador é compartilhado entre requisições, a repetição só vale com uma requisição por vez.

Para mudar uma dessas configurações, o avaliador edita o `docker-compose.yml` e reinicia o serviço. Essa é a única forma de forçar falha ou lentidão.

### 3.4 Respostas do serviço

| Situação | Código | Corpo | Tratamento do agente |
| --- | --- | --- | --- |
| Cotação calculada | 200 | Três planos, com prêmio, franquia, coberturas, multiplicadores e carência | Apresentar ao lead |
| Falha simulada | 500, 502 ou 503 | `upstream_unavailable` | Retry, conforme a [[rfc-0005-modelo-llm-e-apis-externas]] |
| Cotação recusada por regra | 422 | `cotacao_recusada`, com o motivo | Comunicar o motivo e encaminhar |
| Payload inválido | 400 ou 422 | Erro de validação ou `payload_invalido` | Não retentar. Corrigir o payload |

### 3.5 Distinção entre 422

O FastAPI responde 422 a payloads que não passam na validação, como idade fora da faixa de tipo ou ano inexistente. O serviço também responde 422 quando a regra recusa a cotação.

O agente distingue os dois casos pelo corpo da resposta. Se o campo `error` for `cotacao_recusada`, é recusa por regra. Se a resposta trouxer o formato de validação do FastAPI, é payload inválido. Nenhuma mudança no serviço é feita para isso.

### 3.6 Espera do agente

O agente espera até 5 segundos por chamada de cotação. Esse valor é o timeout do cliente. A cotação completa dos três planos tem prazo total de 15 segundos, conforme o FDD-0002.

Como o modo lento responde em 8 segundos, ele vira timeout. Assim, os testes de lentidão exercitam o retry e o encaminhamento. No modo normal, o serviço não tem espera artificial e responde bem antes do limite.

### 3.7 Retry e encaminhamento

Erros 5xx são retentados, até o limite da [[rfc-0005-modelo-llm-e-apis-externas]]. Erros de recusa e de payload não são retentados, porque repetir a mesma chamada não muda o resultado.

Se as tentativas se esgotarem, a conversa segue para um humano, como exige o RF-08 do PRD. O agente não informa preço.

### 3.8 Data de referência

A idade do veículo é calculada pelo ano atual do sistema. Um mesmo caso de teste pode mudar de resultado com o tempo. Por exemplo, um veículo de 2006 é aceito em 2026, mas é recusado em 2027.

Essa escolha é aceita nesta fase. Os casos de teste que dependem de idade do veículo devem registrar a data em que foram rodados.

### 3.9 Regras de negócio

As regras vêm de `plans.json`, sem alteração. Os planos, as faixas, a região de risco, a carência e o pro-rata são aplicados pelo serviço. O agente não recalcula nenhum valor.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Endpoint de controle de falhas no serviço** | Altera o serviço, que fica como caixa-preta. A tela de controle, que dependia dele, foi retirada. |
| ALT-2 | **Mudar o serviço para responder 400 na validação** | Quebraria a decisão de usar o serviço como está. A distinção pelo corpo resolve o problema sem mudança. |
| ALT-3 | **Timeout de 15 segundos** | Permitiria o modo lento responder, sem exercitar o timeout. Foi descartado pelo usuário, que escolheu 5 segundos. |
| ALT-4 | **Timeout de 10 segundos** | Também permitiria o modo lento responder, sem exercitar o timeout. Foi descartado pelo usuário. |
| ALT-5 | **Ano de referência fixo para a idade do veículo** | Torna os testes repetíveis ao longo do tempo. Foi descartado pelo usuário, que escolheu o ano atual. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | O serviço é alterado nesta fase? | Não. Usado como está. |
| QA-2 | Como a falha é forçada | Variáveis de ambiente, com reinício. |
| QA-3 | Ano da idade do veículo | Ano atual. |
| QA-4 | Timeout do agente | 5 segundos. |
| QA-5 | Distinção dos 422 | Pelo corpo da resposta. |

## 6. Premissas assumidas

- O serviço não tem autenticação, porque só é acessível localmente.
- Os logs do serviço ficam no console do contêiner. Nenhum log é enviado ao LangSmith pelo serviço.
- A taxa de falha vale para o serviço inteiro, e não para uma cotação específica.

## 7. Impacto e riscos

**Impacto**

- **Código:** nenhum código do serviço muda. O agente implementa a distinção de 422 e o timeout de 15 segundos.
- **Ambiente:** testar falha ou lentidão exige editar o `docker-compose.yml` e reiniciar o serviço.
- **Testes:** casos que dependem de idade do veículo precisam registrar a data de execução.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Reinício para trocar a falha atrapalha a demonstração | A demo perde fluidez | Trocar as configurações antes da demo, e não durante. |
| Distinção de 422 pelo corpo falha em um caso não previsto | Recusa tratada como erro, ou o contrário | Casos de teste para cada tipo de 422, avaliados no LangSmith. |
| Veículo muda de faixa com o tempo | Um mesmo caso passa a ser recusado | Registrar a data de execução e revisar os casos periodicamente. |
| Semente fixa com várias requisições simultâneas | Falhas não se repetem de forma previsível | Testes sequenciais, uma requisição por vez. |
| Imagem Docker instala dependências por pip, sem o `uv.lock` | Versões podem divergir do lock do projeto | Registrar na implementação a origem das dependências do contêiner. |
| Modo lento bloqueia uma thread do servidor | Lentidão afeta outras requisições em paralelo | Testes sequenciais, uma requisição por vez. |
| Lentidão real acima de 5 segundos vira falha | Encaminhamento desnecessário | Acompanhar a taxa de timeouts nos traces do LangSmith. |

## 8. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: regras de preço oficial, falha e recusa.
- [[rfc-0001-simulador-de-conversa]]: controle de falha retirado da tela, e configurado pelo serviço.
- [[rfc-0005-modelo-llm-e-apis-externas]]: retry e uso da cotação como ferramenta.
- Versionamento do contrato do serviço: só será criado se o contrato mudar.
