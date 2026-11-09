---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0008 — Mascaramento de dados pessoais

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0002-integracao-langsmith]] · [[rfc-0003-banco-postgres-pgvector]] · [[rfc-0005-modelo-llm-e-apis-externas]] · [[rfc-0007-agente-langgraph-langchain]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define o comportamento conceitual do mascaramento: quais dados, onde é aplicado e o que fica guardado. Não é especificação final. Os padrões de detecção e a ordem exata de aplicação ficam para a implementação, com testes próprios.

## 1. Resumo executivo (TL;DR)

Propomos um mascaramento determinístico, por padrões, para cinco tipos de dado: CPF, e-mail, telefone, placa e CEP. Cada dado detectado é substituído por um marcador do seu tipo, como `[CPF]`.

A máscara vale em três pontos: na mensagem do lead antes do modelo, na resposta do agente antes do envio e no conteúdo enviado aos traces e logs. O valor original não some. Ele fica no estado estruturado do agente, fora do modelo, e só o encaminhamento ao vendedor o lê.

A detecção não valida dígito verificador. Qualquer sequência no formato é mascarada. Um falso positivo é aceito, para que nenhum dado real passe.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige que CPF, e-mail, telefone, placa e CEP apareçam mascarados em logs e traces (RNF-01). Exige também que o CPF chegue ao vendedor sem máscara na aba de encaminhados (RF-10). Os dois requisitos precisam valer ao mesmo tempo.

A [[rfc-0002-integracao-langsmith]] usa o mesmo mascaramento para o conteúdo enviado ao LangSmith. A [[rfc-0007-agente-langgraph-langchain]] aplica o mascaramento na entrada do grafo. Esta RFC define as regras dessa etapa e o que ela guarda.

Há um ponto que exige cuidado. O CEP é usado na cotação, e o CPF é coletado para o vendedor. Os dois precisam chegar aos seus destinos sem que o modelo os veja.

## 3. Proposta conceitual

### 3.1 Tipos de dado

| Tipo | Marcador | Exemplo de origem |
| --- | --- | --- |
| CPF | `[CPF]` | Documento do lead, digitado na conversa |
| E-mail | `[EMAIL]` | Endereço informado pelo lead |
| Telefone | `[TELEFONE]` | Número de contato, com ou sem código do país |
| Placa | `[PLACA]` | Placa do veículo |
| CEP | `[CEP]` | Código postal informado para a cotação |

Nome, data de nascimento e idade exata não são mascarados nesta fase. Essa escolha é do usuário e fica registrada na seção 5.

### 3.2 Detecção

A detecção é determinística, por padrões de cada tipo. Não há modelo de linguagem nem validação de dígito verificador.

A regra é mascarar pelo formato. Um número que tenha a forma de CPF é mascarado, mesmo que não seja um CPF válido. Um falso positivo substitui um número por um marcador. Um falso negativo deixa um dado pessoal exposto. Por isso, a escolha é pelo primeiro.

A ordem de aplicação dos padrões é fixa e documentada. Tipos com formato numérico semelhante, como telefone e CEP, têm regra de precedência, para que um dado não seja mascarado duas vezes ou com o marcador errado.

### 3.3 Pontos de aplicação

O mascaramento acontece em quatro pontos:

1. **Mensagem do lead, antes do modelo.** O texto que o modelo recebe já traz os marcadores.
2. **Resposta do agente, antes do envio.** Se o modelo repetir um dado pessoal, ele é mascarado antes de chegar ao lead. A varredura vale mesmo que o dado tenha sido mascarado na entrada.
3. **Conteúdo dos traces**, conforme a [[rfc-0002-integracao-langsmith]].
4. **Logs da aplicação.** Logs guardam o evento de mascaramento, com o tipo e a contagem, mas nunca o valor.

### 3.4 Valor original

Quando o lead informa um CPF, o agente faz duas coisas ao mesmo tempo:

- o modelo recebe o texto com `[CPF]` no lugar do número;
- o valor original é extraído e guardado no estado estruturado da conversa.

O estado não é enviado ao modelo. Só a etapa de encaminhamento lê o CPF, para registrá-lo no registro de encaminhamentos da [[rfc-0003-banco-postgres-pgvector]], sem máscara, conforme o RF-10 do PRD.

O mesmo vale para o CEP. O valor original vai para o estado, e a ferramenta de cotação recebe o CEP da aplicação, e não do modelo. O modelo decide quando cotar, mas não escreve o CEP no payload. Assim, o CEP chega à cotação sem passar pelo modelo.

### 3.5 Saída do agente

Se a resposta do agente contiver um dado pessoal, a varredura da saída o substitui por `[dado omitido]` e registra o evento, com o tipo e sem o valor. A conversa segue normalmente.

A saída nunca deve repetir um dado mascarado. O juiz, descrito na [[rfc-0007-agente-langgraph-langchain]], também verifica isso.

### 3.6 Testes

Os testes usam um conjunto de mensagens com todos os tipos, em variações de formato, como com e sem pontuação, com espaços e com código do país. Três verificações são obrigatórias:

- nenhum valor original aparece no texto enviado ao modelo;
- nenhum valor original aparece nos traces nem nos logs;
- o valor original aparece no estado e chega ao encaminhamento, quando for o caso.

A meta é zero vazamento, conforme o OBJ-4 do PRD.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Detecção por modelo de linguagem ou reconhecimento de entidades** | Captura formatos mais variados, mas é menos previsível e depende de modelo. Não foi adotada, porque os cinco tipos definidos têm formato regular. |
| ALT-2 | **Máscara parcial**, como `***.***.***-09` | Mais informativa, mas deixa parte do dado no texto. Foi descartada pelo usuário, que escolheu o marcador por tipo. |
| ALT-3 | **Validar o dígito verificador do CPF** | Reduz falsos positivos, mas deixa passar um CPF digitado com erro. Foi descartada pelo usuário. |
| ALT-4 | **Descartar o valor original após o mascaramento** | Impede o encaminhamento com CPF, o que contraria o RF-10 do PRD. Foi descartada pelo usuário. |
| ALT-5 | **Mascarar só a entrada** | Deixa o modelo livre para repetir um dado pessoal na resposta. Foi descartada pelo usuário. |
| ALT-6 | **Modelo recebendo o valor original** | Expõe o dado ao provedor de LLM, o que contraria o RNF-01. Não foi considerada. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Tipos mascarados | CPF, e-mail, telefone, placa e CEP. |
| QA-2 | Valor original do CPF | Guardado no estado, fora do modelo, para o encaminhamento. |
| QA-3 | Máscara na saída do agente | Sim, também na saída. |
| QA-4 | Marcador | Por tipo, como `[CPF]`. |
| QA-5 | Validação do dígito verificador | Não. Mascarar pelo formato. |

## 6. Premissas assumidas

- A ordem de aplicação dos padrões é um detalhe de implementação, desde que seja fixa e testada.
- O texto que substitui um dado na saída do agente é `[dado omitido]`, conforme decisão do usuário. Ele não revela o tipo do dado.
- O CEP chega à cotação pela aplicação, a partir do estado, e o modelo não escreve esse valor.
- Os logs registram o tipo e a contagem de cada mascaramento, nunca o valor.

## 7. Impacto e riscos

**Impacto**

- **Código:** surge uma etapa determinística de mascaramento, usada na entrada, na saída, nos traces e nos logs.
- **Estado:** o estado da conversa guarda os valores originais de CPF, CEP e demais dados de cotação, em área fora do alcance do modelo.
- **Cotação:** a ferramenta de cotação recebe o CEP e os dados da aplicação, e não do modelo.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Formato não previsto escapa do padrão | Dado pessoal chega ao modelo ou aos traces | Testes com variações de formato, e revisão periódica dos padrões. |
| Ordem de aplicação gera marcador errado | Texto confuso, ou dado mascarado duas vezes | Precedência fixa e testes de sobreposição. |
| Nome do lead não é mascarado | Nome aparece em traces e logs | Aceito nesta fase, pela decisão do usuário. Revisar se o escopo mudar. |
| Modelo repete dado pessoal na saída | Dado chega ao lead ou aos traces | Varredura da saída e juiz. |
| Valor errado injetado na cotação | Cotação de CEP incorreto | Testes de cotação que comparam o CEP do estado com o CEP enviado. |
| Falso positivo mascara número de cotação ou protocolo | Texto perde informação | Aceito. O marcador deixa o texto legível. |

## 8. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: RNF-01, RF-10 e OBJ-4.
- [[rfc-0002-integracao-langsmith]]: redaction dos traces, com o mesmo conjunto de tipos.
- [[rfc-0003-banco-postgres-pgvector]]: registro de encaminhamentos com CPF sem máscara.
- [[rfc-0005-modelo-llm-e-apis-externas]]: envio ao modelo somente com dados mascarados.
- [[rfc-0007-agente-langgraph-langchain]]: etapa de entrada e juiz.
- [[adr-0020-padroes-deteccao-pii]]: padrões de detecção e ordem de precedência.
