---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0011 — Avaliação e testes

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0002-integracao-langsmith]] · [[rfc-0008-mascaramento-de-dados-pessoais]] · [[rfc-0009-juiz-e-regras-de-validacao]] · [[rfc-0010-contrato-interface-agente]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define as duas camadas de verificação, os casos de avaliação, os critérios de aprovação e a forma de rotulagem. Não é especificação final. O catálogo completo de casos e o limiar de concordância do juiz ficam para a implementação e para a primeira rodada.

## 1. Resumo executivo (TL;DR)

A verificação tem duas camadas:

1. **Testes de código**, automatizados, deterministas e sem custo de modelo. Rodam sempre, a cada alteração.
2. **Avaliação de comportamento**, no LangSmith, com casos de conversa. Roda de forma manual, antes de cada entrega.

As metas de aprovação são as do PRD. Uma rodada é reprovada se houver regressão em OBJ-2 ou OBJ-3. A concordância do juiz com a rotulagem humana é medida em uma amostra.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] define metas de sucesso e uma seção de validação. A [[rfc-0002-integracao-langsmith]] descreve a avaliação offline, mas não define o que os casos cobrem nem como a aprovação é decidida.

Parte das regras é determinística, como a detecção de PII, a verificação de valores e o contrato da interface. Testá-las só na avaliação, com modelo, seria caro e lento. Por isso, elas ganham testes de código.

## 3. Proposta conceitual

### 3.1 Testes de código

Os testes de código cobrem as partes determinísticas do sistema:

- **Mascaramento**, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]]: cada tipo de dado, em variações de formato, e a ausência de vazamento para o modelo, os traces e os logs.
- **Verificação de valores**, conforme a [[rfc-0009-juiz-e-regras-de-validacao]]: a comparação entre a resposta e o resultado oficial, em casos com valores corretos e incorretos.
- **Cotação e erros**, conforme a [[rfc-0006-servico-de-cotacao]]: tratamento dos 422, dos 5xx e do timeout de 5 segundos.
- **Contrato da interface**, conforme a [[rfc-0010-contrato-interface-agente]]: chamada do turno, leitura do estado no banco e tratamento de erro inesperado.

Esses testes usam um agente de teste no lugar do modelo, quando for preciso. Eles não chamam a API da Anthropic.

### 3.2 Casos de avaliação

Os casos de avaliação são conversas completas, rodadas no LangSmith. Eles vêm de duas fontes, conforme a [[rfc-0002-integracao-langsmith]]: o dataset de conversas e os cenários do PRD.

Os casos cobrem pelo menos estas situações:

- cotação completa, com os três planos;
- recusa por regra, por idade ou por veículo;
- falha persistente da cotação;
- pedido do lead para falar com humano;
- recusa do CPF, com a cotação já entregue;
- conversa longa, com resumo acumulado;
- tentativa de obter preço sem cotação;
- conversa com dado pessoal que o lead insiste em repetir.

### 3.3 Rodada de avaliação

A avaliação roda de forma manual, antes de cada entrega. O avaliador dispara a rodada e acompanha o resultado no LangSmith.

Cada rodada registra a versão do prompt e do modelo, conforme a [[rfc-0002-integracao-langsmith]]. Assim, rodadas diferentes podem ser comparadas.

### 3.4 Critérios de aprovação

A rodada é aprovada se atender às metas do PRD:

- OBJ-1: pelo menos 90% das conversas com dados completos chegam às três cotações, excluindo falhas da cotação;
- OBJ-2: 100% dos encaminhamentos acontecem nos gatilhos definidos, e só neles;
- OBJ-3: nenhuma resposta com preço sem cotação oficial correspondente;
- OBJ-4: nenhum dado pessoal sem máscara em logs e traces.

Qualquer queda em OBJ-2 ou OBJ-3, em relação à rodada anterior, reprova a versão. Isso segue a regra de regressão da RFC-0002.

### 3.5 Rotulagem do juiz

Uma amostra de respostas é rotulada por um avaliador humano, como aprovada ou reprovada. Essa amostra é o gabarito.

O juiz é avaliado contra o gabarito. A medida é a concordância entre o juiz e o humano, por regra. Discordâncias são analisadas, e o juiz ou suas instruções são revisados quando a concordância ficar abaixo do limiar.

### 3.6 Registro dos resultados

Os resultados de cada rodada ficam no LangSmith e, de forma resumida, na área de avaliação do banco, conforme a [[rfc-0003-banco-postgres-pgvector]]. Assim, a comparação entre rodadas não depende da ferramenta externa.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Avaliação a cada alteração no código** | Detecta regressão cedo, mas tem custo alto de modelo a cada mudança. Foi descartada pelo usuário, que escolheu rodada manual. |
| ALT-2 | **Só avaliação no LangSmith, sem testes de código** | Regras determinísticas só aparecem em rodadas caras e lentas. Foi descartada pelo usuário. |
| ALT-3 | **Juiz avaliado sem gabarito humano** | Barato, mas não mede se o juiz está certo. Foi descartada pelo usuário, que escolheu rotulagem em amostra. |
| ALT-4 | **Testes de código chamando o modelo real** | Torna os testes lentos, caros e não determinísticos. Não foi adotada. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Quando a avaliação roda | Manual, antes de cada entrega. |
| QA-2 | Testes de código | Sim, para mascaramento, regras e fronteira. |
| QA-3 | Rotulagem do juiz | Avaliador humano, em amostra. |

## 6. Premissas assumidas

- Os testes de código não chamam a API da Anthropic e rodam sem custo de modelo.
- A amostra de 50 respostas cobre cada regra e os cenários do PRD.
- As metas de aprovação são as do PRD, sem alteração.

## 7. Limiar e amostra

- **Limiar de concordância do juiz:** 90%, medido por regra contra o gabarito humano.
- **Amostra rotulada:** 50 respostas, cobrindo as regras R1 a R4 e os cenários do PRD.

## 8. Impacto e riscos

**Impacto**

- **Código:** surge um conjunto de testes de código, separado do código da aplicação.
- **Operação:** cada entrega passa por uma rodada manual de avaliação, com custo de modelo.
- **Trabalho humano:** a rotulagem da amostra exige tempo do avaliador antes da primeira rodada.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Rodada manual esquecida antes da entrega | Versão entregue sem avaliação | Checklist de entrega, que inclui a rodada. |
| Amostra rotulada pequena ou enviesada | Concordância medida de forma falsa | Amostra que cubra os casos da seção 3.2. |
| Juiz concorda com o humano em casos fáceis e erra nos difíceis | Concordância alta mascara erros | Casos difíceis incluídos na amostra. |
| Custo do modelo por rodada | Gasto acima do esperado | Rodadas manuais e custo acompanhado no LangSmith. |
| Testes de código divergem do comportamento real | Regra passa no teste e falha na conversa | Casos de avaliação que exercitam as mesmas regras. |

## 9. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: metas de sucesso e seção de validação.
- [[rfc-0002-integracao-langsmith]]: avaliação offline, regressão e registro.
- [[rfc-0008-mascaramento-de-dados-pessoais]]: testes de mascaramento.
- [[rfc-0009-juiz-e-regras-de-validacao]]: testes de verificação de valores e gabarito do juiz.
- [[rfc-0010-contrato-interface-agente]]: testes de contrato.
