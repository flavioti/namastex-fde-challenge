# CLAUDE.md

Guia de contexto para agentes de IA (e para humanos) trabalharem neste repositório.

## 1. O projeto

Este repo é um **desafio técnico take-home** da Namastex para a vaga de FDE (Forward Deployed Engineer) / AI Engineer. O cenário é fictício: a seguradora **AutoSeguro** atende leads de **veículo** pelo **WhatsApp**.

O objetivo é construir um **agente de IA** que:

1. Conversa com o lead, qualifica os dados e cota um plano chamando a API de cotação.
2. Decide quando resolve sozinho e quando encaminha para um humano, com critério explícito.
3. Não trava e não inventa preço quando a infraestrutura falha.

**Intenção:** este é um **MVP de uma aplicação real**. Priorize decisões de engenharia defensáveis, rastreabilidade e tratamento de falhas, não features extras.

## 2. Fase atual: implementação

A especificação (PRD, RFC, ADR, FDD e diagramas) foi revisada e aprovada em 2026-11-09. A implementação começa a partir dela. Cada componente segue o FDD correspondente, e nada é implementado fora do que os documentos aprovados descrevem.

Consequências:

- Não crie `ui-app/`, o serviço do agente nem o Postgres no `docker-compose.yml` antes de receber ordem explícita.
- Toda decisão de arquitetura vai para um documento em `docs/` antes de virar código.
- Os requisitos de regras de negócio ainda serão definidos nos design docs. Não invente regras.

## 3. Entregáveis do desafio (segundo o README)

- Agente que atende um lead de ponta a ponta: conversa, qualifica, cota e decide (resolve ou encaminha).
- Repositório público no GitHub com o código.
- README com como rodar e **as decisões tomadas e o porquê**.
- Log de uma execução completa, do início ao fim, com a cotação saindo.
- Pasta `ai-logs/` com as conversas com IAs exportadas. **Esses logs entram na avaliação.**

## 4. Artefatos existentes

| Caminho | Conteúdo |
|---|---|
| `README.md` | Enunciado completo do desafio e critérios de avaliação. |
| `quote-service/` | API mock de cotação em FastAPI (`POST /quote`, `GET /planos`, `GET /health`). Simula um sistema legado instável. |
| `quote-service/data/plans.json` | Planos, preços base e **regras de cotação**. Fonte de verdade para preços. |
| `dataset/conversations.parquet` | ~2.500 conversas sintéticas lead/vendedor, uma linha por mensagem. |
| `dataset/sample.jsonl` | Amostra legível de 3 conversas, gerada pelo script. |
| `dataset/DICIONARIO.md` | Esquema do parquet. |
| `scripts/generate_dataset.py` | Gera o dataset de forma reprodutível. |
| `docker-compose.yml` | Sobe a API de cotação na porta 8000. |
| `.env` | Chaves de API definidas manualmente pelo usuário. **Nunca leia, exiba ou commite este arquivo.** |
| `.claude/skills/system-design/` | Skill de geração de diagramas de system design (ver seção 9). |
| `.claude/settings.json` | Hooks do projeto: avisam sobre mudanças nos documentos e regeneram o system design. |
| `docs/rastreabilidade.md` | Histórico de alterações dos documentos de design. Fonte para as decisões da IA. |
| `.gitignore` | Ignora `.env`, chaves, `database/` e similares. Permite `ai-logs/`. |

Observação: o diretório de scripts se chama `scripts/`, não `script/`.

## 5. Arquitetura pretendida

Decisões já tomadas pelo usuário. Detalhes vão para RFC e ADR.

- **Orquestração:** LangGraph.
- **Observabilidade, otimização e validação:** LangSmith Cloud, conta gratuita e pública. O projeto não contém dados sensíveis, e o PII é mascarado antes de qualquer trace (ver abaixo).
- **LLM:** API da Anthropic. A chave vem do `.env`.
- **Interface de simulação:** `ui-app/` com Streamlit, na raiz. Simula as interações de WhatsApp e permite testar o sistema localmente. Só a chamada à LLM e o LangSmith são externos.
- **Persistência local:** PostgreSQL, na versão mais recente, no `docker-compose.yml` com volume persistente em `database/` na raiz. A pasta `database/` não é versionada.
- **Harness de dados (entrada do agente):** nós do LangGraph que mascaram PII antes de o agente processar a mensagem. Sempre que possível, a lógica é determinística em Python, com regex. Esse passo acontece na entrada, não em um pipeline separado.
- **Juiz (LLM-as-a-judge):** antes de devolver qualquer resposta ao usuário, um juiz valida as regras de negócio. As regras serão definidas nos design docs.
- **Rastreabilidade:** cada mensagem e cotação com id e status, gravados no Postgres.

### Regras de negócio da cotação (`plans.json`)

- **Faixa etária:** 18 a 24 anos com multiplicador 1,60; 25 a 29 com 1,25; 30 a 59 com 1,00; 60 a 75 com 1,40. Acima de 75 a cotação é recusada.
- **Idade do veículo:** 0 a 5 anos com 1,00; 6 a 10 com 1,15; 11 a 20 com 1,45. Mais de 20 anos é recusado.
- **Região:** CEP com prefixo de alto risco (`07`, `08`, `21`, `26`, `59`) recebe multiplicador 1,30.
- **Carência:** roubo e furto valem só após 30 dias da vigência.
- **Pro-rata:** se a vigência começa no meio do mês, o primeiro pagamento é proporcional aos dias restantes. Os meses seguintes são integrais.
- **Prêmio:** `base_mensal × faixa_etária × idade_veículo × região`.

## 6. API de cotação

### Endpoints

- `GET /health`: sempre estável.
- `GET /planos`: tabela de planos e regras.
- `POST /quote`: calcula a cotação.

Payload de `POST /quote`:

```json
{"plano_id": "completo", "idade": 35, "veiculo_ano": 2022, "cep": "01310-100", "data_inicio": "2026-07-15"}
```

- `plano_id` aceita `essencial`, `completo` ou `premium`. O padrão é `essencial`.
- `idade` e `veiculo_ano` são obrigatórios.
- `cep` e `data_inicio` (`YYYY-MM-DD`) são opcionais.

### Códigos de resposta

| Código | Significado | Tratamento esperado no agente |
|---|---|---|
| 200 | Cotação calculada | Apresentar ao lead. |
| 500, 502, 503 | Falha transitória (`upstream_unavailable`) | Retry com backoff e, se persistir, encaminhar ou informar o lead. **Nunca inventar preço.** |
| 422 | Cotação recusada (`cotacao_recusada`, com `motivo`) | Comunicar o motivo. Não é erro técnico. |
| 400 | Payload inválido (`payload_invalido`) | Corrigir o payload. Revisar o agente, não retentar às cegas. |

Comportamento de falha simulado:

- Cerca de 20% das chamadas falham com 5xx (`QUOTE_FAILURE_RATE`).
- Cerca de 10% das chamadas são lentas, com 8 segundos de espera (`QUOTE_SLOW_RATE`, `QUOTE_SLOW_SECONDS`). Use timeout no cliente.
- `QUOTE_SEED` torna as falhas reproduzíveis.

## 7. Dados e privacidade

- O dataset é **sintético**, mas contém dados pessoais no formato real: CPF, e-mail, telefone, placa e CEP.
- Trate esses dados como sensíveis no código e nos documentos, mesmo com a conta pública do LangSmith. O mascaramento acontece antes de qualquer envio ao LangSmith ou à LLM.
- `dataset/sample.jsonl` contém PII sem máscara. Não o trate como dado limpo.
- Os preços citados nas falas das conversas (ex.: R$ 129 a R$ 389) não batem com `plans.json`. Use **`plans.json` como fonte de verdade** para cotação.

## 8. Como trabalhar neste repo

- **Human-in-the-loop na fase de desenvolvimento assistido:** em qualquer dúvida, **pergunte no terminal** antes de seguir. Não invente requisitos nem decisões de produto ou arquitetura.
- **Human-in-the-loop na fase de execução do agente:** quando o agente gerar logs e métricas no LangSmith e for preciso avaliar ou analisar algo na ferramenta, **avise o usuário**.
- **Design docs:** a arquitetura segue system design apoiado em documentos (ver seção 9). Não implemente componentes grandes sem o documento aprovado.
- **Idioma:** documentação, comentários e mensagens de commit em **português**. Identificadores de domínio seguem o padrão do código existente (`cotar`, `premio_mensal`).
- **Não quebre o contrato da API:** o `quote-service` é externo ao agente. Não altere sua lógica para fazer o agente passar. Se precisar de mudança, pergunte.
- **Segredos:** nunca commitar `.env` ou chaves. Revise `ai-logs/` antes de commitar.
- **Decisões de design:** antes de propor ou decidir algo de arquitetura ou regra de negócio, consulte `docs/rastreabilidade.md` e os documentos citados. Se a informação não estiver lá, pergunte ao usuário em vez de presumir.
- **Commits:** só faça commit quando pedido.
- **Exportação de `ai-logs/`:** é feita **manualmente pelo usuário** quando o projeto estiver pronto. Não exporte nem gere essa pasta.

## 9. Documentação e system design

Estrutura prevista em `docs/`:

- `docs/prd/`: requisitos de produto.
- `docs/rfc/`: propostas técnicas em discussão.
- `docs/adr/`: decisões de arquitetura aceitas ou rejeitadas.
- `docs/fdd/`: design de funcionalidades.

Os diagramas de system design são gerados pela skill `.claude/skills/system-design/`, adaptada para este projeto. Ela produz dois artefatos a partir de `system-design/autoseguro-system-design.json`:

- `system-design/autoseguro-system-design-geral.html`: todos os documentos, aprovados e não aprovados.
- `system-design/autoseguro-system-design-aprovado.html`: só o que tem ADR aceito.

Os hooks em `.claude/settings.json` executam `aprovacoes.py` e `sincronizar.py` depois de cada `Edit`, `Write` ou `Bash` e a cada mensagem do usuário. Eles avisam quando um documento muda e regeneram os HTMLs.

O histórico de alterações e as decisões registradas ficam em `docs/rastreabilidade.md`. Consulte esse arquivo antes de tomar decisões de design.

## 10. Critérios de avaliação (resumo do README)

- Funciona de ponta a ponta, sem quebrar no caminho feliz.
- Comportamento claro quando `/quote` falha. Esse é o ponto que mais separa.
- Critério de encaminhamento para humano explícito e defensável.
- Rastreabilidade de cada mensagem e cotação.
- Cuidado com dados sensíveis.
- Qualidade: outro engenheiro entende o código e as decisões.
- Uso de IA demonstrado pelos `ai-logs/`.

## 11. Decisões resolvidas

1. Modelos: agente `claude-haiku-5-5` e juiz `claude-opus-5-5`, com IDs fixos e configurados no código. Ver [[adr-0007-cliente-modelo-chatanthropic]] e [[rfc-0005-modelo-llm-e-apis-externas]].
2. Regras do juiz: R1 em código e R2 a R4 pelo modelo. Ver [[rfc-0009-juiz-e-regras-de-validacao]] e [[fdd-0009-juiz]].
3. Avaliação no LangSmith: rodada manual antes de cada entrega, com casos de conversa e rotulagem humana em amostra. Ver [[rfc-0002-integracao-langsmith]] e [[rfc-0011-avaliacao-e-testes]].

Pendência externa, sem bloquear a implementação: a confirmação das regras de preço pela AutoSeguro. Até lá, `quote-service/data/plans.json` é a fonte de verdade. Ver a seção 9 do [[prd-0001-agente-de-cotacao]].
