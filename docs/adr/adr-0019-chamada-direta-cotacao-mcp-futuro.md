---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0019 — Chamada direta à cotação no MVP, com servidor MCP como evolução futura

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de revisão dos RFCs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

A cotação é uma ferramenta que o agente chama, conforme a [[rfc-0005-modelo-llm-e-apis-externas]]. O formato ideal para expor essa ferramenta seria um servidor MCP, que permitiria a qualquer agente ou cliente reutilizá-la com o mesmo contrato.

Para o MVP, há um único agente, um único consumidor da cotação e prazo curto. Um servidor MCP acrescentaria um processo a mais e uma camada de protocolo sem benefício imediato.

## Decisão

- No MVP, a aplicação chama a API de cotação diretamente, por HTTP, como ferramenta do agente. Não há servidor MCP nesta fase.
- O cliente HTTP segue a [[adr-0008-cliente-http-cotacao]], e o schema da ferramenta segue a [[adr-0015-ferramenta-cotacao-schema-pydantic]].
- O servidor MCP fica registrado como ponto de melhoria para versões futuras.

## Consequências

- Há um processo a menos para subir e um protocolo a menos para depurar no MVP.
- O agente fica acoplado ao endereço e ao contrato HTTP da cotação. Essa dependência é aceita nesta fase.
- Na evolução, o servidor MCP deve expor o mesmo schema. A lógica do juiz e a regra de que todo valor vem da cotação não mudam, porque continuam dependendo apenas do resultado da ferramenta.

## Evolução futura

O servidor MCP deve ser considerado quando houver:

- mais de um agente ou cliente usando a cotação;
- necessidade de reutilizar a ferramenta fora deste projeto;
- necessidade de controle de acesso ou de versão do contrato da ferramenta.

## Alternativas consideradas

- Servidor MCP já no MVP: descartado pelo usuário, por escopo e prazo. Fica como evolução.

## Decisões relacionadas

- [[rfc-0005-modelo-llm-e-apis-externas]]
- [[rfc-0006-servico-de-cotacao]]
- [[rfc-0007-agente-langgraph-langchain]]
- [[adr-0008-cliente-http-cotacao]]
- [[adr-0015-ferramenta-cotacao-schema-pydantic]]
