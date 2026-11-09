---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0013 — Teto de cerca de 50 mil tokens por conversa, com encaminhamento ao atingir

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['A RFC-0005 define um teto de tokens por conversa, para evitar loops e gasto sem controle. O teto conta agente e juiz juntos.']

## Decisão

- Definir o teto inicial em cerca de 50 mil tokens por conversa, somando agente e juiz.
- Ao atingir o teto, a conversa é encaminhada para um humano, com o motivo registrado.
- O valor é ajustado nos testes, com registro da mudança.

## Consequências

- O teto limita tokens, e não custo. O custo é acompanhado separadamente por agente e juiz no LangSmith.
- Conversas longas e legítimas podem ser encaminhadas, e o valor deve ser revisto com os testes.

## Alternativas consideradas

- Teto de 20 mil ou de 100 mil tokens: descartados na RFC-0005, por trade-off entre corte precoce e proteção contra loops.

## Decisões relacionadas

- [[rfc-0005-modelo-llm-e-apis-externas]]
- [[rfc-0007-agente-langgraph-langchain]]
