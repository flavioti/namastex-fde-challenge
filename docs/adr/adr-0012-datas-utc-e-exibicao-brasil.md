---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0012 — Datas em UTC no armazenamento e exibição no horário de Brasília

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['Traces, registros e logs precisam ser comparáveis entre si. A simulação é voltada a um público brasileiro.']

## Decisão

- Armazenar todas as datas e horários em UTC, no banco e nos logs.
- Exibir na interface no horário de Brasília.
- Validar a data de início da vigência como data civil de Brasília, a partir de hoje, conforme o FDD-0001.

## Consequências

- Trace e registro ficam alinhados no mesmo instante.
- A conversão para Brasília acontece apenas na apresentação.

## Alternativas consideradas

- Horário local da máquina em tudo: inconsistente se o ambiente mudar de fuso.

## Decisões relacionadas

- [[fdd-0001-fluxo-de-conversa-e-coleta]]
- [[rfc-0001-simulador-de-conversa]]
