---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0005 — Agente: estado, grafo e nós

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0007-agente-langgraph-langchain]] |
| **Documentos relacionados** | [[rfc-0005-modelo-llm-e-apis-externas]] · [[rfc-0006-servico-de-cotacao]] · [[rfc-0008-mascaramento-de-dados-pessoais]] · [[rfc-0009-juiz-e-regras-de-validacao]] · [[adr-0005-busca-hibrida-rrf]] · [[adr-0006-estado-do-grafo-pydantic]] · [[adr-0007-cliente-modelo-chatanthropic]] · [[adr-0013-teto-tokens-e-encaminhamento]] · [[adr-0015-ferramenta-cotacao-schema-pydantic]] · [[adr-0017-metadados-de-trace-dicionario-unico]] · [[fdd-0001-fluxo-de-conversa-e-coleta]] · [[fdd-0002-cliente-da-cotacao]] · [[fdd-0003-mascaramento-de-dados-pessoais]] · [[fdd-0004-banco-e-migracoes]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve o estado do grafo, cada nó, as arestas condicionais, a integração com o modelo e com o juiz, e os testes do agente.

## 1. Escopo

O agente conduz uma conversa de cotação, turno a turno. A cada mensagem do lead, o grafo executa as etapas de entrada, coleta, cotação, juiz, resposta e, quando for o caso, encaminhamento ou encerramento. O estado é gravado a cada etapa, no esquema `agente`.

O modelo conduz a conversa e decide quando chamar a ferramenta de cotação. A aplicação controla as transições, valida cada dado, executa a cotação e decide se a resposta pode ser enviada.

## 2. Stack e dependências

| Item | Escolha | Referência |
| --- | --- | --- |
| Orquestração | LangGraph, com `StateGraph` | [[rfc-0007-agente-langgraph-langchain]] |
| Checkpoint | `PostgresSaver`, no esquema `agente` | [[fdd-0004-banco-e-migracoes]] |
| Modelo do agente | `ChatAnthropic` com `claude-haiku-5-5` | [[adr-0007-cliente-modelo-chatanthropic]] |
| Modelo do juiz | `ChatAnthropic` com `claude-opus-5-5` | [[rfc-0009-juiz-e-regras-de-validacao]] |
| Estado | Pydantic v2 | [[adr-0006-estado-do-grafo-pydantic]] |
| Ferramenta | Função Python, descrita por schema Pydantic | [[adr-0015-ferramenta-cotacao-schema-pydantic]] |
| Cliente da cotação | `CotacaoClient` | [[fdd-0002-cliente-da-cotacao]] |
| Mascaramento | `mascarar_entrada` e `mascarar_saida` | [[fdd-0003-mascaramento-de-dados-pessoais]] |
| Tracing | Metadados com chaves do dicionário único | [[adr-0017-metadados-de-trace-dicionario-unico]] |

As versões de LangGraph e LangChain são as do `uv.lock`. A temperatura dos dois modelos é 0, conforme a [[rfc-0005-modelo-llm-e-apis-externas]].

## 3. Estrutura de arquivos

```
autoseguro/
  agente/
    __init__.py
    estado.py          modelo Pydantic do estado
    grafo.py           montagem do StateGraph, arestas e checkpoint
    llm.py             instâncias de ChatAnthropic para agente e juiz
    ferramentas.py     descrição e execução da ferramenta de cotação
    roteiros.py        textos fixos de cada etapa, com o dado pedido
    coleta_valores.py  extração determinística de cada campo
    resumo.py          resumo acumulado do histórico
    nos/
      entrada.py
      coleta.py
      cotacao.py
      juiz.py
      resposta.py
      encaminhamento.py
      encerramento.py
tests/
  agente/
    test_estado.py
    test_coleta_valores.py
    test_nos.py
    test_grafo.py
```

### Interface pública do agente

O módulo `autoseguro/agente` expõe duas funções, usadas pela interface e pelos testes:

- `turno(conversa_id: UUID, texto: str) -> RespostaTurno`. Executa o grafo para uma mensagem do lead. `RespostaTurno` traz o texto do agente, já mascarado, o status resultante e o indicador de encaminhamento.
- `ler_estado(conversa_id: UUID) -> EstadoLeitura`. Lê o estado do checkpoint, sem executar o grafo. `EstadoLeitura` traz os dados coletados sem o CPF, o último resultado de cotação, o status e o motivo de encaminhamento.

Nenhuma das duas funções expõe o CPF original ou o CEP original. O CEP aparece apenas na forma usada pelo painel, mascarada.

## 4. Estado

O estado é um modelo Pydantic, `EstadoConversa`, com os campos abaixo.

| Campo | Tipo | Observação |
| --- | --- | --- |
| `conversa_id` | UUID | Igual ao `thread_id` do checkpoint |
| `mensagens` | lista de `Mensagem` | Texto já mascarado, com papel e ordem |
| `resumo` | texto, opcional | Resumo acumulado das mensagens antigas |
| `dados` | `DadosColeta` | Valores originais, usados pela cotação e pelo encaminhamento |
| `tentativas` | dicionário campo para inteiro | Dado inválido por campo, até duas novas tentativas |
| `cotacao` | `ResultadoCotacao`, opcional | Resultado da última cotação |
| `rascunho` | texto, opcional | Resposta candidata aguardando o juiz |
| `reescritas` | inteiro | Número de reescritas feitas no turno, máximo 1 |
| `status` | `em_andamento`, `cotada`, `encaminhada` ou `encerrada` | Igual à [[fdd-0001-fluxo-de-conversa-e-coleta]] |
| `motivo_encaminhamento` | texto, opcional | Um dos motivos da FDD-0001 |
| `tokens_consumidos` | inteiro | Soma de entrada e saída de agente e juiz |

**`DadosColeta`**

| Campo | Tipo | Origem |
| --- | --- | --- |
| `idade` | inteiro, opcional | Lead, validado por `coleta_valores` |
| `ano_veiculo` | inteiro, opcional | Lead, validado por `coleta_valores` |
| `cep` | texto, opcional | Valor original, nunca o marcador |
| `data_inicio` | data, opcional | Lead, validada por `coleta_valores` |
| `plano_escolhido` | texto, opcional | Lead, dentre os três planos |
| `consentimento_cpf` | booleano, opcional | Resposta do lead ao pedido de consentimento |
| `cpf` | texto, opcional | Valor original, sem máscara |

Valores originais de CEP e CPF ficam no estado e no checkpoint, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]]. O modelo nunca recebe esses valores. O esquema `agente` é local, e a regra vale para todos os seus dados.

## 5. Grafo

O grafo é montado uma vez, em `grafo.py`, e compilado com o checkpoint `PostgresSaver`. Cada turno é uma execução do grafo com `thread_id` igual a `conversa_id`.

**Nós**

| Nó | Função |
| --- | --- |
| `entrada` | Mascara a mensagem do lead e extrai os valores originais detectados |
| `coleta` | Decide o próximo campo, valida a resposta e gera a pergunta pelo roteiro |
| `cotacao` | Executa a ferramenta quando o modelo a chama, e devolve o resultado ao modelo |
| `juiz` | Verifica o rascunho antes do envio |
| `resposta` | Grava a mensagem do agente e encerra o turno |
| `encaminhamento` | Registra o motivo e a mensagem final do roteiro |
| `encerramento` | Registra o status encerrada |

**Arestas**

| De | Para | Condição |
| --- | --- | --- |
| `entrada` | `coleta` | Sempre |
| `coleta` | `cotacao` | O modelo chamou a ferramenta |
| `coleta` | `juiz` | Há rascunho que cita valor ou recusa |
| `coleta` | `resposta` | Há rascunho sem valor nem recusa |
| `coleta` | `encaminhamento` | Gatilho da FDD-0001 acionado |
| `coleta` | `encerramento` | Lead desistiu, ou 30 minutos sem resposta |
| `cotacao` | `coleta` | Sempre, para o modelo redigir com o resultado |
| `juiz` | `resposta` | Aprovado |
| `juiz` | `coleta` | Reprovado e `reescritas` menor que 1 |
| `juiz` | `encaminhamento` | Reprovado e `reescritas` igual a 1, ou falha do juiz |
| `resposta` | `fim` | Sempre |
| `encaminhamento` | `fim` | Sempre |
| `encerramento` | `fim` | Sempre |

O nó `coleta` é o único que chama o modelo do agente. O nó `juiz` é o único que chama o modelo do juiz.

**Decisões da revisão.** Quando a cotação é recusada ou falha, o nó `cotacao` leva direto ao encaminhamento, sem o modelo redigir a resposta, porque a mensagem é fixa e não cita valores. O pedido de humano e a desistência são detectados por listas fixas de frases.

**Teto de tokens (decisão da implementação).** O consumo do modelo do juiz entra no mesmo teto do agente, por decisão de revisão.

## 6. Nó entrada

1. Recebe a mensagem original do lead.
2. Chama `detectar`, do módulo de mascaramento, para obter os achados e seus valores originais.
3. Guarda o CPF e o CEP detectados em `dados`, apenas se o campo pendente for esse.
4. Chama `mascarar_entrada` e grava a mensagem mascarada em `mensagens`.
5. Verifica o teto de tokens. Se `tokens_consumidos` for igual ou maior que 50 mil, define o gatilho de teto de tokens e segue para `encaminhamento`, conforme a [[adr-0013-teto-tokens-e-encaminhamento]].
6. Se `mensagens` tiver mais de 20 mil tokens estimados, chama `resumo.py`, que gera o resumo acumulado com o modelo do agente, mantendo as últimas mensagens literais.

## 7. Nó coleta

**Ordem dos campos.** Os campos são pedidos nesta ordem: idade, ano do veículo, CEP, data de início. Depois da cotação, o CPF é pedido quando há um plano escolhido.

**Extração determinística.** `coleta_valores.py` extrai cada campo da mensagem do lead por código, sem o modelo:

| Campo | Regra |
| --- | --- |
| Idade | Inteiro entre 1 e 120 |
| Ano do veículo | Inteiro de quatro dígitos entre 1950 e o ano atual |
| CEP | Oito dígitos, com ou sem hífen |
| Data de início | Formato dia, mês e ano, não anterior a hoje, no fuso de Brasília |
| CPF | Onze dígitos, com ou sem pontuação |

Se a extração falhar, o contador de `tentativas` do campo aumenta. Isso inclui respostas em texto livre, como "tenho uns 35", em que o número não é reconhecido. Até duas novas tentativas são pedidas pelo roteiro. Na terceira falha, o gatilho de dado inválido é acionado.

**Roteiro.** Cada etapa tem um roteiro fixo em `roteiros.py`, com o dado pedido, o formato e um exemplo. O modelo recebe o roteiro no prompt do sistema e escreve a pergunta, sem alterar o dado pedido.

**Ferramenta.** Quando os quatro dados estão completos e válidos, o modelo recebe a ferramenta de cotação com a descrição do schema. O modelo decide quando chamá-la. A aplicação preenche os argumentos a partir de `dados`, incluindo o CEP original.

**Temperatura e modelo.** O modelo do agente é `claude-haiku-5-5`, com temperatura 0 e chamadas com tentativas conforme a [[rfc-0005-modelo-llm-e-apis-externas]].

## 8. Nó cotação

1. Monta `DadosCotacao` a partir de `dados`.
2. Chama `CotacaoClient.cotar`, que faz as três chamadas, uma por plano.
3. Grava o resultado em `cotacao`.
4. Se o resultado for `sucesso`, o status passa a `cotada`.
5. Se o resultado for `recusada`, ou `indisponivel`, ou `payload_invalido`, o motivo é registrado para o nó `coleta` redigir a resposta com o roteiro correspondente.
6. Devolve ao modelo, como resultado da ferramenta, apenas os planos e os motivos. O CEP e o CPF não entram nesse retorno.

## 9. Nó juiz

1. Recebe o `rascunho`, o `cotacao` e o `status`.
2. Aplica a regra R1 em código: cada valor citado no rascunho precisa existir no resultado da cotação, comparado como `Decimal`.
3. Chama o modelo do juiz, `claude-opus-5-5`, com as regras R2, R3 e R4 do [[rfc-0009-juiz-e-regras-de-validacao]].
4. A saída do modelo é um objeto Pydantic com `aprovado`, `regra` e `motivo`.
5. Se qualquer regra reprovar, a decisão é reprovada e o motivo é guardado.
6. Se a chamada ao juiz falhar após três tentativas, a decisão é reprovada com o motivo de falha do juiz.

O juiz só é chamado para rascunhos que citam valor ou recusa. Rascunhos apenas de coleta passam direto para `resposta`.

## 10. Nó resposta

Grava `rascunho` em `mensagens`, como mensagem do agente, depois de passar pela `mascarar_saida`. Limpa `rascunho` e `reescritas`. Ao fim, o turno termina.

Se o juiz tiver reprovado uma vez e aprovado na reescrita, a mensagem enviada é a reescrita, e a primeira reprovação fica registrada nos traces.

## 11. Nós encaminhamento e encerramento

**Encaminhamento.** Grava `motivo_encaminhamento` e `status` igual a `encaminhada`. Cria o registro de encaminhamento com o motivo, o resumo e o CPF original, se houver, conforme a [[fdd-0004-banco-e-migracoes]]. Envia a mensagem final do roteiro e encerra o turno. Nenhuma resposta do agente é gerada depois disso.

**Encerramento.** Grava `status` igual a `encerrada`, sem mensagem final. A regra de quando encerrar está na [[fdd-0001-fluxo-de-conversa-e-coleta]].

## 12. Erros

| Situação | Tratamento |
| --- | --- |
| API do modelo falha após três tentativas | Encaminhamento, com motivo de falha do modelo |
| Juiz falha após três tentativas | Reprovação, e encaminhamento sem envio do rascunho |
| Cotação indisponível | Resposta do roteiro e encaminhamento |
| Teto de tokens atingido | Encaminhamento com motivo de limite |
| Erro inesperado de código | Mensagem neutra, registro do erro, conforme a [[rfc-0010-contrato-interface-agente]] |

Nenhum dos erros acima envia preço ao lead.

## 13. Traces e logs

Cada nó grava, nos traces, as chaves do dicionário único da [[adr-0017-metadados-de-trace-dicionario-unico]]: identificador da conversa, versão do prompt, modelo, etapa e tipo de execução. Os textos enviados aos traces são os mascarados. Os logs seguem a [[adr-0011-logging-json-padrao]].

## 14. Testes

Os testes não chamam a API real. Os modelos são substituídos por dublês que devolvem respostas roteirizadas, e a cotação é substituída por um `httpx.MockTransport`.

| Arquivo | O que verifica |
| --- | --- |
| `test_estado.py` | Valores válidos e inválidos de cada campo do estado |
| `test_coleta_valores.py` | Cada regra de extração, com casos aceitos e recusados |
| `test_nos.py` | Cada nó isolado, com entrada e saída esperadas |
| `test_grafo.py` | Caminhos completos do grafo, de ponta a ponta |

**Caminhos do grafo que devem ser testados**

- Cotação completa, com três planos e escolha de plano.
- Recusa por regra da cotação.
- Falha persistente da cotação.
- Pedido do lead para falar com humano.
- Recusa do consentimento do CPF, com a cotação já registrada.
- Três respostas inválidas seguidas para um campo.
- Juiz reprova o rascunho uma vez e aprova a reescrita.
- Juiz reprova a reescrita, e a conversa é encaminhada.
- Falha do juiz após três tentativas.
- Teto de tokens atingido.

## 15. Critérios de aceite técnicos

1. O grafo é compilado com checkpoint em `PostgresSaver`, no esquema `agente`.
2. Nenhuma chamada ao modelo recebe CEP ou CPF originais.
3. A ferramenta de cotação só é executada com dados completos e válidos.
4. Nenhum rascunho com valor sem aprovação de R1 chega à resposta.
5. Nenhuma resposta é enviada depois do encaminhamento.
6. Todos os caminhos da seção 14 passam sem chamada de rede.

## 16. Decisões de ferramenta e extração

- **Ferramenta sem parâmetros.** O modelo vê a ferramenta de cotação sem campos. A aplicação preenche os argumentos a partir do estado.
- **Texto livre.** A extração não interpreta texto livre. Uma resposta que não contém o dado no formato esperado conta como tentativa inválida, e o lead é pedido de novo.

## 17. Decisões relacionadas

- [[rfc-0007-agente-langgraph-langchain]]: arquitetura do agente.
- [[fdd-0001-fluxo-de-conversa-e-coleta]]: regras de coleta, tentativas e encaminhamento.
- [[fdd-0002-cliente-da-cotacao]]: cliente que executa a cotação.
- [[fdd-0003-mascaramento-de-dados-pessoais]]: mascaramento de entrada e saída.
- [[fdd-0004-banco-e-migracoes]]: checkpoint e registro de encaminhamentos.
