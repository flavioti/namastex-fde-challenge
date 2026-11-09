---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0003 — Modelo de embeddings multilingual-e5-small, com 384 dimensões

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['A RFC-0004 exige um modelo local, multilíngue, de até cerca de 500 MB, que rode em CPU. O catálogo de regras é pequeno e em português.']

## Decisão

- Usar o modelo multilingual-e5-small para gerar os vetores dos trechos e das consultas.
- Vetores com 384 dimensões.
- A dimensão e o identificador do modelo ficam registrados em cada vetor, conforme a RFC-0004.

## Consequências

- Trocar de modelo exige recalcular o índice inteiro, o que está previsto na RFC-0004.
- A qualidade para termos técnicos do português deve ser confirmada nos casos de recuperação da RFC-0011.
- O modelo é baixado uma vez para o volume local, conforme a RFC-0012.

## Alternativas consideradas

- paraphrase-multilingual-MiniLM-L12-v2: também pequeno e com 384 dimensões, mas mais antigo.
- Medir os dois modelos nos casos de recuperação e escolher depois: fica como plano de contingência, se o e5 não atender.

## Decisões relacionadas

- [[rfc-0004-geracao-de-embeddings]]
- [[adr-0004-indice-vetorial-e-metrica]]
