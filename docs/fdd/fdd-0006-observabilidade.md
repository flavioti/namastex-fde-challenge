---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0006 — Observabilidade com LangSmith

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0002-integracao-langsmith]] |
| **Documentos relacionados** | [[rfc-0008-mascaramento-de-dados-pessoais]] · [[rfc-0009-juiz-e-regras-de-validacao]] · [[rfc-0011-avaliacao-e-testes]] · [[adr-0011-logging-json-padrao]] · [[adr-0017-metadados-de-trace-dicionario-unico]] · [[fdd-0003-mascaramento-de-dados-pessoais]] · [[fdd-0004-banco-e-migracoes]] · [[fdd-0005-agente]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve a configuração do LangSmith, a redação antes do envio, as chaves de metadado, as tags, o registro de feedback do juiz e os testes da integração.

## 1. Escopo

Cada turno do agente gera um trace no LangSmith, com a árvore de execução dos nós, as chamadas ao modelo e as chamadas à ferramenta de cotação. O juiz registra sua decisão como feedback do trace. A identificação do trace fica gravada na conversa.

Todo conteúdo enviado ao LangSmith passa pela redação de dados pessoais antes do envio. Se a redação falhar, o trace não é enviado.

## 2. Stack e dependências

| Item | Escolha | Referência |
| --- | --- | --- |
| SDK de tracing | `langsmith`, na versão do lock | [[rfc-0002-integracao-langsmith]] |
| Integração com o LangChain | Tracing nativo, ativado por variável de ambiente | [[adr-0007-cliente-modelo-chatanthropic]] |
| Redação antes do envio | Função passada ao cliente do LangSmith | [[rfc-0008-mascaramento-de-dados-pessoais]] |
| Chaves de metadado | Dicionário único | [[adr-0017-metadados-de-trace-dicionario-unico]] |
| Logs | `logging` padrão, em JSON | [[adr-0011-logging-json-padrao]] |

## 3. Configuração

| Variável | Origem | Valor |
| --- | --- | --- |
| `LANGSMITH_API_KEY` | `.env` | Chave da conta gratuita e pública |
| `LANGSMITH_TRACING` | `.env` ou código de execução | `true` na demonstração e na avaliação. `false` nos testes |
| `LANGSMITH_PROJECT` | Constante do módulo | `autoseguro-mvp` |

A chave nunca é gravada em log nem em trace. O módulo de configuração não expõe o valor da chave em nenhuma representação.

## 4. Estrutura de arquivos

```
autoseguro/
  observabilidade/
    __init__.py
    config.py        leitura da configuração e do modo de execução
    chaves.py        dicionário único de chaves de metadado e de tags
    redacao.py       função de redação aplicada antes do envio
    cliente.py       construção do cliente do LangSmith com a redação
    feedback.py      registro da decisão do juiz como feedback
tests/
  observabilidade/
    test_redacao.py
    test_chaves.py
    test_feedback.py
    test_envio.py
```

## 5. Chaves de metadado e tags

Todas as chaves vêm de `chaves.py`. Nenhuma etapa cria uma chave fora desse módulo, conforme a [[adr-0017-metadados-de-trace-dicionario-unico]].

| Chave | Valor | Onde aparece |
| --- | --- | --- |
| `conversa_id` | UUID da conversa | Metadado do turno |
| `versao_prompt` | Versão do roteiro usado | Metadado de cada chamada ao modelo |
| `modelo` | Identificador exato do modelo | Metadado de cada chamada ao modelo |
| `etapa` | Nome do nó do grafo | Metadado de cada nó |
| `tipo_execucao` | Uma das tags da seção 6 | Metadado do turno |

**Tags**

| Tag | Quando |
| --- | --- |
| `teste` | Execuções dos testes e de desenvolvimento |
| `demonstracao` | Conversas feitas na interface simulada |
| `avaliacao` | Execuções das rodadas da [[rfc-0011-avaliacao-e-testes]] |

A tag é definida pelo ponto de entrada da execução. A interface define `demonstracao`, e a rodada de avaliação define `avaliacao`.

## 6. Redação antes do envio

A função `redacao.py` recebe o conteúdo de cada run antes do envio.

1. Entradas e saídas de texto são passadas por `mascarar_entrada` ou `mascarar_saida`, conforme a [[fdd-0003-mascaramento-de-dados-pessoais]].
2. Campos que contenham valores originais de CPF ou CEP, vindos do estado, são substituídos pelos marcadores. A verificação é por nome do campo e pelo conteúdo.
3. A função devolve o payload redigido. Nunca devolve o payload original.
4. Se a função lançar qualquer exceção, o run é descartado. Nenhum conteúdo do run é enviado, e um registro de erro é emitido pelo módulo de logs, sem o conteúdo do run.

O cliente é construído em `cliente.py` com a função de redação aplicada às entradas e às saídas de cada run.

## 7. Vínculo entre conversa e trace

Na primeira execução de um turno, o identificador do trace raiz é gravado em `registro.referencias_trace`, junto com a conversa, conforme a [[fdd-0004-banco-e-migracoes]]. Nos turnos seguintes, a referência é reaproveitada, e não é regravada.

Se a gravação da referência falhar, o turno segue normalmente. A falha é registrada em log, sem o conteúdo do turno.

## 8. Feedback do juiz

Cada decisão do juiz gera um feedback no trace do turno, em `feedback.py`.

| Chave do feedback | Pontuação | Comentário |
| --- | --- | --- |
| `juiz_regra_1` | 1 se os valores são oficiais, 0 se não | Motivo curto, sem valor |
| `juiz_regra_2` a `juiz_regra_4` | 1 se aprovado, 0 se reprovado | Motivo curto, sem valor |
| `juiz_decisao` | 1 se aprovado, 0 se reprovado | Regra violada, se houver |

O comentário nunca contém valor de preço, CPF nem CEP. O motivo é o código da regra e uma frase curta, vinda da saída do juiz.

Se a gravação do feedback falhar, a decisão do juiz continua válida para a conversa. A falha é registrada em log.

## 9. Pontos de envio e independência

- O envio dos traces é assíncrono. O agente não espera o envio para responder ao lead.
- Uma falha no envio não altera a resposta enviada ao lead, nem o status da conversa.
- O tempo de envio não entra no tempo de resposta do turno.

## 10. Custo

Os traces guardam, para cada chamada ao modelo, a contagem de tokens de entrada e saída. A soma por turno é gravada em `tokens_consumidos` do estado, conforme a [[fdd-0005-agente]]. O custo em dinheiro é calculado a partir dessas contagens, por modelo, e acompanhado por agente e juiz, conforme a [[rfc-0005-modelo-llm-e-apis-externas]].

## 11. Logs

Cada tentativa de envio gera um registro de log, em JSON, com:

- nível, horário em UTC e evento;
- identificador da conversa;
- resultado do envio: enviado, descartado por falha de redação, ou falha de envio;
- número de runs envolvidos.

O log nunca contém conteúdo de run.

## 12. Testes

Os testes não enviam nada ao LangSmith. O cliente é substituído por um dublê que captura os payloads.

| Arquivo | O que verifica |
| --- | --- |
| `test_redacao.py` | Nenhum CPF, CEP, e-mail, telefone ou placa aparece no payload redigido. Falha da redação resulta em descarte |
| `test_chaves.py` | As chaves usadas nas etapas existem no dicionário, e nenhuma chave fora dele é usada |
| `test_feedback.py` | Cada regra do juiz gera a pontuação e o comentário esperados, sem valor |
| `test_envio.py` | Falha do envio não altera a resposta ao lead nem o status da conversa |

**Casos de redação**

- Texto com CPF, CEP e telefone, na entrada: os três aparecem como marcadores.
- Resposta com valor de preço: o valor permanece, porque não é dado pessoal.
- Payload com exceção na redação: o run não é enviado, e o log não contém o conteúdo.
- Execução com `LANGSMITH_TRACING` igual a `false`: nenhum payload é capturado.

## 13. Critérios de aceite técnicos

1. Nenhum payload enviado ao LangSmith contém CPF, CEP, e-mail, telefone ou placa em texto.
2. Nenhum payload enviado contém o valor original de CPF ou CEP do estado.
3. Quando a redação falha, nenhum conteúdo do run é enviado.
4. A chave do LangSmith não aparece em log, trace nem mensagem de erro.
5. Cada turno tem tag, `conversa_id` e `modelo` nos metadados.
6. A decisão do juiz é registrada como feedback, sem valor no comentário.
7. Falha do envio não altera a resposta enviada ao lead.

## 14. Decisões de descarte e feedback

- **Descarte de run.** Se a versão do SDK fixada não permitir descartar um run antes do envio, a própria aplicação bloqueia a chamada de rede quando a redação falha. A regra de falha fechada se mantém, sem depender de recurso do SDK.
- **Nomes do feedback.** As chaves `juiz_regra_1` a `juiz_regra_4` e `juiz_decisao` são mantidas, e ficam no módulo `chaves.py`.

## 15. Decisões relacionadas

- [[rfc-0002-integracao-langsmith]]: integração com o LangSmith.
- [[rfc-0008-mascaramento-de-dados-pessoais]]: regras de redação.
- [[rfc-0009-juiz-e-regras-de-validacao]]: decisões do juiz registradas como feedback.
- [[fdd-0005-agente]]: nós e turnos que geram os traces.
