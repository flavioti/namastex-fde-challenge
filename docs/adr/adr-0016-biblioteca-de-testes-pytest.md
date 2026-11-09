---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0016 — pytest como biblioteca de testes

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['Os testes de código da RFC-0011 incluem casos parametrizados de mascaramento, de verificação de valores e de contrato, em grande variedade de formatos.']

## Decisão

- Usar pytest para todos os testes de código.
- Usar fixtures para o agente de teste e o serviço de cotação simulado.

## Consequências

- Casos parametrizados ficam legíveis, com uma linha por variação de formato.
- Uma dependência de teste a mais, aceita no lock.

## Alternativas consideradas

- unittest: biblioteca padrão, mas com menos recursos para casos parametrizados.

## Decisões relacionadas

- [[rfc-0011-avaliacao-e-testes]]
- [[adr-0001-python-e-gerenciador]]
