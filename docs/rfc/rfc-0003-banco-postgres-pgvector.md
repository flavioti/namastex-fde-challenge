---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0003 — Banco Postgres local com pgvector (uso híbrido)

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0001-simulador-de-conversa]] · [[rfc-0002-integracao-langsmith]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define requisitos conceituais do banco. Não é especificação final. Escolhas de índice, dimensão de vetor, modelo de embeddings, estratégia de ranking e ferramenta de migração ficam para ADRs próprios.

## 1. Resumo executivo (TL;DR)

Propomos um único Postgres local, na versão mais recente, com a extensão pgvector, subido pelo `docker-compose.yml`. Os dados ficam no volume `database/`, na raiz do repositório, e persistem entre execuções.

Esse banco é híbrido. Ele guarda:

1. **Registro operacional:** conversas, mensagens, cotações, encaminhamentos, ids de trace e resultados de avaliação, em tabelas convencionais.
2. **Catálogo de regras:** planos, coberturas, faixas de elegibilidade, carência e pro-rata, também em tabelas convencionais.
3. **Índice vetorial:** trechos de texto das regras, com embeddings de um modelo local e leve. Fica na mesma base que o catálogo, para que filtros e busca vetorial rodem na mesma consulta.
4. **Índice textual:** busca full-text nativa do Postgres, com coluna `tsvector`, índice GIN e configuração em português, sobre os mesmos trechos.

A busca é híbrida: combina o ranking textual com o ranking vetorial.

A cotação oficial continua vindo da API, nunca do índice ou do catálogo.

## 2. Contexto e problema

O [[prd-0001-agente-de-cotacao]] exige rastreabilidade de cada conversa, mensagem e cotação (RNF-05), e que o agente só informe valores vindos da cotação oficial (RF-05). A [[rfc-0001-simulador-de-conversa]] precisa guardar conversas para reabri-las e auditá-las. A [[rfc-0002-integracao-langsmith]] precisa ligar cada conversa ao trace correspondente e guardar os resultados do juiz.

O agente também precisa explicar regras de elegibilidade, franquia, carência e pro-rata com base na tabela oficial. Essa explicação depende de três tipos de acesso: filtrar regras por atributos, cruzar regras com o registro e encontrar trechos por significado. Um único banco com tabelas convencionais e vetores atende aos três.

## 3. Proposta conceitual

### 3.1 Instância única

Um único serviço Postgres, na versão mais recente estável com a extensão pgvector, é definido no `docker-compose.yml`. Os dados ficam no volume `database/`, na raiz. Esse volume não é versionado no git.

O banco fica acessível apenas no ambiente local. Não há exposição para fora da máquina.

### 3.2 Áreas lógicas

Os dados ficam na mesma base, separados em duas áreas por esquema:

- **Registro:** dados da simulação e da avaliação, com histórico.
- **Regras:** catálogo de planos e regras, mais o índice vetorial dos trechos.

Separar por esquema deixa claro o que é histórico e o que é derivado. O catálogo e o índice podem ser reconstruídos a partir da fonte oficial, sem perda. O registro não pode ser reconstruído, por isso é tratado como dado de primeira classe.

### 3.3 Área de registro

Guarda, conceitualmente:

- **Conversas**, com identificador, nome fictício do lead, status e data.
- **Mensagens**, em ordem dentro da conversa, com o papel de quem escreveu.
- **Cotações**, com os três planos recebidos e o momento da consulta.
- **Encaminhamentos**, com motivo e resumo para o vendedor.
- **Referências de trace**, ligando cada conversa ao trace do LangSmith.
- **Resultados de avaliação**, com a nota do juiz e os casos reprovados por rodada.

Cada registro tem identificador e status, como exige o RNF-05 do PRD.

### 3.4 Área de regras

O catálogo guarda, em tabelas convencionais, os planos, as coberturas, as faixas de idade, as faixas de idade do veículo, a região de risco, a carência e a regra de pro-rata. A fonte oficial continua sendo a tabela de planos da AutoSeguro (RNF-07 do PRD). O catálogo é uma materialização dessa fonte, reimportada quando ela muda.

Cada regra também tem um ou mais trechos de texto, com identificador de origem e um vetor gerado por um modelo local. O vetor fica na mesma tabela de trechos, ligado à regra de origem. Assim, uma consulta pode filtrar por atributos da regra e ordenar por similaridade no mesmo passo.

Cada trecho tem também uma coluna textual indexada, para a busca full-text em português. Cada trecho guarda uma impressão digital do conteúdo. Se a fonte mudar, só os trechos alterados são recalculados.

### 3.5 Usos híbridos previstos

Os três usos pedidos ficam assim:

1. **Filtrar a busca por atributos.** Uma pergunta sobre carência de furto no plano Premium filtra primeiro as regras do plano e da cobertura, e depois ranqueia os trechos por similaridade.
2. **Juntar registro e regras.** Uma consulta pode mostrar, para um encaminhamento, quais regras foram citadas na conversa e em que plano elas se aplicam.
3. **Ranquear por texto e por vetor.** Termos exatos, como pro-rata e carência, são encontrados pelo full-text. Significado parecido é encontrado pelo vetor. Os dois rankings são fundidos num ranking único, com método definido em ADR.

Os termos técnicos exatos não dependem do modelo de embeddings, porque o full-text os encontra diretamente. A fusão dos dois rankings é o ponto que precisa de calibração, verificada por casos de teste de recuperação.

O agente usa essas buscas para explicar regras. Ele não usa o resultado para decidir preço. O valor de cotação continua vindo da API, conforme o RF-05 do PRD.

### 3.6 Embeddings

Os embeddings são gerados por um modelo local, leve, que roda em qualquer máquina do avaliador, sem chave externa. Como o catálogo é pequeno, a qualidade desse modelo é suficiente.

A busca textual usa o full-text nativo do Postgres, com ts_rank para o ranking. BM25 foi descartado, porque exigiria extensão no Postgres. Ver ALT-9.

Trocar o modelo de embeddings obriga a recalcular o índice inteiro. Essa troca é uma decisão de ADR, não um ajuste de configuração.

### 3.7 Fora do índice

Os documentos de docs/ (PRD, RFC, ADR e FDD) não entram no índice. Eles são consultados diretamente, como manda o `CLAUDE.md`, pela rastreabilidade.

Os dados de conversas ficam na área de registro, sem vetor. O índice contém só regras, que não têm dado pessoal.

### 3.8 Dados pessoais no registro

O registro guarda conversas com dados pessoais.

- Mensagens e cotações ficam mascaradas, conforme o RNF-01 do PRD.
- O CPF aparece sem máscara só nos encaminhamentos, como exige o RF-10 do PRD.

Como o banco é local e acessado só pela aplicação, o risco é controlado. O dado sem máscara fica restrito à área de encaminhamentos.

### 3.9 Persistência

Os dados persistem entre execuções, no volume `database/`. Não há reset automático. Uma limpeza, se necessária, é uma ação explícita do avaliador.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Banco vetorial separado** (um serviço dedicado de vetores) | Soma um serviço a mais e impede filtrar vetores pelos atributos das tabelas comuns na mesma consulta. |
| ALT-2 | **SQLite local** | Não atende ao pedido de Postgres e não tem pgvector. |
| ALT-3 | **Embeddings por API externa** (Voyage ou OpenAI) | Exige nova chave e dependência externa. O modelo local atende ao catálogo pequeno. |
| ALT-4 | **Dois bancos**, um para registro e outro para regras e vetores | Impede cruzar registro e regras numa consulta, o que o uso híbrido exige. |
| ALT-5 | **Indexar documentos de design no RAG** | Mistura decisão de projeto com regra de negócio e aumenta o índice sem necessidade. A rastreabilidade já cumpre o papel. |
| ALT-6 | **Cotação feita pelo catálogo ou pelo índice** | Viola o RF-05 do PRD. O valor precisa vir da cotação oficial. |
| ALT-7 | **Guardar CPF mascarado também nos encaminhamentos** | Contraria o RF-10 do PRD, que exige o CPF sem máscara para o vendedor. |
| ALT-8 | **Regras só em JSON, sem tabelas** | Impede filtrar e juntar regras com o registro numa consulta. O JSON continua como fonte, mas não como forma de consulta. |
| ALT-9 | **BM25 com extensão** | Oferece um ranking lexical mais refinado, mas exige extensão extra no Postgres. O full-text nativo com ts_rank atende ao caso, sem dependência adicional. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | O que o RAG indexa | Trechos das regras de cotação, na mesma base do catálogo. |
| QA-2 | Quais dados o Postgres registra | Conversas e mensagens, cotações e encaminhamentos, ids de trace e resultados de avaliação. |
| QA-3 | Origem dos embeddings | Modelo local, sem chave extra. |
| QA-4 | Documentos de design no RAG | Ficam fora. |
| QA-5 | Prioridade do modelo local | Leve, para rodar em qualquer máquina. |
| QA-6 | Persistência dos dados | Volume persistente em `database/`. |
| QA-7 | Uso híbrido esperado | Filtrar a busca por atributos, juntar registro e regras, e combinar texto e vetor. |
| QA-8 | Uso do Postgres além dos embeddings | Tabelas convencionais para registro e catálogo de regras, junto com os vetores. |
| QA-9 | Combinação da busca | Híbrida: full-text nativo com ts_rank, somado à similaridade vetorial. |
| QA-10 | Extensão extra para BM25 | Não. Só pgvector e o full-text nativo do Postgres. |
| QA-11 | Configuração de idioma da busca textual | Português. |

## 6. Impacto e riscos

**Impacto**

- **Operação:** o `docker-compose.yml` ganha o serviço de banco, com volume em `database/`. Essa mudança será feita na implementação, não nesta fase.
- **Código:** a aplicação lê e grava no registro, lê o catálogo de regras e mantém o índice vetorial.
- **Ambiente:** o avaliador sobe o banco antes da aplicação. Sem o banco, a simulação não guarda histórico nem consulta regras.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| CPF sem máscara no registro de encaminhamentos | Dado pessoal acessível a quem tiver acesso ao banco | Acesso restrito ao ambiente local. O CPF fica só na área de encaminhamentos. |
| Catálogo ou índice desatualizados em relação à tabela de planos | O agente explica regra antiga | Reimportação quando a fonte muda, com impressão digital por trecho. |
| Consultas híbridas complexas | Resposta lenta ou difícil de manter | Consultas pequenas e documentadas. |
| Fusão dos rankings mal calibrada | Regra errada recuperada para o agente | Casos de teste de recuperação, avaliados no LangSmith, conforme a RFC-0002. |
| Troca do modelo de embeddings | Índice inconsistente com a busca | Recalcular o índice inteiro junto com a troca, registrado em ADR. |
| Volume de dados cresce sem limpeza | Ambiente local lento | Limpeza explícita pelo avaliador, sem automação nesta fase. |

## 7. Pontos para ADRs futuros

Estes pontos eram técnicos e foram decididos em documentos próprios, sem mudar o que foi decidido aqui:

- Modelo local de embeddings e dimensão do vetor: [[adr-0003-modelo-de-embeddings]].
- Tipo de índice vetorial e métrica de similaridade: [[adr-0004-indice-vetorial-e-metrica]].
- Método de fusão dos rankings textual e vetorial: [[adr-0005-busca-hibrida-rrf]].
- Configuração do índice textual em português: [[fdd-0004-banco-e-migracoes]].
- Ferramenta de migração do esquema: [[adr-0002-acesso-banco-e-migracoes]].
- Formato detalhado das tabelas de cada área: [[fdd-0004-banco-e-migracoes]].

## 8. Decisões relacionadas

- [[prd-0001-agente-de-cotacao]]: rastreabilidade, privacidade e verificação de preço.
- [[rfc-0001-simulador-de-conversa]]: conversas que o banco guarda e reabre.
- [[rfc-0002-integracao-langsmith]]: ids de trace e resultados de avaliação que o banco registra.
- [[adr-0002-acesso-banco-e-migracoes]], [[adr-0003-modelo-de-embeddings]], [[adr-0004-indice-vetorial-e-metrica]] e [[adr-0005-busca-hibrida-rrf]]: decisões de banco, modelo, índice e fusão.
