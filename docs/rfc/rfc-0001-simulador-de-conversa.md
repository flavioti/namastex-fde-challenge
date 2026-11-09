---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0001 — Simulador de conversa (interface Streamlit que imita o WhatsApp)

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define requisitos conceituais do simulador. Não é especificação final. Algumas decisões vão mudar com as RFCs seguintes, e a implementação ainda não começou.

## 1. Resumo executivo (TL;DR)

Propomos uma aplicação Streamlit, em `ui-app/`, que simula uma conversa de WhatsApp entre um lead fictício e o agente de cotação. A tela tem três áreas: uma lista de conversas, o chat e um painel lateral com o estado da conversa. Também tem uma aba para o vendedor, somente leitura, com as conversas encaminhadas.

O simulador não contém a lógica do agente. Ele envia mensagens do lead, mostra as respostas e guarda o histórico. Tudo roda localmente, com um banco local para as conversas.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige uma demonstração de ponta a ponta, sem canal real. O avaliador precisa conversar com o agente, ver o que foi coletado e cotado, e conferir quando e por que a conversa foi encaminhada. Também precisa testar o comportamento do agente quando a cotação falha ou demora.

Sem uma interface dedicada, essa verificação depende de chamadas manuais à API e de leitura de logs. Isso é lento e pouco fiel à experiência do lead.

## 3. Proposta conceitual

### 3.1 Visão geral

A aplicação tem três áreas de uso:

- **Conversas (lista).** Mostra as conversas guardadas, com status, e permite iniciar um lead novo.
- **Chat.** Mostra as mensagens do lead e do agente, e aceita texto do lead.
- **Painel lateral.** Mostra o estado da conversa: dados coletados, cotações recebidas, status e, quando houver, o motivo do encaminhamento.
- **Vendedor.** Uma aba de encaminhados, somente leitura, para o vendedor.

A interface não decide nada sobre preço, elegibilidade ou encaminhamento. Essas decisões são do agente. A interface só mostra o que o agente informa.

### 3.2 Componentes conceituais

1. **Lista de conversas.** Cada conversa tem identificador, nome fictício do lead, data de início e status (em andamento, cotada, encaminhada ou encerrada). O avaliador pode abrir uma conversa existente ou criar um lead novo.
2. **Chat.** Exibe as mensagens em ordem, com indicação de que o agente está processando. Aceita apenas texto. Após o encaminhamento, o campo de texto fica desativado, com um aviso de que a conversa foi encaminhada.
3. **Painel lateral.** Mostra, em leitura, os dados coletados, as cotações dos três planos quando existirem, o status atual e o motivo do encaminhamento.
4. **Aba de encaminhados.** Lista as conversas encaminhadas, com motivo e resumo para o vendedor. Mostra o CPF sem máscara, quando houver, conforme o [[prd-0001-agente-de-cotacao]]. A aba é somente leitura: o vendedor não responde pela simulação.
5. **Persistência.** Conversas e mensagens ficam guardadas no banco local, para que possam ser reabertas e auditadas. O modelo de dados e a escolha da tabela são técnicos e ficam para uma RFC própria.
6. **Respondedor de teste.** Enquanto o agente não existe, a simulação usa um respondedor fixo, sem modelo de linguagem, só para validar a tela e os estados. Ele responde com informações básicas sobre a AutoSeguro, informando que é uma empresa de seguros. É descartável e será substituído pelo agente.

### 3.3 Fluxo conceitual de uma mensagem

1. O avaliador escreve uma mensagem do lead e a envia.
2. A mensagem é guardada na conversa e a tela mostra que o agente está processando.
3. O agente devolve uma resposta, que é mostrada no chat e guardada.
4. Se o agente informar um encaminhamento, a conversa muda de status, o painel lateral mostra o motivo e o campo de texto é desativado.
5. A conversa encaminhada aparece na aba de encaminhados.

### 3.4 Dados exibidos e privacidade

- O lead é criado com nome e telefone fictícios, gerados aleatoriamente pela simulação.
- O telefone e o CPF aparecem sem máscara só onde o PRD permite: no chat do próprio lead e na aba de encaminhados. Logs e traces guardam esses dados mascarados.
- A simulação não guarda dados reais. Mesmo assim, trata os dados como sensíveis, para manter o processo próximo do produtivo.

### 3.5 Estados da conversa

| Estado | Quando ocorre | O que o avaliador vê |
| --- | --- | --- |
| Em andamento | A conversa está aberta e o agente ainda não cotou nem encaminhou | Chat ativo |
| Cotada | O agente apresentou as cotações dos três planos | Painel com as cotações |
| Encaminhada | O agente informou um encaminhamento | Chat bloqueado, motivo no painel, conversa na aba de encaminhados |
| Encerrada | O lead desiste, ou não responde por 30 minutos, sem cotação nem encaminhamento | Chat somente leitura. Nos testes iniciais, não pode ser reaberta. |

### 3.6 Fronteira com o agente

A simulação conversa com o agente por uma fronteira simples: envia a mensagem do lead e recebe a resposta, o estado e, quando houver, o encaminhamento. O formato exato dessa troca e o tratamento de falhas técnicas são definidos em RFC própria. Esta RFC só exige que a fronteira exista e que a interface não dependa de detalhes internos do agente.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Só o chat, sem painel lateral** | Obriga o avaliador a procurar o estado dentro das mensagens. O painel custa pouco e torna a análise mais rápida. |
| ALT-2 | **Conversa em memória da sessão** | Some ao recarregar a página e impede auditar conversas antigas, o que o PRD exige. |
| ALT-3 | **Uma conversa por vez, sem lista** | Dificulta comparar casos e revisar o que aconteceu antes. |
| ALT-4 | **Canal real de WhatsApp** | Exige conta e integração externa, fora do escopo do MVP. |
| ALT-5 | **Controle de falhas na tela, com endpoint de teste no serviço de cotação** | Altera o serviço, que fica como caixa-preta nesta fase. Foi descartado: a falha passa a ser configurada pelas variáveis de ambiente do serviço, com reinício. |
| ALT-6 | **Interface em linha de comando** | Menos legível para o avaliador, que precisa ver o estado ao mesmo tempo que a conversa. |
| ALT-7 | **Vendedor respondendo no chat** | Amplia o escopo para um segundo papel na conversa. O MVP só precisa mostrar o encaminhamento. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | O controle de falha vale só para a próxima cotação ou para a conversa inteira? | Superada. O controle na tela saiu do escopo. A falha é configurada pelas variáveis de ambiente do serviço de cotação, conforme a [[rfc-0006-servico-de-cotacao]]. |
| QA-2 | Nome e telefone fictícios são gerados aleatoriamente ou seguem uma lista fixa? | Gerados aleatoriamente. |
| QA-3 | Qual é o comportamento mínimo do respondedor de teste? | Responde com informações básicas sobre a AutoSeguro, informando que é uma empresa de seguros. |
| QA-4 | O avaliador pode reabrir uma conversa já encerrada? | Não, nos testes iniciais. |

## 6. Impacto e riscos

**Impacto**

- **Código:** surge uma nova pasta `ui-app/`, com a aplicação Streamlit.
- **Banco:** conversas e mensagens passam a ser guardadas no banco local, o que exige um serviço de banco no ambiente local.
- **Operação:** o avaliador sobe a aplicação e o banco localmente, sem serviços externos além do modelo de linguagem.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| A simulação se afasta do WhatsApp real | A experiência do lead fica diferente da real | Manter o texto simples e os estados explícitos. Aceitar a diferença, já que o canal real está fora de escopo. |
| CPF exibido na aba de encaminhados | Dado sensível visível na tela | Restringir a exibição à aba de encaminhados, conforme o PRD. Nunca mostrar fora dela. |
| Respondedor de teste fica mais tempo que o necessário | Testes passam sem validar o agente de verdade | Marcar o respondedor como descartável e removê-lo quando o agente estiver pronto. |
| Mudança na fronteira com o agente | A interface precisa ser refeita | Manter a fronteira simples e documentada, e tratá-la em RFC própria. |

## 7. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: requisitos de produto que esta RFC implementa conceitualmente.
- [[adr-0018-mensagens-em-tabela-propria]]: persistência das conversas.
- [[rfc-0010-contrato-interface-agente]]: contrato entre a interface e o agente.
