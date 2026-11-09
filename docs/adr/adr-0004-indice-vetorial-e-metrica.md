---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0004 — Índice HNSW com distância cosseno no pgvector

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['A busca vetorial precisa ser rápida o bastante para a conversa e manter boa precisão. A métrica deve ser adequada a embeddings de texto.']

## Decisão

- Criar um índice HNSW sobre a coluna de vetores dos trechos.
- Usar distância cosseno como métrica de similaridade.

## Consequências

- Parâmetros do índice HNSW são ajustados na implementação, com os casos de recuperação.
- A consulta usa o mesmo operador de distância que o índice, para que o índice seja aproveitado.

## Alternativas consideradas

- Busca exata, sem índice: simples e precisa para um catálogo pequeno. Fica como alternativa caso o HNSW cause problemas.
- IVFFlat: exige escolher listas e refazer quando o catálogo cresce.
- Produto interno: só equivale ao cosseno com vetores normalizados, o que exige cuidado a mais.

## Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]
- [[adr-0003-modelo-de-embeddings]]
- [[adr-0005-busca-hibrida-rrf]]
