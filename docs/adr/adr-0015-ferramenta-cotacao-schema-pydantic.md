---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0015 — Descrição da ferramenta de cotação gerada do modelo Pydantic

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['O modelo chama a ferramenta de cotação com os argumentos descritos em um schema. Se o schema for escrito à mão, pode divergir da validação real do que a aplicação aceita.']

## Decisão

- Os argumentos validados da cotação são descritos por um modelo Pydantic interno, que a aplicação usa para validar os dados do estado.
- A ferramenta exposta ao modelo não tem parâmetros. A aplicação preenche os argumentos a partir do estado, incluindo o CEP, conforme a RFC-0005, a RFC-0008 e o FDD-0005. A descrição da ferramenta é um texto fixo.

## Consequências

- Uma única fonte para a validação dos dados da cotação, o que reduz divergência entre o estado e a chamada.
- Mudar a descrição da ferramenta exige alterar o texto fixo, e não o modelo Pydantic.
- O mesmo schema servirá de base para o servidor MCP futuro, conforme a [[adr-0019-chamada-direta-cotacao-mcp-futuro]].

## Alternativas consideradas

- Schema escrito à mão em JSON: pode divergir da validação real.

## Decisões relacionadas

- [[rfc-0005-modelo-llm-e-apis-externas]]
- [[rfc-0007-agente-langgraph-langchain]]
- [[adr-0006-estado-do-grafo-pydantic]]
