---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0018 — Mensagens em tabela própria, ligada à conversa

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['O registro precisa permitir consultar, filtrar e auditar mensagem a mensagem, para a análise da RFC-0002 e para a aba de encaminhados da RFC-0001.']

## Decisão

- Guardar cada mensagem como linha em tabela própria, com identificador, conversa, ordem, papel e data.
- A ordem das mensagens dentro da conversa é um campo explícito, e não depende da ordem de inserção.

## Consequências

- Consultas por mensagem, por papel e por período ficam simples em SQL.
- Gravar uma mensagem exige uma linha nova, o que é aceito.

## Alternativas consideradas

- Lista dentro da conversa: mais simples de gravar, mas difícil de consultar por mensagem.

## Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]
- [[adr-0002-acesso-banco-e-migracoes]]
- [[adr-0009-identificadores-uuid]]
