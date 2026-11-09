---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0017 — Metadados de trace em chaves fixas definidas em um dicionário único

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['Os traces precisam ser filtrados por versão de prompt, modelo, conversa e etapa. Nomes divergentes entre etapas tornam a análise falha.']

## Decisão

- Definir todas as chaves de metadado em um único módulo do projeto.
- Toda etapa do grafo usa as chaves desse módulo, sem criar nomes novos.
- As chaves incluem identificador da conversa, versão do prompt, modelo, etapa e tipo de avaliação.

## Consequências

- Filtros no LangSmith funcionam com nomes estáveis entre rodadas.
- Incluir uma chave nova exige alterar o módulo, o que é intencional.

## Alternativas consideradas

- Chaves livres em cada etapa: mais rápido de escrever, mas dificulta filtrar os traces.

## Decisões relacionadas

- [[rfc-0002-integracao-langsmith]]
- [[adr-0011-logging-json-padrao]]
