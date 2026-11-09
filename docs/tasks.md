# Tarefas e pendências da implementação

Registro das dúvidas e decisões de implementação que não estavam explícitas nos documentos de design. Cada item diz o que foi feito e o que precisa de revisão. Ao final da implementação, o conjunto será revisado com o usuário.

Situação geral: 188 testes passam. Cobrem banco, mascaramento, cliente da cotação, catálogo, juiz, agente, observabilidade e interface. A carga do catálogo rodou com o modelo e5 real. O agente não foi executado contra a API da Anthropic, porque a chave fica no `.env` do usuário.

## Ambiente e banco (FDD-0004, RFC-0003, RFC-0012)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-01 | Versão do Postgres | Feito | `pgvector/pgvector:pg18` fixada no compose. A tag `pg19` não existe como imagem com pgvector no momento. | Sim, se houver imagem pg19 antes da entrega. |
| T-02 | Identificador do trecho | Feito | O trecho recebe UUID v5 derivado do identificador da regra. A carga faz upsert sem consultar outra coluna, e cada regra tem um trecho. | Sim. O FDD-0004 não prevê índice único em `regra_id`. Alternativa: migração 0005 com índice único. |
| T-03 | `.gitignore` e `.env.example` | Feito | A regra `.env.*` escondia o `.env.example`. Adicionada exceção `!.env.example`, porque a RFC-0012 exige o arquivo versionado. | Não. |
| T-04 | Dimensão de vetor errada | Feito | O tipo `vector(384)` recusa vetores de outra dimensão antes da restrição CHECK. O teste espera o erro do driver. | Não. |
| T-05 | Variáveis do compose | Feito | O serviço `banco` exige `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` no `.env`, documentadas no `.env.example`. | Confirmar que o `.env` local tem as três variáveis. |
| T-06 | Motivos de encaminhamento | Feito | Os motivos usados são os da FDD-0001, seção 7, mais "Falha do modelo", "Falha do juiz" e "Resposta reprovada pelo juiz" (ver T-19). | Sim, junto com T-19. |
| T-07 | Parâmetros do HNSW | Feito | Padrões do pgvector, conforme o ADR-0004. | Sim, depois dos casos de recuperação com o modelo real (T-10). |
| T-08 | Cache do modelo de embeddings | **Pendente de decisão** | O RFC-0004 prevê o modelo em `database/modelos`. A pasta `database/` foi criada pelo Docker como root, e o usuário não consegue gravar nela. Adicionada a variável `AUTOSEGURO_MODELOS`. A carga real rodou com o cache em `~/.cache/autoseguro/modelos`. | Sim. Opções: `sudo chown` em `database/`, ou aceitar outro caminho e atualizar a RFC-0004. |

## Catálogo e embeddings (FDD-0008, RFC-0004)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-09 | Carga real com o modelo e5 | Feito | Carga executada contra o banco de desenvolvimento: 3 planos, 12 regras e 12 trechos. A segunda execução não reembeda nada. | Não. |
| T-10 | Qualidade da busca com o modelo real | Pendente | Para "pro-rata" e "carência", o trecho certo fica em primeiro. Para "prêmio para motorista jovem de 19 anos", a faixa de 18 a 24 anos não aparece entre os três primeiros. | Sim. Criar os casos de recuperação do ADR-0004 e ajustar os textos ou o HNSW. |
| T-11 | Fonte da carga | Feito | A carga lê `quote-service/data/plans.json`. Preços são `Decimal`. | Não. |
| T-12 | Pro-rata na resposta da API | Feito | O FDD-0002 diz que `primeiro_pagamento_pro_rata` é `Decimal`. A API devolve um objeto com `valor_primeiro_pagamento`. O cliente extrai o valor. | Confirmar com a RFC-0006 se o objeto deve ser mantido. |
| T-13 | Ordem dos padrões de mascaramento | Feito | Cada padrão roda sobre o texto original, e um trecho já coberto por um padrão anterior não é casado de novo. O FDD diz "em sequência", com o mesmo resultado para os padrões atuais. | Não. |
| T-14 | Telefone com 11 dígitos sem separador | Aceito | `11912345678` casa com CPF, que vem antes na ordem, e sai como `[CPF]`. O dado sai mascarado, que é o objetivo do ADR-0020. | Não. |
| T-15 | Texto de exemplo nos roteiros | Feito | Os roteiros usam o CEP de exemplo 30130-000, para não coincidir com dados de teste. | Não. |

## Cliente da cotação (FDD-0002, RFC-0006)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-16 | Prazo total de 15 s e timeout | Feito | O prazo conta desde a primeira chamada. Esperas consomem o prazo. Quando o prazo acaba, os planos restantes viram `indisponivel` sem chamada. Timeout e erro de conexão são retentados, como 5xx. | Não. |

## Agente (FDD-0005, FDD-0001, FDD-0009)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-17 | Detecção de pedido de humano e de desistência | **Pendente** | Listas fixas de frases em `agente/nos.py` ("atendente", "humano", "vendedor"; "não quero mais", "desisto"). O FDD-0001 não define a detecção. | Sim. Pode ser substituída por classificação do modelo. |
| T-18 | Desvios no fluxo da cotação | Feito | Quando a cotação falha ou é recusada, o nó `cotacao` leva direto ao encaminhamento, sem passar pelo modelo para redigir. O FDD-0005 diz que o modelo redige sempre. Quando a cotação dá certo, o modelo apresenta os planos, como previsto. | Sim. Confirmar se a mensagem de recusa do roteiro serve. |
| T-19 | Motivos fora do FDD | Feito | "Falha do modelo", "Falha do juiz" e "Resposta reprovada pelo juiz" não estão nas listas do FDD-0001. O motivo "falha do juiz" segue o FDD-0009. | Sim. |
| T-20 | Interface pública do agente | Feito | O FDD-0005 fala em funções `turno` e `ler_estado`. Implementei uma classe `Agente` com esses dois métodos. | Não. |
| T-21 | CEP no painel | Feito | `ler_estado` devolve o CEP como `[CEP]`. O FDD-0005 pede a forma mascarada usada pelo painel. | Confirmar o formato desejado. |
| T-22 | Textos dos roteiros | **Pendente de revisão** | Os textos de `agente/roteiros.py` e as mensagens de encaminhamento foram redigidos pela implementação. | Sim, junto com o produto (João). |
| T-23 | Redação que falha | Feito, com desvio | O FDD-0006 pede descarte do run quando a redação falha. O SDK do LangSmith só oferece ocultação de entradas e saídas. Quando a redação falha, o run segue sem conteúdo, e nenhum dado pessoal sai. | Sim. |
| T-24 | Referência de trace na conversa | **Pendente** | O FDD-0006 pede gravar o identificador do trace raiz em `registro.referencias_trace`. O agente ainda não grava esse identificador. Os metadados e as tags já são enviados. | Sim. |
| T-25 | Tokens do juiz no teto | **Pendente** | O FDD-0005 soma tokens de agente e juiz. O cliente do juiz ainda não devolve o consumo, então só o agente conta no teto. | Sim. |
| T-26 | Tentativas em plano e consentimento | Feito | Resposta sem plano ou sem sim/não só repete a pergunta, e não conta como tentativa inválida. O FDD-0001 fala em dado inválido apenas para os quatro campos de coleta. | Confirmar. |
| T-27 | Lista de DDDs e nomes | Feito | Os nomes e DDDs ficam em `ui-app/leads.toml`, editável. | Não. |

## Juiz (FDD-0009)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-28 | Número com separador em texto de motivo | Aceito | A R1 verifica todo número com separador decimal. Um multiplicador como "1,6" no rascunho reprova a resposta. O roteiro proíbe citar multiplicadores, mas o risco fica registrado. | Sim, se aparecer nas rodadas. |

## Interface (FDD-0007)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-29 | Streamlit em produção | Feito | O servidor sobe e responde com HTTP 200 contra o banco real. Os testes usam `AppTest`. | Não. |
| T-30 | Caminho do `leads.toml` | Feito | O arquivo fica em `ui-app/leads.toml`, ao lado de `app.py`, conforme a estrutura do FDD. | Não. |

## Observabilidade (FDD-0006)

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-31 | Feedback do juiz no trace | Feito, sem ligação | `registrar_feedbacks` existe e é testado, mas ainda não é chamado pelo nó do juiz, porque o identificador do run não está disponível (ver T-24). | Sim, junto com T-24. |

## Execução ponta a ponta

| # | Item | Situação | Decisão tomada | Revisar |
| --- | --- | --- | --- | --- |
| T-32 | Execução com a API da Anthropic | **Pendente de verificação** | O agente foi testado com modelos substitutos. A chamada real depende de `ANTHROPIC_API_KEY` no `.env` do usuário, que não consultei. | Sim. Rodar a interface com `RESPONDEDOR=agente` e conferir uma conversa completa. |
| T-33 | README de execução e decisões | **Pendente** | O README atual é o enunciado do desafio. O README de execução e de decisões será escrito na revisão final. | Sim. |

## Pendências externas

| # | Item | Responsável | Situação |
| --- | --- | --- | --- |
| E-01 | Confirmação das regras de preço e elegibilidade da tabela de planos (PRD, seção 9). | AutoSeguro | Externa, a confirmar. Até lá, `plans.json` é a fonte de verdade. Não bloqueia a implementação. |
