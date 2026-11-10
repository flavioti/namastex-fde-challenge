---
tipo: prd
status: aprovado
data: 2026-11-09
---

# PRD — Agente de cotação de seguro auto (MVP)

| Campo | Valor |
| --- | --- |
| **Product Manager** | João |
| **Tech Lead** | Paulo |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Tipo de entrega** | MVP de demonstração, com interface simulada |
| **Documentos relacionados** | [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Este é um MVP.** Serve para demonstrar o fluxo de ponta a ponta, sem canal real e sem fechar venda. Decisões técnicas ficam para as RFCs e os ADRs.

## 1. Resumo e contexto

A AutoSeguro vende seguro de veículo e atende leads pelo WhatsApp. Hoje o vendedor conduz a qualificação e a cotação de cada lead. O MVP entrega um agente que conversa com o lead, coleta os dados necessários, apresenta as cotações dos três planos e encaminha a conversa a um vendedor nos casos definidos.

O agente nunca informa um preço que não tenha vindo da cotação oficial. Quando a cotação não está disponível, o agente diz isso ao lead e passa a conversa a um humano.

## 2. Problema e motivação

- **Qualificação manual.** O vendedor gasta tempo perguntando os mesmos dados de todo lead antes de cotar.
- **Risco de preço errado.** Uma resposta que inventa preço ou cobertura gera expectativa falsa e retrabalho.
- **Falta de critério de encaminhamento.** Não há regra clara sobre quando a conversa deve ir para um humano.

O MVP testa se um agente consegue resolver a parte repetitiva da conversa e reconhecer quando precisa de um vendedor.

## 3. Público-alvo e cenários de uso

**Personas**

| Persona | Quem é | O que precisa |
| --- | --- | --- |
| **Lead** | Pessoa que quer segurar o carro e conversa com o agente. Na demo, usa a interface simulada. | Receber uma cotação clara, entender os planos e ser encaminhada quando precisar de ajuda. |
| **Vendedor** | Recebe a conversa encaminhada. | Ver de imediato o motivo do encaminhamento e um resumo da conversa, com os dados coletados. |
| **Avaliador da demo** | Quem acompanha a demonstração e analisa a qualidade do agente. | Ver o fluxo ponta a ponta e conferir se os dados sensíveis estão protegidos. |

**Cenários de uso**

1. **Cotação completa.** O lead informa idade, ano do veículo, CEP e data de início. O agente apresenta os três planos com prêmio mensal, franquia e coberturas. Quando o lead escolhe um plano, o agente pede o CPF, com consentimento.
2. **Cotação recusada.** O lead informa um veículo com mais de 20 anos. A cotação é recusada, o agente explica o motivo e encaminha a conversa ao vendedor.
3. **Cotação indisponível.** A cotação falha várias vezes seguidas. O agente informa que não consegue cotar agora, não inventa preço e encaminha a conversa.
4. **Pedido de humano.** O lead pede para falar com um vendedor. O agente encaminha, com o resumo da conversa.
5. **Consentimento recusado.** O lead recebe a cotação e não autoriza a coleta do CPF. O agente encaminha a conversa ao vendedor, sem o CPF.
6. **Encaminhamento visível.** Na interface simulada, a conversa aparece como encaminhada, com o motivo e o resumo para o vendedor.

## 4. Objetivos e métricas de sucesso

| # | Objetivo | Métrica | Meta |
| --- | --- | --- | --- |
| OBJ-1 | Cotar leads com dados completos | Percentual de conversas com dados completos que chegam às três cotações | **≥ 90%**, excluindo falhas da cotação. |
| OBJ-2 | Encaminhar no momento certo | Encaminhamentos feitos nos gatilhos definidos e só neles | **100%** dos casos de teste |
| OBJ-3 | Nunca inventar preço | Respostas com preço sem cotação oficial correspondente | **0** |
| OBJ-4 | Proteger dados pessoais | CPF, e-mail, telefone ou placa sem máscara em logs e traces | **0** |

## 5. Escopo

### 5.1 Incluso

- Conversa em português com o lead, pela interface simulada.
- Coleta de idade, ano do veículo, CEP e data de início da vigência para a cotação.
- Pedido de CPF, com consentimento, depois da cotação e só quando o lead escolhe um plano.
- Cotação dos três planos (Essencial, Completo e Premium) para o mesmo lead.
- Encaminhamento para humano nos casos de cotação recusada, pedido do lead, cotação indisponível, recusa do CPF e dado inválido que persiste após as novas tentativas.
- Área de conversas encaminhadas na interface simulada, com motivo e resumo para o vendedor, incluindo o CPF sem máscara.
- Mascaramento de dados pessoais em logs e traces.
- Registro de cada conversa, mensagem e cotação, com identificador e status.

### 5.2 Fora de escopo

| Item | Situação | Motivo |
| --- | --- | --- |
| **Fechamento da venda** (boleto, apólice) | Fora do MVP | O agente só cota e encaminha. |
| **Negociação ou desconto** | Fora do MVP | Objeções de preço ficam com o vendedor. |
| **Mais de um veículo por lead** | Fora do MVP | Uma conversa cobre um único veículo. |
| **Troca de plano após a cotação** | Fora do MVP | Comparar ou trocar exige nova conversa. |
| **Ramos além de auto** | Fora do MVP | Residencial, vida e outros produtos não entram. |
| **Canal WhatsApp real** | Fora do MVP | A demo usa interface simulada. |
| **Notificação externa ao vendedor** | Fora do MVP | O encaminhamento aparece só na interface simulada. |
| **Piloto com leads reais** | Fora do MVP | Projeto de simulação, sem operação real. |

## 6. Requisitos funcionais

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-01 | O agente conduz a conversa em português, de forma objetiva, e não responde sobre seguro com informações fora das regras da AutoSeguro. | Must |
| RF-02 | O agente coleta idade, ano do veículo, CEP e data de início da vigência para cotar. | Must |
| RF-03 | Depois da cotação, quando o lead escolhe um plano, o agente informa a finalidade do CPF, que é entregá-lo ao vendedor, e pede consentimento. | Must |
| RF-04 | Com os dados completos, o agente apresenta os três planos com prêmio mensal, franquia e coberturas. | Must |
| RF-05 | O agente só informa preço, franquia ou cobertura que tenham vindo da cotação oficial. | Must |
| RF-06 | Quando a cotação é recusada, por idade fora da faixa aceita ou veículo com mais de 20 anos, o agente informa o motivo ao lead e encaminha a conversa ao vendedor. | Must |
| RF-07 | Quando o lead pede para falar com um humano, o agente encaminha a conversa ao vendedor. | Must |
| RF-08 | Quando a cotação falha de forma persistente, o agente informa o lead que a cotação está indisponível, não inventa preço e encaminha a conversa. | Must |
| RF-09 | Quando o lead não autoriza o CPF, o agente mantém a cotação já entregue e encaminha a conversa ao vendedor, sem o CPF. | Must |
| RF-10 | Ao encaminhar, o agente registra o motivo e um resumo da conversa, com os dados coletados, incluindo o CPF sem máscara quando houver. O vendedor vê tudo na área de conversas encaminhadas. | Must |
| RF-11 | Cada conversa termina com um status: cotada, encaminhada ou encerrada. A conversa é encerrada quando o lead desiste ou fica 30 minutos sem responder, sem cotação nem encaminhamento. | Must |
| RF-12 | Quando um dado obrigatório continua inválido após duas novas tentativas, o agente encaminha a conversa ao vendedor. | Must |

## 7. Requisitos não funcionais

| ID | Categoria | Requisito |
| --- | --- | --- |
| RNF-01 | Privacidade | CPF, e-mail, telefone, placa e CEP aparecem mascarados em logs e traces. |
| RNF-02 | Privacidade | O CPF só é coletado depois da cotação, quando o lead escolhe um plano, e depois do consentimento. O texto de consentimento usado é assumido como juridicamente correto, por se tratar de uma simulação. |
| RNF-03 | Confiabilidade | Toda resposta com preço passa por uma verificação contra as regras de negócio antes de chegar ao lead. |
| RNF-04 | Confiabilidade | O lead sempre recebe um retorno, mesmo quando a cotação demora ou falha. |
| RNF-05 | Rastreabilidade | Cada conversa, mensagem e cotação tem identificador e status, para ser auditada depois. |
| RNF-06 | Escopo técnico | O MVP roda localmente. Os únicos serviços externos são o modelo de linguagem, a ferramenta de observabilidade e o download, feito uma vez, do modelo de embeddings. |
| RNF-07 | Fonte das regras | As regras de preço e de elegibilidade vêm da tabela de planos da AutoSeguro. Nenhuma regra é inventada pelo agente. |

## 8. Decisões de produto e trade-offs

| Decisão | O que ganhamos | O que aceitamos |
| --- | --- | --- |
| Agente só cota e encaminha, sem fechar venda | Foco no que importa para a demo | A venda depende do vendedor. |
| Falha persistente da cotação vira encaminhamento | Nunca há preço inventado | O vendedor recebe conversas quando a cotação está fora do ar. |
| Coletar CPF com consentimento e entregar ao vendedor | O vendedor identifica o lead sem novo contato | Tratamento de dado sensível, com exigência de consentimento. |
| Pedir o CPF só depois da escolha de um plano | O lead vê os preços antes de dar dado sensível | Parte dos encaminhamentos sai sem CPF. |
| Recusa do CPF mantém a cotação e encaminha | O lead não perde o preço recebido | Mais conversas caem no vendedor. |
| Cotar os três planos para o mesmo lead | O lead compara as opções na mesma conversa | Três cotações por conversa, o que aumenta a exposição a falhas da cotação. |
| Interface simulada como único canal | Controle total da demo | Não valida o canal real do WhatsApp. |

**Premissa de LGPD.** O projeto é uma simulação, mas segue um processo semelhante ao produtivo. O texto de consentimento é assumido como juridicamente correto. Um uso real com leads exigiria revisão adicional da base legal e do prazo de guarda dos dados.

## 9. Dependências

| Dependência | Responsável | Tipo |
| --- | --- | --- |
| Confirmação das regras de preço e elegibilidade da tabela de planos | AutoSeguro | Resolvida: `plans.json` é a fonte de verdade, confirmado pelo usuário |
| Texto de consentimento para o CPF | AutoSeguro e jurídico | Externa, assumida como aprovada para a simulação |
| Chave de acesso ao modelo de linguagem | Usuário | Interna, fornecida no arquivo de ambiente |
| Conta de observabilidade, gratuita e pública | Usuário | Interna |

## 10. Riscos e mitigação

| # | Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- | --- |
| R-1 | O agente informa preço que não veio da cotação | Média | Alto | Verificação antes do envio (RNF-03) e teste dedicado (OBJ-3). |
| R-2 | O CPF aparece em log ou trace | Média | Alto | Mascaramento obrigatório (RNF-01) e verificação dos logs na demo. |
| R-3 | A conta de observabilidade é pública e expõe conversas | Média | Alto | Só entram dados já mascarados nos traces. |
| R-4 | A cotação falha com frequência e a experiência fica ruim | Alta | Médio | Encaminhamento após falhas persistentes (RF-08) e aviso claro ao lead. |
| R-5 | Consentimento insuficiente para tratar o CPF | Baixa | Alto | Texto de consentimento assumido como juridicamente correto para a simulação. Revisar antes de qualquer uso real. |
| R-6 | Regras de preço mudam durante o MVP | Baixa | Médio | A tabela de planos é a única fonte de regras (RNF-07). |

## 11. Critérios de aceitação

1. **Dado** um lead com idade e veículo elegíveis, **quando** fornece os dados necessários, **então** o agente apresenta os três planos com prêmio, franquia e coberturas vindos da cotação.
2. **Dado** um veículo com mais de 20 anos, **quando** a cotação é recusada, **então** o agente informa o motivo e a conversa aparece como encaminhada, com o motivo.
3. **Dado** que a cotação falha de forma persistente, **quando** o lead pede o preço, **então** o agente não informa valor e a conversa é encaminhada.
4. **Dado** que o lead pede para falar com um humano, **quando** o pedido acontece, **então** a conversa é encaminhada com o resumo.
5. **Dado** que o lead recebeu a cotação e não autoriza o CPF, **quando** a recusa acontece, **então** a conversa é encaminhada sem o CPF e a cotação permanece registrada.
6. **Dado** que o lead ainda não escolheu um plano, **quando** a conversa acontece, **então** o agente não pede o CPF.
7. **Dado** qualquer conversa com CPF, **quando** os logs e traces são consultados, **então** o CPF aparece mascarado.
8. **Dado** uma conversa, **quando** é encerrada, **então** ela tem status final (cotada, encaminhada ou encerrada) e registro das cotações.
9. **Dado** uma resposta com preço, **quando** não há cotação oficial correspondente, **então** a resposta não é enviada ao lead.
10. **Dado** um dado obrigatório inválido em três respostas seguidas, **quando** a terceira falha acontece, **então** a conversa é encaminhada ao vendedor.

## 12. Validação

- **Roteiro de demonstração** com cinco casos: cotação completa, recusa por regra, falha persistente, pedido de humano e recusa do CPF.
- **Revisão de logs e traces** para confirmar o mascaramento de dados pessoais.
- **Teste de preço inventado**: conversas com a cotação indisponível, verificando que nenhum valor aparece.
- **Conferência das regras** com a tabela de planos, caso a caso.

## 13. Questões em aberto

Nenhuma questão aberta neste momento.
