---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0008 — Cliente HTTP httpx para o serviço de cotação, com timeout de 5 segundos

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['A RFC-0006 define um timeout de 5 segundos por cotação, e a RFC-0005 define retry para erros 5xx. A chamada precisa tratar timeout e status separadamente.']

## Decisão

- Usar httpx como cliente HTTP da cotação.
- Configurar timeout de 5 segundos por tentativa, e prazo total de 15 segundos para a cotação completa dos três planos.
- Tratar timeout como falha transitória, retentada como um 5xx.
- Tratar 5xx como erro transitório, para retry, e 422 e 400 como respostas de negócio ou payload, sem retry.
- Três tentativas por chamada, com esperas de 0,5 s e 1 s, conforme o FDD-0002.

## Consequências

- Chamadas assíncronas ficam disponíveis, se a interface precisar delas.
- A distinção de 422 pelo corpo da resposta é feita na camada de cliente, conforme a RFC-0006.

## Alternativas consideradas

- requests: cliente síncrono e conhecido, sem versão assíncrona nativa.

## Decisões relacionadas

- [[rfc-0006-servico-de-cotacao]]
- [[rfc-0005-modelo-llm-e-apis-externas]]
