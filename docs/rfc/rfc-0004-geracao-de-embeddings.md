---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0004 — Geração de embeddings das regras de cotação

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0003-banco-postgres-pgvector]] |
| **Documentos relacionados** | [[prd-0001-agente-de-cotacao]] · [[rfc-0002-integracao-langsmith]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define requisitos conceituais da geração de embeddings. Não é especificação final. Escolha exata do modelo, dimensão do vetor e formato de armazenamento ficam para ADRs próprios.

## 1. Resumo executivo (TL;DR)

Propomos gerar um embedding por regra do catálogo, com um modelo local, multilíngue e leve, de até cerca de 500 MB. O mesmo modelo gera os vetores dos trechos e os vetores das consultas.

Os embeddings são gerados na carga do catálogo e só para as regras cuja impressão digital mudou. O modelo roda em CPU e usa GPU quando houver. Na primeira execução, ele é baixado uma vez e fica guardado no volume `database/`.

Se o modelo não carregar, a busca para e avisa. Ela não responde com resultado parcial.

## 2. Contexto e problema

A [[rfc-0003-banco-postgres-pgvector]] define o índice vetorial dos trechos de regras e a busca híbrida com full-text. Ela deixa em aberto como os vetores são produzidos, quando são recalculados e o que acontece quando o modelo falha.

O [[prd-0001-agente-de-cotacao]] exige que o agente explique regras com base na tabela oficial (RF-05, RNF-07). Um vetor mal gerado ou desatualizado faria o agente recuperar uma regra errada. Por isso, a geração precisa ser reproduzível e rastreável.

## 3. Proposta conceitual

### 3.1 Unidade de embedding

Cada regra do catálogo vira um trecho, e cada trecho tem um embedding. Exemplos de regras: a faixa etária, a idade do veículo, a região de risco, a carência e o pro-rata.

Trechos curtos dão uma busca mais precisa do que trechos por plano ou por cobertura, porque cada vetor representa uma única regra.

### 3.2 Quando os embeddings são gerados

Os embeddings são gerados na carga do catálogo. A cada carga:

1. Cada trecho tem sua impressão digital recalculada a partir do conteúdo da regra.
2. A impressão digital é comparada com a já guardada.
3. Só os trechos com impressão digital diferente, ou novos, são embedados de novo.

Assim, uma mudança pequena na tabela de planos não recalcula o índice inteiro.

### 3.3 Modelo

O modelo é local, multilíngue, com foco em português, e tem até cerca de 500 MB. O mesmo modelo gera os vetores dos trechos e os vetores das consultas. Usar modelos diferentes para cada lado tornaria a comparação sem sentido.

Trocar o modelo obriga a recalcular todo o índice. Essa troca é decisão de ADR.

### 3.4 Hardware

A geração roda em CPU, que é suficiente para um catálogo pequeno. Quando houver GPU disponível, ela é usada automaticamente, com CPU como alternativa. O código não exige GPU.

### 3.5 Metadados de cada vetor

Cada vetor guarda, junto com o próprio valor:

- o identificador do modelo usado;
- a dimensão do vetor;
- a impressão digital do trecho;
- a data da geração.

Esses metadados permitem detectar um vetor gerado por outro modelo e forçar o recálculo. Sem eles, uma troca de modelo passaria despercebida.

### 3.6 Primeira execução e download

Na primeira execução, o modelo é baixado uma vez e fica guardado no volume `database/`. Depois disso, a geração roda sem acesso à internet. O download é a única chamada externa além da LLM, e acontece uma vez por ambiente.

### 3.7 Falha do modelo

Se o modelo não carregar ou falhar durante a geração ou a consulta, a busca para e avisa. Não há resposta parcial, nem busca só textual como substituto.

Um erro explícito evita que o agente recupere regras incompletas sem perceber. A falha fica registrada para análise.

### 3.8 Dados pessoais

Só regras de cotação entram na geração. Nenhuma mensagem de conversa, CPF ou outro dado pessoal é embedado. Isso é consequência direta da [[rfc-0003-banco-postgres-pgvector]].

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Um trecho por plano** | Cada vetor carrega várias regras, e a busca perde precisão. A pergunta sobre uma regra específica pode cair no plano errado. |
| ALT-2 | **Um trecho por cobertura** | Útil para perguntas sobre cobertura, mas deixa de fora regras que não são de cobertura, como faixa etária e região. |
| ALT-3 | **Recalcular a cada inicialização** | Gasta tempo sem necessidade, já que a fonte muda pouco. A impressão digital evita o trabalho. |
| ALT-4 | **Gerar sob demanda, na primeira consulta** | A primeira resposta do agente fica lenta e a falha aparece no meio da conversa, e não na carga. |
| ALT-5 | **Degradar para full-text quando o modelo falha** | Responde com resultado parcial, o que pode levar o agente a uma regra incompleta. Foi rejeitado pelo usuário. |
| ALT-6 | **Modelo grande, sem limite de tamanho** | Exige máquina mais potente e carga lenta. Foi rejeitado pelo usuário, que manteve o modelo leve. |
| ALT-7 | **Modelo pré-carregado no repositório** | Deixa o repositório pesado. O volume `database/` resolve a mesma necessidade. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Como os trechos são montados | Um trecho por regra. |
| QA-2 | Quando os embeddings são gerados | Na carga do catálogo, só quando a fonte muda. |
| QA-3 | Limite de tamanho do modelo | Até cerca de 500 MB, mantendo a decisão do RFC-0003. |
| QA-4 | Hardware | CPU, com GPU quando houver. |
| QA-5 | Comportamento quando o modelo falha | Para e avisa, sem resposta parcial. |
| QA-6 | Como o modelo chega ao ambiente | Baixa uma vez e guarda no volume `database/`. |

## 6. Premissas assumidas

Estas premissas seguem as RFCs anteriores e não foram perguntadas de forma explícita:

- O mesmo modelo gera vetores de trechos e de consultas.
- Cada vetor guarda o identificador e a dimensão do modelo.
- Trocar o modelo recalcula o índice inteiro.
- Só regras de cotação são embedadas.

Se alguma dessas premissas não valer, o documento deve ser revisado.

## 7. Impacto e riscos

**Impacto**

- **Código:** surge uma etapa de geração na carga do catálogo, com comparação de impressão digital.
- **Ambiente:** a primeira execução precisa de internet para baixar o modelo. As seguintes funcionam offline.
- **Banco:** cada vetor ganha metadados de modelo e de data.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Download do modelo falha na primeira execução | A busca não funciona no ambiente novo | Mensagem clara de erro, com instrução de tentar de novo com internet. |
| Modelo trocado sem recalcular o índice | Vetores de modelos diferentes se misturam | Metadado de modelo em cada vetor, com recálculo forçado quando diferente. |
| Carga inicial lenta em CPU | Demora para subir o ambiente | Catálogo pequeno e geração só para trechos alterados. |
| Regra mal interpretada pelo modelo | Agente explica regra errada | Casos de teste de recuperação, avaliados no LangSmith, conforme a [[rfc-0002-integracao-langsmith]]. |

## 8. Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]: banco e busca híbrida que consomem os embeddings.
- [[prd-0001-agente-de-cotacao]]: requisito de explicar regras com base na tabela oficial.
- [[rfc-0002-integracao-langsmith]]: casos de teste de recuperação.
- [[adr-0003-modelo-de-embeddings]]: modelo e dimensão do vetor.
- [[adr-0014-recalculo-na-troca-de-modelo]]: recálculo na troca de modelo.
