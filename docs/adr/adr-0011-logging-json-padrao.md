---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0011 — Logging com o módulo padrão do Python, saída em JSON

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['A aplicação precisa de logs que possam ser filtrados e que nunca tragam dado pessoal sem máscara, conforme a RFC-0008.']

## Decisão

- Usar o módulo logging da biblioteca padrão do Python.
- Emitir cada registro de log como JSON, com campos fixos: nível, horário, etapa, identificador da conversa e evento.
- Registrar eventos de mascaramento com o tipo e a contagem, nunca o valor.

## Consequências

- Sem dependência extra de logs.
- Os logs passam pela mesma regra de mascaramento dos traces.

## Alternativas consideradas

- structlog: recursos de contexto por requisição, mas uma dependência a mais.

## Decisões relacionadas

- [[rfc-0008-mascaramento-de-dados-pessoais]]
- [[rfc-0002-integracao-langsmith]]
