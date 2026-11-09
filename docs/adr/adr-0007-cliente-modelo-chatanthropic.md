---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0007 — Cliente do modelo Claude por ChatAnthropic, do LangChain

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['O agente usa o LangGraph para orquestrar, e o LangSmith para tracing. Os dois se integram melhor com os componentes do LangChain.']

## Decisão

- Chamar o modelo Claude pelo componente ChatAnthropic, do LangChain.
- Usar o mesmo componente para o agente e para o juiz, trocando apenas o identificador do modelo.

## Consequências

- O tracing e os nós do grafo recebem as chamadas sem adaptadores.
- A versão do componente segue o lock, conforme a ADR-0001.

## Alternativas consideradas

- SDK oficial da Anthropic direto: mais controle, mas exige adaptar o tracing e o grafo.

## Decisões relacionadas

- [[rfc-0005-modelo-llm-e-apis-externas]]
- [[rfc-0007-agente-langgraph-langchain]]
- [[adr-0006-estado-do-grafo-pydantic]]
