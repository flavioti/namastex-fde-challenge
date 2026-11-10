---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0002 — Cliente da cotação

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[fdd-0001-fluxo-de-conversa-e-coleta]] |
| **Documentos relacionados** | [[rfc-0006-servico-de-cotacao]] · [[rfc-0005-modelo-llm-e-apis-externas]] · [[adr-0001-python-e-gerenciador]] · [[adr-0008-cliente-http-cotacao]] · [[adr-0010-valores-monetarios-decimal]] · [[adr-0011-logging-json-padrao]] · [[adr-0015-ferramenta-cotacao-schema-pydantic]] · [[adr-0016-biblioteca-de-testes-pytest]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve arquivos, contratos, comportamento de cada resposta, configuração e testes do cliente que chama o serviço de cotação.

## 1. Escopo

O cliente é o único módulo da aplicação que chama o serviço de cotação. Ele recebe os dados já validados pela conversa, chama o serviço para cada um dos três planos e devolve um resultado tipado para o agente.

O cliente não valida regras de negócio. Idade fora da faixa, veículo antigo e região de risco são decididos pelo serviço, e o cliente apenas os traduz em resultado.

## 2. Stack e dependências

| Item | Escolha | Referência |
| --- | --- | --- |
| Linguagem | Python 3.12 | [[adr-0001-python-e-gerenciador]] |
| Gerenciador | uv, com versões exatas no `uv.lock` | [[adr-0001-python-e-gerenciador]] |
| Cliente HTTP | httpx, síncrono | [[adr-0008-cliente-http-cotacao]] |
| Modelos de dados | Pydantic v2 | [[adr-0015-ferramenta-cotacao-schema-pydantic]] |
| Valores monetários | `decimal.Decimal`, duas casas | [[adr-0010-valores-monetarios-decimal]] |
| Logs | `logging` padrão, saída em JSON | [[adr-0011-logging-json-padrao]] |
| Testes | pytest, com `httpx.MockTransport` | [[adr-0016-biblioteca-de-testes-pytest]] |

Não há SDK externo neste módulo. O cliente não depende do LangChain nem do LangGraph, para que possa ser testado isoladamente.

## 3. Estrutura de arquivos

```
autoseguro/
  cotacao/
    __init__.py      exporta a interface pública do módulo
    config.py        URL base e constantes de timeout e retry
    modelos.py       modelos Pydantic de entrada e de resultado
    erros.py         exceções internas de transporte
    cliente.py       CotacaoClient: chamadas HTTP, retry e mapeamento
tests/
  cotacao/
    test_modelos.py
    test_cliente.py
```

## 4. Configuração

| Item | Origem | Valor padrão |
| --- | --- | --- |
| URL base do serviço | Variável `COTACAO_BASE_URL`, no `.env` | `http://localhost:8000` |
| Timeout por tentativa | Constante em `config.py` | 5 segundos |
| Prazo total da cotação | Constante em `config.py` | 15 segundos, para as três chamadas e retentativas |
| Número de tentativas | Constante em `config.py` | 3 |
| Esperas entre tentativas | Constante em `config.py` | 0,5 s e depois 1 s |
| Jitter | Não existe | Esperas fixas |

As constantes de timeout, tentativas e esperas ficam em código, e não no `.env`. Assim, os testes sempre rodam com os mesmos valores.

## 5. Modelos de dados

**Entrada, `CotacaoEntrada`**

| Campo | Tipo | Observação |
| --- | --- | --- |
| `plano_id` | literal `essencial`, `completo` ou `premium` | Definido pelo cliente, um por chamada |
| `idade` | inteiro | Já validado pela conversa |
| `veiculo_ano` | inteiro | Já validado pela conversa |
| `cep` | texto | Valor original do estado, nunca o marcador |
| `data_inicio` | data no formato `YYYY-MM-DD` | Obrigatória para a cotação |

O CEP vem do estado da conversa, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]]. O modelo de linguagem não participa dessa montagem.

**Resultado de um plano, `PlanoCotado`**

| Campo | Tipo |
| --- | --- |
| `plano_id` | texto |
| `plano_nome` | texto |
| `premio_mensal` | `Decimal`, duas casas |
| `franquia` | `Decimal`, duas casas |
| `coberturas` | lista de textos |
| `carencia_dias` | inteiro |
| `primeiro_pagamento_pro_rata` | `Decimal` ou ausente |

Os valores numéricos da resposta, que chegam como número de ponto flutuante, são convertidos com `Decimal(str(valor))`, arredondados para duas casas em `ROUND_HALF_UP`. A conversão é feita na entrada do módulo.

**Resultado da cotação, `ResultadoCotacao`**

Uma união de quatro casos, com `tipo` como discriminador:

| `tipo` | Campos | Quando ocorre |
| --- | --- | --- |
| `sucesso` | `planos`: lista com os três `PlanoCotado` | Os três planos foram cotados |
| `recusada` | `motivo`: texto | Regra de negócio recusou a cotação |
| `indisponivel` | `motivo`: texto curto | Falha persistente após as tentativas |
| `payload_invalido` | `detalhe`: texto | O serviço rejeitou o formato |

O cliente devolve o resultado. Não lança exceção para casos previstos. Exceções ficam reservadas a erros de programação.

## 6. Interface pública

```
CotacaoClient(base_url, transporte=None, sleep=time.sleep)
    cotar(entrada: DadosCotacao) -> ResultadoCotacao
```

- `DadosCotacao` contém idade, ano, CEP e data de início, sem o plano.
- `cotar` chama o serviço três vezes, uma para cada plano, em sequência.
- O argumento `transporte` existe para os testes, que passam um `httpx.MockTransport`.
- O argumento `sleep` existe para os testes, que substituem a espera por uma função que apenas registra as chamadas.

**Agregação dos três planos**

- Se os três planos retornarem sucesso, o resultado é `sucesso`.
- Se qualquer plano retornar `recusada`, o resultado é `recusada`. A recusa é por idade ou veículo, e não depende do plano.
- Se qualquer plano retornar `indisponivel`, o resultado é `indisponivel`, e os demais planos já obtidos não são exibidos.
- Se qualquer plano retornar `payload_invalido`, o resultado é `payload_invalido`.

A ordem de prioridade é `payload_invalido`, depois `recusada`, depois `indisponivel`. Um erro de payload indica bug, e deve aparecer antes de qualquer outra situação.

## 7. Mapeamento das respostas HTTP

| Situação | Ação | Resultado |
| --- | --- | --- |
| 200 | Converte o corpo nos modelos de plano | `sucesso` |
| 422 com `error` igual a `cotacao_recusada` | Lê `motivo` | `recusada` |
| 422 no formato de validação do FastAPI, com `detail` | Não retenta | `payload_invalido` |
| 400 com `error` igual a `payload_invalido` | Não retenta | `payload_invalido` |
| 500, 502 ou 503 | Retenta | `indisponivel` se esgotar |
| Timeout de 5 segundos | Retenta | `indisponivel` se esgotar |
| Erro de conexão | Retenta | `indisponivel` se esgotar |
| Qualquer outro status | Não retenta | `indisponivel`, com log de status inesperado |
| Corpo que não é JSON válido em 200 | Não retenta | `indisponivel`, com log de resposta malformada |

A distinção entre os dois 422 é feita pelo corpo, conforme a [[rfc-0006-servico-de-cotacao]].

## 8. Retry

- Há até três tentativas por plano.
- Entre a primeira e a segunda tentativa, espera 0,5 segundo. Entre a segunda e a terceira, espera 1 segundo.
- As esperas são feitas pela função `sleep` injetada. Nenhuma espera acontece nos testes.
- Só erros transitórios são retentados: 5xx, timeout e erro de conexão.
- Respostas de negócio e de payload nunca são retentadas.

A cotação completa tem prazo total de 15 segundos, contado desde a primeira chamada. Cada tentativa usa como timeout o menor valor entre 5 segundos e o tempo restante do prazo. Esperas também consomem o prazo.

Quando o prazo acaba, a cotação é encerrada como `indisponivel`, mesmo que ainda houvesse tentativas, e os planos já obtidos não são exibidos.

## 9. Timeout

O timeout é de 5 segundos por tentativa, com `httpx.Timeout(5.0)`, limitado pelo tempo restante do prazo total da seção 8. Como o prazo total é de 15 segundos, um timeout consome um terço do prazo, e as retentativas e os demais planos ficam com o tempo restante.

## 10. Logs

Cada tentativa gera um registro de log, em JSON, com os campos:

- nível, horário em UTC, evento e identificador da conversa;
- plano, número da tentativa e status HTTP, quando houver;
- duração da chamada, em milissegundos;
- resultado da tentativa.

O log nunca contém o corpo da requisição nem o CEP. A montagem do registro passa pelo mesmo critério de mascaramento da [[rfc-0008-mascaramento-de-dados-pessoais]].

## 11. Testes

Os testes usam `httpx.MockTransport` e a função `sleep` injetada. Não há chamada de rede.

| Caso | Entrada simulada | Resultado esperado |
| --- | --- | --- |
| Cotação completa | 200 para os três planos | `sucesso`, com valores em `Decimal` |
| Recusa por regra | 422 com `cotacao_recusada` | `recusada`, com o motivo |
| Payload inválido | 422 no formato FastAPI | `payload_invalido` |
| Falha transitória e recuperação | 503 na primeira tentativa e 200 na segunda | `sucesso`, com uma espera de 0,5 s |
| Falha persistente | 503 nas três tentativas | `indisponivel`, com esperas de 0,5 s e 1 s |
| Timeout | Exceção de timeout nas três tentativas | `indisponivel` |
| Erro de conexão | Exceção de conexão na primeira tentativa | Retenta e recupera |
| Status inesperado | 418 | `indisponivel`, sem retry |
| Conversão de valores | Prêmio `119.9` | `Decimal("119.90")` |
| Conversão com arredondamento | Prêmio `10.005` | `Decimal("10.01")` |
| Log sem dado pessoal | Chamada com CEP | Nenhum registro contém o CEP |

## 12. Critérios de aceite técnicos

1. O cliente chama o serviço apenas com os dados recebidos, sem completar nem alterar valores.
2. Nenhum valor monetário é representado por ponto flutuante após a conversão.
3. Erros transitórios são retentados exatamente até três tentativas, com as esperas de 0,5 s e 1 s.
4. Respostas 422 e 400 nunca são retentadas.
5. Todos os casos da seção 11 passam sem chamada de rede.
6. Nenhum registro de log contém o CEP ou o corpo da requisição.
7. Nenhuma cotação completa ultrapassa 15 segundos, incluindo retentativas.

## 13. Decisões de prazo

- **Prazo total de 15 segundos** para a cotação completa, conforme decisão do usuário.
- **Timeout é falha transitória.** Um timeout é retentado como um 5xx, com as mesmas tentativas e esperas.
- **Consequência:** se um plano atingir timeout na primeira tentativa, sobra cerca de 10 segundos para os demais planos e as retentativas. Isso pode resultar em `indisponivel` com mais frequência do que o pior caso de tentativas isoladas sugere.

## 14. Decisões relacionadas

- [[fdd-0001-fluxo-de-conversa-e-coleta]]: origem das regras de coleta.
- [[rfc-0006-servico-de-cotacao]]: contrato do serviço e comportamento de erro.
- [[rfc-0005-modelo-llm-e-apis-externas]]: política de retry para erros da API.
- [[adr-0008-cliente-http-cotacao]]: escolha do cliente HTTP e do timeout.

## Decisão de revisão: formato do pro-rata

O campo `primeiro_pagamento_pro_rata` do `PlanoCotado` é um `Decimal` extraído de `valor_primeiro_pagamento`, porque a API devolve um objeto. Ver a RFC-0006.
