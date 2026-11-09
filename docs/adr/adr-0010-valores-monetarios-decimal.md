---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0010 — Valores monetários em Decimal com duas casas decimais

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['Prêmio, franquia e pro-rata são cálculos com centavos. Ponto flutuante pode gerar erro de arredondamento em valores exibidos ao lead.']

## Decisão

- Representar valores monetários com Decimal, com duas casas decimais.
- Converter o valor vindo da cotação para Decimal na entrada, antes de qualquer comparação.
- Arredondar apenas na apresentação, com regra única de arredondamento.

## Consequências

- A verificação de valores do juiz, RFC-0009, compara Decimal com Decimal.
- O serviço de cotação devolve números com ponto flutuante. A conversão na entrada deve ser testada.

## Alternativas consideradas

- Float: mais simples e nativo, mas sujeito a erros de arredondamento em centavos.

## Decisões relacionadas

- [[rfc-0006-servico-de-cotacao]]
- [[rfc-0009-juiz-e-regras-de-validacao]]
- [[adr-0008-cliente-http-cotacao]]
