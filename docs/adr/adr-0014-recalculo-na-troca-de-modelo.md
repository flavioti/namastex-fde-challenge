---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0014 — Recálculo completo do índice na troca de modelo de embeddings

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['Vetores gerados por modelos diferentes não são comparáveis. Um índice misturado daria resultados sem sentido.']

## Decisão

- Cada vetor guarda o identificador do modelo e a dimensão.
- Trocar o modelo recalcula todo o índice, e não apenas os trechos alterados.
- A troca é feita como mudança registrada, com rodada de avaliação depois.

## Consequências

- Trocas de modelo são raras e custam tempo de carga, o que é aceito.
- A divergência entre vetores antigos e novos é detectada pelos metadados.

## Alternativas consideradas

- Recalcular apenas os trechos alterados: mistura modelos no mesmo índice.

## Decisões relacionadas

- [[rfc-0004-geracao-de-embeddings]]
- [[adr-0003-modelo-de-embeddings]]
