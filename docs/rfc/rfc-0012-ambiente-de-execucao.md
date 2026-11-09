---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0012 — Ambiente de execução e configuração

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[prd-0001-agente-de-cotacao]] |
| **Documentos relacionados** | [[rfc-0003-banco-postgres-pgvector]] · [[rfc-0004-geracao-de-embeddings]] · [[rfc-0005-modelo-llm-e-apis-externas]] · [[rfc-0006-servico-de-cotacao]] · [[rfc-0010-contrato-interface-agente]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define quais serviços sobem em Docker, o que roda na máquina, como o ambiente é configurado e o que o README precisa ensinar. Não é especificação final. Versões exatas de imagens e a lista completa de variáveis ficam para a implementação.

## 1. Resumo executivo (TL;DR)

O ambiente tem duas partes. A infraestrutura sobe no Docker Compose: o banco Postgres com pgvector e o serviço de cotação. A aplicação, que inclui a interface Streamlit e o agente, roda na máquina, com `uv`.

São dois comandos para o avaliador: um sobe a infraestrutura, e outro sobe a aplicação. A configuração fica num arquivo `.env`, fora do git, e um `.env.example`, versionado, lista as variáveis sem valores.

O contêiner do serviço de cotação continua instalando dependências com pip, sem o lock do projeto. Esse risco é aceito, conforme a decisão do usuário.

## 2. Contexto e problema

Várias RFCs dependem do ambiente. O banco e a configuração de volume estão na [[rfc-0003-banco-postgres-pgvector]]. O download do modelo de embeddings, uma vez por ambiente, está na [[rfc-0004-geracao-de-embeddings]]. As chaves das APIs externas estão na [[rfc-0005-modelo-llm-e-apis-externas]]. O serviço de cotação e suas variáveis estão na [[rfc-0006-servico-de-cotacao]].

Nenhum documento define como essas partes sobem juntas nem o que o avaliador precisa fazer para rodar o projeto. O README do desafio exige essa explicação.

## 3. Proposta conceitual

### 3.1 Serviços no Docker Compose

O `docker-compose.yml` define a infraestrutura:

- **Postgres**, com a extensão pgvector e volume persistente em `database/`, conforme a [[rfc-0003-banco-postgres-pgvector]].
- **Serviço de cotação**, construído a partir de `quote-service/`, com as variáveis de falha e lentidão, conforme a [[rfc-0006-servico-de-cotacao]].

Não há outros serviços no compose nesta fase.

### 3.2 Aplicação na máquina

A interface Streamlit e o agente rodam na máquina, com `uv`. Eles acessam o banco e o serviço de cotação pelas portas expostas no compose.

Essa escolha facilita a depuração. O avaliador pode interromper, inspecionar e reiniciar a aplicação sem reconstruir imagens.

### 3.3 Ordem de subida

A infraestrutura sobe antes da aplicação. A aplicação só deve iniciar quando o banco estiver disponível. Se o banco não estiver no ar, a aplicação deve dizer isso claramente, e não falhar com erro genérico.

### 3.4 Configuração

Há dois arquivos:

- **`.env`**, com os valores reais: chave da API da Anthropic, chave do LangSmith, nome do projeto no LangSmith e conexão com o banco. Esse arquivo não é versionado.
- **`.env.example`**, versionado, com a lista de variáveis e sem valores.

O `.gitignore` já impede o versionamento do `.env`. O `.env.example` documenta o que o avaliador precisa preencher.

### 3.5 Dados persistentes

O volume `database/` guarda o banco. Ele persiste entre execuções, conforme a [[rfc-0003-banco-postgres-pgvector]]. O modelo de embeddings também fica em área persistente, para que o download aconteça uma vez, conforme a [[rfc-0004-geracao-de-embeddings]].

Limpar esses dados é uma ação explícita do avaliador, não um efeito de reiniciar os serviços.

### 3.6 Versões

A imagem do Postgres usa a versão mais recente estável com pgvector. A versão exata é fixada na implementação, para que o ambiente não mude sem aviso.

O contêiner do serviço de cotação instala dependências com pip, sem o lock do projeto. Essa decisão foi tomada pelo usuário, e o risco está registrado na seção 7.

### 3.7 README

O README do projeto ensina, nesta ordem:

1. preencher o `.env` a partir do `.env.example`;
2. subir a infraestrutura com o compose;
3. subir a aplicação com `uv`;
4. rodar a primeira vez, com download do modelo de embeddings;
5. reiniciar ou limpar o ambiente, quando necessário.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Aplicação dentro do Docker Compose** | Mais reproduzível, mas mais lento para depurar. Foi descartada pelo usuário, que escolheu rodar a aplicação com `uv`. |
| ALT-2 | **Um único comando para tudo** | Mais conveniente, mas depende de um script que precisa ser mantido. Foi descartada pelo usuário, que escolheu dois comandos. |
| ALT-3 | **Variáveis documentadas só no README** | Sem arquivo de exemplo, o avaliador precisa copiar a lista à mão. Foi descartada pelo usuário. |
| ALT-4 | **Contêiner do serviço de cotação com o uv.lock** | Alinha as versões ao lock do projeto. Foi descartada pelo usuário, que manteve o pip. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Onde roda a aplicação Streamlit | Na máquina, com `uv run`. |
| QA-2 | Quantos comandos para subir o ambiente | Dois: infraestrutura e aplicação. |
| QA-3 | Documentação da configuração | Arquivo `.env.example` versionado, sem valores. |
| QA-4 | Dependências do contêiner de cotação | Manter pip. |

## 6. Premissas assumidas

- O avaliador tem Docker e `uv` instalados na máquina.
- O avaliador tem acesso à internet na primeira execução, para baixar o modelo de embeddings.
- O `docker-compose.yml` define as portas expostas para a aplicação na máquina.

## 7. Impacto e riscos

**Impacto**

- **Operação:** o avaliador precisa de Docker e de `uv`, e de duas linhas de comando para subir o ambiente.
- **Configuração:** surgem o `.env.example` e a lista de variáveis, documentada no README.
- **Código:** o `docker-compose.yml` ganha o serviço do Postgres, e nenhum código de aplicação muda por causa desta RFC.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Contêiner de cotação com versões diferentes do lock | Comportamento pode mudar em relação à máquina | Risco aceito, por decisão do usuário. Registrado na RFC-0006 e aqui. Revisar se o comportamento divergir. |
| Tag `latest` do Postgres muda sem aviso | Ambiente muda entre execuções | Fixar a versão maior na implementação. |
| Aplicação sobe antes do banco | Erro confuso para o avaliador | Mensagem clara quando o banco não responde. |
| `.env` versionado por engano | Chave de API exposta | `.gitignore` e revisão antes de cada commit. |
| Primeira execução sem internet | Modelo de embeddings não baixa | Mensagem clara, com instrução de tentar com internet, conforme a RFC-0004. |

## 8. Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]: banco, volume e persistência.
- [[rfc-0004-geracao-de-embeddings]]: download do modelo e área persistente.
- [[rfc-0005-modelo-llm-e-apis-externas]]: chaves das APIs externas.
- [[rfc-0006-servico-de-cotacao]]: serviço de cotação e variáveis de falha.
- [[rfc-0010-contrato-interface-agente]]: interface e agente no mesmo processo.
