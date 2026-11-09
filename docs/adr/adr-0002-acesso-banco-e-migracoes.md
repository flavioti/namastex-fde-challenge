---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0002 — Acesso ao Postgres com psycopg 3 e SQL, migrações em arquivos SQL versionados

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['O banco combina tabelas convencionais, índice vetorial com pgvector e busca textual nativa. Essas funções exigem SQL específico, como tsvector, índices GIN e operadores do pgvector.']

## Decisão

- Acessar o Postgres com o driver psycopg 3, usando consultas SQL escritas à mão e um pool de conexões compartilhado pela aplicação, conforme o FDD-0004.
- Versionar o esquema em arquivos SQL numerados, aplicados em ordem por um script.
- Não usar ORM para o acesso ao banco.

## Consequências

- As consultas de busca ficam visíveis e revisáveis em SQL.
- O esquema é auditável como histórico de arquivos, sem depender de uma ferramenta de migração.
- Cada consulta precisa ser escrita e testada à mão, o que aumenta o código de acesso a dados.

## Alternativas consideradas

- SQLAlchemy como ORM, com Alembic para migrações: esconde o SQL que a busca híbrida usa.
- SQLAlchemy sem ORM, só como camada de conexão: mistura abstrações sem ganho claro.

## Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]
- [[adr-0001-python-e-gerenciador]]
