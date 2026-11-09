---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0009 — Juiz: verificação R1 em código e R2 a R4 com o modelo

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0009-juiz-e-regras-de-validacao]] |
| **Documentos relacionados** | [[rfc-0005-modelo-llm-e-apis-externas]] · [[rfc-0007-agente-langgraph-langchain]] · [[rfc-0008-mascaramento-de-dados-pessoais]] · [[rfc-0011-avaliacao-e-testes]] · [[adr-0007-cliente-modelo-chatanthropic]] · [[adr-0010-valores-monetarios-decimal]] · [[adr-0016-biblioteca-de-testes-pytest]] · [[fdd-0002-cliente-da-cotacao]] · [[fdd-0005-agente]] · [[fdd-0006-observabilidade]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve a verificação R1 em código, a chamada ao modelo do juiz para R2 a R4, o formato da decisão, o tratamento de falha e os testes.

## 1. Escopo

O juiz decide se um rascunho de resposta do agente pode ser enviado ao lead. Ele só é acionado para rascunhos que citam valor ou recusa. Aprova ou reprova, com a regra violada e um motivo curto.

A regra R1 é verificada em código, inclusive a associação entre valor e plano. As regras R2, R3 e R4 são verificadas pelo modelo `claude-opus-5-5`.

## 2. Stack e dependências

| Item | Escolha | Referência |
| --- | --- | --- |
| Modelo | `ChatAnthropic` com `claude-opus-5-5`, temperatura 0 | [[adr-0007-cliente-modelo-chatanthropic]] |
| Saída estruturada | Modelo Pydantic `VeredictoJuiz`, via `with_structured_output` | [[rfc-0009-juiz-e-regras-de-validacao]] |
| Valores monetários | `Decimal`, com duas casas | [[adr-0010-valores-monetarios-decimal]] |
| Tentativas | Até três, com esperas de 0,5 s e 1 s, como no cliente da cotação | [[fdd-0002-cliente-da-cotacao]] |
| Testes | pytest, com modelo substituto | [[adr-0016-biblioteca-de-testes-pytest]] |

## 3. Estrutura de arquivos

```
autoseguro/
  juiz/
    __init__.py
    modelos.py        VeredictoJuiz e entrada do juiz
    extracao.py       reconhecimento de valores no texto
    r1.py             verificação R1 em código
    prompts.py        instruções de R2, R3 e R4 e versão do prompt
    juiz.py           orquestração: R1, depois o modelo
tests/
  juiz/
    test_extracao.py
    test_r1.py
    test_juiz.py
```

## 4. Entrada do juiz

O juiz recebe apenas:

| Campo | Origem | Observação |
| --- | --- | --- |
| `rascunho` | Estado do agente | Já mascarado. Nunca contém CPF, CEP, e-mail, telefone ou placa |
| `planos` | Resultado da cotação | Preços, franquias, coberturas e pro-rata, sem CEP nem CPF |
| `status` | Estado do agente | `em_andamento`, `cotada`, `encaminhada` ou `encerrada` |
| `motivo_cotacao` | Resultado da cotação | Recusa ou falha, quando houver |

O juiz não recebe o estado completo, nem o histórico da conversa. Assim, o modelo não vê dados pessoais, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]].

## 5. Gatilho

O juiz é acionado quando o rascunho:

- contém pelo menos um valor reconhecido pela extração da seção 6; ou
- contém termo de recusa ou indisponibilidade, da lista fixa em `prompts.py`.

Rascunhos sem nenhum dos dois passam direto para a resposta, conforme a [[fdd-0005-agente]].

## 6. Extração de valores

`extracao.py` reconhece dois tipos de valor, por expressão regular:

| Tipo | Exemplo | Convertido para |
| --- | --- | --- |
| Valor com `R$` | `R$ 119,90`, `R$ 4.500,00` | `Decimal` |
| Número com separador decimal | `119,90`, `119.90` | `Decimal` |

Números inteiros sem `R$` são ignorados. Isso cobre prazos, idades e anos, que não são valores monetários.

A conversão segue o formato brasileiro: ponto é separador de milhar e vírgula é separador decimal. Para número com ponto decimal e sem vírgula, o ponto é tratado como separador decimal.

## 7. Verificação R1 em código

1. Extrai os valores do rascunho.
2. Monta o conjunto de valores permitidos por plano: `premio_mensal`, `franquia` e `primeiro_pagamento_pro_rata` de cada plano do resultado da cotação, como `Decimal`, e um conjunto geral com a união de todos os planos.
2a. Para cada valor, identifica o plano citado na mesma frase, pelo nome do plano. Se houver um plano citado, o valor precisa estar no conjunto desse plano. Se não houver, o valor precisa estar no conjunto geral.
3. Se não há valor no rascunho, R1 é aprovada.
4. Se há valor e não há cotação com planos, R1 é reprovada. Nenhum preço é permitido sem cotação, conforme o OBJ-3 do PRD.
5. Se há valor e cada valor está no conjunto permitido, R1 é aprovada.
6. Se algum valor não está no conjunto, R1 é reprovada.

Se R1 for reprovada, o modelo não é chamado. A decisão é gravada com a regra R1.

## 8. Verificação pelo modelo

Quando R1 é aprovada, o modelo `claude-opus-5-5` verifica:

- **R2:** recusa e encaminhamento coerentes com o status e o motivo da cotação.
- **R3:** nenhuma promessa de apólice, boleto, contratação ou emissão.
- **R4:** nenhum dado pessoal sem máscara.

A chamada usa temperatura 0. A saída é o modelo `VeredictoJuiz`, com:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `aprovado` | booleano | Verdadeiro somente se nenhuma regra foi violada |
| `regra` | `R1`, `R2`, `R3`, `R4` ou nulo | Nulo quando aprovado |
| `motivo` | texto de até 200 caracteres | Curto, sem valor monetário nem dado pessoal |

## 9. Sanitização do motivo

O motivo vai para os traces, conforme a [[fdd-0006-observabilidade]]. Antes de ser guardado, o motivo passa por uma checagem:

- se contiver `R$`, sequência de dígitos com separador ou qualquer dado pessoal reconhecido pelo mascaramento, o motivo é substituído por `motivo omitido`.

Assim, mesmo que o modelo repita um valor no motivo, ele não vai para o trace.

## 10. Falhas

| Situação | Tratamento |
| --- | --- |
| Chamada ao modelo falha | Até três tentativas, com esperas de 0,5 s e 1 s |
| Saída fora do formato `VeredictoJuiz` | Conta como uma tentativa falha |
| Três tentativas falham | Decisão reprovada, com motivo `falha do juiz`, e encaminhamento, conforme a [[fdd-0005-agente]] |
| Erro de código no R1 | Decisão reprovada com motivo `falha do juiz`, e registro do erro sem conteúdo |

Nenhuma falha do juiz libera o rascunho. Essa é uma falha fechada, conforme a RFC-0009.

## 11. Decisão e registro

A decisão do juiz é devolvida ao agente com: aprovado, regra, motivo e número de tentativas.

Cada decisão gera feedback no trace, conforme a [[fdd-0006-observabilidade]]:

- `juiz_regra_1` a `juiz_regra_4`, com 1 para aprovado e 0 para reprovado;
- `juiz_decisao`, com 1 para aprovado e 0 para reprovado.

A versão do prompt é gravada como metadado `versao_prompt`, conforme a [[adr-0017-metadados-de-trace-dicionario-unico]].

## 12. Testes

Os testes não chamam o modelo real. O modelo é substituído por um dublê que devolve saídas roteirizadas, e a contagem de chamadas é verificada.

| Arquivo | O que verifica |
| --- | --- |
| `test_extracao.py` | Reconhecimento e conversão de cada formato, e rejeição de inteiros sem `R$` |
| `test_r1.py` | Valor permitido, valor fora da cotação, valor sem cotação e rascunho sem valor |
| `test_juiz.py` | Aprovação, reprovação em R2, falha com retry, saída inválida e motivo sanitizado |

**Casos de extração**

- `R$ 119,90` e `R$ 4.500,00` são reconhecidos e convertidos.
- `119.90` é reconhecido.
- `2 anos` e `30 dias` não são reconhecidos.
- `R$ 4.500,00` na cotação e no rascunho são iguais como `Decimal`.

**Casos do juiz**

- Rascunho com valor de R1 reprovado não chama o modelo.
- Rascunho sem valor e sem recusa não chama o modelo.
- Modelo aprova: a decisão é aprovada, sem regra.
- Modelo reprova em R2: a decisão traz R2 e um motivo.
- Saída fora do formato, três vezes seguidas: decisão reprovada com motivo `falha do juiz`.
- Motivo contendo `R$ 999,00`: o motivo é substituído por `motivo omitido`.

## 13. Critérios de aceite técnicos

1. Nenhum rascunho com valor fora da cotação é aprovado.
2. Nenhum rascunho com valor é aprovado quando não há cotação.
3. O modelo não é chamado quando R1 reprova.
4. Nenhuma falha do juiz libera o rascunho.
5. O motivo gravado nunca contém valor monetário.
6. O juiz nunca recebe CPF, CEP, e-mail, telefone ou placa.
7. Os casos da seção 12 passam sem chamada ao modelo real.

## 14. Decisões de R1

- **Formatos de valor.** A R1 verifica todo número com separador decimal e todo valor com `R$`. Inteiros sem `R$`, como prazos e idades, são ignorados.
- **Associação valor e plano.** Verificada em código, pelo nome do plano na mesma frase.

## 15. Decisões relacionadas

- [[rfc-0009-juiz-e-regras-de-validacao]]: regras e formato da decisão.
- [[rfc-0005-modelo-llm-e-apis-externas]]: modelo do juiz e política de tentativas.
- [[rfc-0008-mascaramento-de-dados-pessoais]]: dados que não entram no juiz.
- [[fdd-0005-agente]]: onde o juiz é chamado no grafo.
- [[fdd-0006-observabilidade]]: feedback e versão do prompt.
