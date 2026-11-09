---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0002 — Integração com o LangSmith (observabilidade e avaliação)

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0001-simulador-de-conversa]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define requisitos conceituais da integração. Não é especificação final. Decisões técnicas detalhadas, como formato de metadados e esquema de datasets, ficam para RFCs próprias.

## 1. Resumo executivo (TL;DR)

Propomos usar o LangSmith em um único projeto público da conta gratuita para duas coisas: registrar cada execução do agente como um trace e avaliar o agente offline sobre casos de teste. Os traces saem sempre mascarados. Uma segunda camada de redaction, antes do envio, remove qualquer PII que tenha escapado.

O juiz do próprio projeto avalia as respostas e envia o resultado ao LangSmith como feedback. Os prompts ficam versionados no git. Os avisos ao avaliador só acontecem quando algo exige ação.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige rastreabilidade de cada conversa, mensagem e cotação, e a verificação de que o agente não inventa preço. Também exige que nenhum CPF apareça sem máscara em logs ou traces.

Sem uma ferramenta de observabilidade, depurar uma conversa ruim depende de logs espalhados. Medir se o agente mudou de comportamento entre versões fica manual e pouco confiável.

## 3. Proposta conceitual

### 3.1 Escopo de uso

O LangSmith cobre duas frentes:

- **Tracing.** Cada execução do agente, de ponta a ponta, vira um trace, com as etapas, as entradas, as saídas e a latência.
- **Avaliação offline.** Datasets de casos de teste rodam contra o agente, e os resultados ficam comparáveis entre versões.

A avaliação online, sobre as conversas reais da simulação, fica fora desta fase.

### 3.2 Organização do projeto

Todos os traces vão para um único projeto do MVP. Execuções de teste, demonstração e avaliação se diferenciam por tags, não por projetos separados.

O projeto é público, conforme combinado. Por isso, a proteção de dados precisa estar em vigor antes de qualquer envio.

### 3.3 O que cada trace guarda

Cada trace guarda as entradas e as saídas **já mascaradas**: mensagens do lead, dados coletados e cotações. Isso permite depurar sem expor PII. Também guarda metadados operacionais: identificador da conversa, versão dos prompts, etapa, latência e status.

Cada conversa guardada no banco local registra o identificador do trace correspondente, para que a conversa e a execução possam ser cruzadas.

### 3.4 Camadas de proteção de dados

Há duas camadas, em sequência:

1. **Mascaramento na entrada do agente.** Já previsto no PRD. Remove ou substitui CPF, e-mail, telefone, placa e CEP antes que a mensagem seja processada.
2. **Redaction no envio.** Antes de cada trace sair da aplicação, um filtro remove qualquer padrão de PII que tenha escapado à primeira camada.

A segunda camada existe porque o projeto é público. Ela não substitui a primeira. Os testes de mascaramento do PRD continuam valendo.

### 3.5 Avaliação offline

Os casos de teste vêm de duas fontes:

- **Dataset de conversas** do repositório, usado como base de casos reais, já mascarados antes de qualquer uso.
- **Casos escritos a partir do PRD**, cobrindo os cenários e os critérios de aceitação, incluindo falha persistente, recusa por regra, pedido de humano e recusa do CPF.

Cada rodada de avaliação compara a versão atual do agente com a anterior. Um caso reprovado tem motivo registrado.

### 3.6 Juiz e feedback

O juiz (LLM-as-a-judge) roda no código do projeto, antes de cada resposta chegar ao lead, conforme o PRD. O mesmo juiz é usado na avaliação offline. O resultado de cada avaliação é enviado ao LangSmith como feedback associado ao trace.

Assim, a mesma regra vale em produção simulada e em teste, e o LangSmith apenas registra e compara os resultados.

### 3.7 Regra de regressão

Qualquer queda em OBJ-2 (encaminhamento fora dos gatilhos) ou em OBJ-3 (preço inventado) conta como regressão. Essas metas são de 100% e de zero, respectivamente, e não admitem queda. Uma regressão bloqueia a versão até que seja analisada.

### 3.8 Versionamento de prompts

Os prompts são arquivos do repositório, versionados no git. Cada trace registra a versão do prompt usada, como metadado, para comparar execuções de versões diferentes.

### 3.9 Avisos ao avaliador

O avaliador é avisado apenas quando algo exige ação, conforme o `CLAUDE.md`:

- regressão em OBJ-2 ou OBJ-3;
- falha do juiz que impeça a avaliação;
- necessidade de análise manual na ferramenta.

Rodadas sem problemas não geram aviso.

### 3.10 Retenção

Os traces ficam no LangSmith enquanto o plano gratuito permitir. Não há limpeza manual programada nesta fase.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Só tracing, sem avaliação no LangSmith** | Deixa a comparação entre versões manual. Perde o principal ganho da ferramenta para este MVP. |
| ALT-2 | **Avaliação online sobre as conversas reais** | Exige mais volume e mais configuração. Não cabe no escopo de demonstração. |
| ALT-3 | **Um projeto por ambiente** | Separa execuções com pouco ganho. As tags já diferenciam teste, demo e avaliação. |
| ALT-4 | **Só metadados nos traces, sem conteúdo** | Impede depurar a resposta do agente. Esconde o que precisamos ver. |
| ALT-5 | **Avaliadores configurados no LangSmith** | Separa a regra de negócio do código e dificulta versionar a avaliação junto com o agente. |
| ALT-6 | **Prompts no LangSmith Hub** | Mistura a versão do prompt com a ferramenta de observabilidade. O git já dá histórico e revisão. |
| ALT-7 | **Projeto privado** | Não foi a escolha do usuário. Com os traces mascarados, a visibilidade pública é aceitável. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Escopo de uso do LangSmith | Tracing e avaliação offline. Avaliação online fica fora. |
| QA-2 | Organização dos projetos | Um único projeto para o MVP, com tags. |
| QA-3 | Conteúdo de cada trace | Entradas e saídas mascaradas, com metadados. |
| QA-4 | Quem executa a avaliação | O juiz do próprio projeto, com resultado enviado como feedback. |
| QA-5 | Origem dos casos de avaliação | Dataset de conversas e casos escritos a partir do PRD. |
| QA-6 | Camada extra de proteção antes do envio | Sim, redaction no envio, além do mascaramento na entrada. |
| QA-7 | Quando avisar o avaliador | Só quando algo exigir ação. |
| QA-8 | Onde ficam os prompts | No repositório, versionados no git. |
| QA-9 | O que conta como regressão | Qualquer queda em OBJ-2 ou OBJ-3. |
| QA-10 | Retenção dos traces | Enquanto o plano gratuito permitir. |
| QA-11 | Visibilidade do projeto | Público, com traces mascarados. |

## 6. Impacto e riscos

**Impacto**

- **Código:** o agente passa a enviar traces em cada execução. Surgem uma etapa de redaction antes do envio e um conjunto de casos de avaliação versionado no repositório.
- **Banco:** cada conversa guarda o identificador do trace correspondente.
- **Operação:** a conta gratuita do LangSmith passa a ser dependência do ambiente local. Sem ela, o agente segue funcionando, mas sem traces.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| PII escapa do mascaramento e chega ao projeto público | Dado pessoal exposto | Duas camadas, com teste dedicado que procura padrões de CPF, e-mail, telefone, placa e CEP nos traces. |
| Juiz reprova respostas legítimas | Falso alarme de regressão | Revisar casos reprovados antes de bloquear a versão. |
| Limite do plano gratuito é atingido | Traces param de ser gravados | Acompanhar o volume a cada rodada e registrar o limite no aviso ao avaliador. |
| Prompt muda sem registro | Comparação entre versões perde sentido | Prompt no git e versão registrada em cada trace. |

## 7. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: requisitos de rastreabilidade, privacidade e verificação de preço.
- [[rfc-0001-simulador-de-conversa]]: interface que gera as conversas registradas nos traces.
- [[adr-0017-metadados-de-trace-dicionario-unico]]: formato dos metadados dos traces.
- [[rfc-0009-juiz-e-regras-de-validacao]]: regras do juiz.
