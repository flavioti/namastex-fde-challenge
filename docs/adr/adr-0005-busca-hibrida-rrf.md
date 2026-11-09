---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0005 — Busca híbrida com full-text em português e vetores, fundidos por RRF

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['A busca precisa encontrar termos técnicos, como pro-rata e carência, e também trechos de mesmo significado. As duas buscas têm escalas de pontuação diferentes.']

## Decisão

- Usar o full-text nativo do Postgres, com coluna tsvector, índice GIN, configuração em português e ts_rank.
- Fundir o ranking textual com o vetorial pelo Reciprocal Rank Fusion, que soma o inverso da posição de cada trecho nos dois rankings.
- Não usar BM25, porque exigiria extensão extra.

## Consequências

- Não é preciso normalizar os scores das duas buscas, o que simplifica a fusão.
- A configuração de idioma do Postgres deve ser a de português, e é verificada nos casos de recuperação.
- A constante do RRF é 60, o valor padrão, ajustável nos testes de busca. Cada busca traz até 20 candidatos, conforme o FDD-0004.

## Alternativas consideradas

- Soma ponderada de scores normalizados: exige calibrar pesos com os casos de teste.
- Busca só vetorial: perde a precisão de termos exatos.
- BM25 com extensão: dependência extra, sem ganho que justifique.

## Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]
- [[adr-0004-indice-vetorial-e-metrica]]
