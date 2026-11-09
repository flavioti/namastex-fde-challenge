---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0009 — Identificadores UUID v4 para conversas, mensagens e cotações

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['Conversas, mensagens e cotações são referenciadas pelo banco, pelos traces e pela interface. Identificadores sequenciais revelariam a ordem de criação e exigiriam sequência no banco.']

## Decisão

- Usar UUID v4 como identificador de conversas, mensagens, cotações, encaminhamentos e avaliações.
- Gerar o identificador na aplicação, antes da gravação.

## Consequências

- O mesmo identificador liga a conversa ao trace, conforme a RFC-0002.
- Identificadores são mais longos e menos legíveis na tela, o que é aceito.

## Alternativas consideradas

- Inteiros sequenciais: mais curtos, mas revelam ordem e exigem sequência no banco.

## Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]
- [[rfc-0002-integracao-langsmith]]
