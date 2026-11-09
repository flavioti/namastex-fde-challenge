---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0006 — Estado do grafo do agente modelado com Pydantic

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['O agente passa dados por várias etapas, e alguns deles são sensíveis ou precisam de formato correto, como CEP, data de início e CPF. Erros de formato devem aparecer cedo.']

## Decisão

- Modelar o estado do grafo com Pydantic, com validação ao entrar e sair de cada etapa.
- Usar o estado para os dados coletados, as cotações, o status e o motivo de encaminhamento, conforme a RFC-0007.

## Consequências

- Erros de formato aparecem na etapa em que ocorrem, com mensagem clara.
- Há uma pequena dependência do modelo de validação em toda a aplicação.

## Alternativas consideradas

- TypedDict: apenas tipagem estática, sem validação em tempo de execução. Erros só aparecem mais tarde.

## Decisões relacionadas

- [[rfc-0007-agente-langgraph-langchain]]
- [[adr-0007-cliente-modelo-chatanthropic]]
