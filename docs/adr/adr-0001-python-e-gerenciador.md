---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0001 — Python 3.12 e gerenciador uv com versões exatas no lock

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de criação dos ADRs |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

['O projeto precisa de uma versão de Python única para a aplicação e para o contêiner do serviço de cotação, que já usa Python 3.12. Também precisa de reprodutibilidade entre máquinas e ao longo do tempo.']

## Decisão

- Usar Python 3.12 em toda a aplicação, alinhado ao Dockerfile do quote-service.
- Gerenciar o ambiente com `uv`, a partir do `pyproject.toml`.
- Usar as versões exatas travadas no `uv.lock`. A aplicação roda com o lock.

## Consequências

- A máquina de desenvolvimento usa a mesma versão do contêiner de aplicação.
- Atualizações de biblioteca são deliberadas, feitas com regeneração do lock e nova rodada de testes.
- O contêiner do quote-service continua com pip, conforme a RFC-0012. Esse é o único ponto fora do lock, e é um risco aceito.

## Alternativas consideradas

- Python 3.14, versão encontrada na máquina: mais recente, mas com suporte de pacotes ainda incompleto.
- Faixas de versão no `pyproject`, com lock atualizado com frequência: menos previsível.

## Decisões relacionadas

- [[rfc-0012-ambiente-de-execucao]]
- [[rfc-0006-servico-de-cotacao]]
