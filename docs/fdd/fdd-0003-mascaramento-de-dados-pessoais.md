---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0003 — Mascaramento de dados pessoais

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0008-mascaramento-de-dados-pessoais]] |
| **Documentos relacionados** | [[adr-0020-padroes-deteccao-pii]] · [[adr-0011-logging-json-padrao]] · [[adr-0016-biblioteca-de-testes-pytest]] · [[fdd-0001-fluxo-de-conversa-e-coleta]] · [[fdd-0002-cliente-da-cotacao]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve a biblioteca de detecção, a interface, os padrões, os testes e os critérios de aceite do mascaramento.

## 1. Escopo

O mascaramento é um módulo de código puro, sem chamada de modelo nem de rede. Ele detecta CPF, e-mail, CEP, telefone e placa em um texto e substitui cada ocorrência.

Ele é usado em quatro pontos: na mensagem do lead antes do modelo, na resposta do agente antes do envio, no conteúdo dos traces e nos logs. A regra de cada ponto está na [[rfc-0008-mascaramento-de-dados-pessoais]].

## 2. Stack e dependências

| Item | Escolha |
| --- | --- |
| Linguagem | Python 3.12 |
| Expressões regulares | Biblioteca padrão `re`, sem dependência extra |
| Testes | pytest, com casos parametrizados |
| Logs | Módulo `logging` padrão, em JSON |

Nenhuma dependência externa. O módulo não importa LangChain, LangGraph, Streamlit nem o cliente da cotação.

## 3. Estrutura de arquivos

```
autoseguro/
  mascaramento/
    __init__.py      exporta a interface pública
    padroes.py       padrões de detecção, em ordem de aplicação
    mascara.py       função de substituição e tipos de resultado
tests/
  mascaramento/
    test_padroes.py
    test_mascara.py
    test_vazamento.py
```

## 4. Padrões e ordem de aplicação

A ordem é fixa, conforme a [[adr-0020-padroes-deteccao-pii]]: CPF, e-mail, CEP, telefone e placa. Os padrões são aplicados em sequência sobre o texto, e cada substituição altera o texto que os padrões seguintes recebem. Como os marcadores não têm a forma de nenhum padrão, eles não são mascarados de novo.

| Ordem | Tipo | Marcador | Padrão de referência (sem diferenciar maiúsculas) |
| --- | --- | --- | --- |
| 1 | CPF | `[CPF]` | `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b` |
| 2 | E-mail | `[EMAIL]` | `\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b` |
| 3 | CEP | `[CEP]` | `\b\d{5}-?\d{3}\b` |
| 4 | Telefone | `[TELEFONE]` | `(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}\b` |
| 5 | Placa | `[PLACA]` | `\b[a-z]{3}-?\d{4}\b` ou `\b[a-z]{3}\d[a-z]\d{2}\b` |

Os padrões acima são a referência de implementação. A validação real é feita pelo corpus de testes da seção 8, e um padrão só é aceito se passar nesse corpus.

Os padrões não validam dígito verificador de CPF, conforme a [[rfc-0008-mascaramento-de-dados-pessoais]]. Um número com a forma de CPF é mascarado mesmo que seja inválido.

## 5. Interface pública

```
detectar(texto: str) -> list[Achado]
mascarar_entrada(texto: str) -> ResultadoMascara
mascarar_saida(texto: str) -> ResultadoMascara
```

**`Achado`**: tipo, valor original, posição inicial e posição final no texto original.

**`ResultadoMascara`**: texto mascarado, lista de achados e contagem por tipo.

- `mascarar_entrada` substitui cada achado pelo marcador do seu tipo, como `[CPF]`. Usada na mensagem do lead antes do modelo.
- `mascarar_saida` substitui cada achado por `[dado omitido]`, conforme decisão do usuário. Usada na resposta do agente antes do envio e nos traces de saída.
- `detectar` não altera o texto. Usada pela etapa que guarda o valor original no estado.

O valor original de cada achado é devolvido apenas para a etapa de estado. Ele nunca é gravado em log nem enviado ao modelo.

## 6. Tratamento de texto

- A detecção não diferencia maiúsculas de minúsculas.
- Espaços e quebras de linha no texto original são preservados. Só o trecho detectado é substituído.
- Textos vazios e textos sem dado pessoal voltam inalterados, com lista de achados vazia.
- Se um mesmo trecho casar com dois padrões, o primeiro na ordem da seção 4 vence.

## 7. Logs

Cada chamada de mascaramento gera um registro de log, em JSON, com:

- nível, horário em UTC, evento e identificador da conversa;
- ponto de aplicação: entrada, saída, trace ou log;
- contagem por tipo, sem valor.

Nenhum registro contém o valor detectado. Esta regra é verificada pelos testes da seção 8.

## 8. Testes

Os testes são determinísticos e não chamam rede nem modelo.

| Arquivo | O que verifica |
| --- | --- |
| `test_padroes.py` | Cada padrão casa com as variações de formato e não casa com textos comuns |
| `test_mascara.py` | Substituição, marcadores, texto sem dado, texto vazio e ordem de precedência |
| `test_vazamento.py` | Nenhum valor original aparece no texto mascarado, nos logs nem nos registros |

**Corpus de variações**

- CPF com e sem pontuação, e com espaços em volta.
- E-mail com subdomínio, com números e com sinais como ponto e hífen.
- CEP com e sem hífen.
- Telefone com +55, com 55 sem o sinal, com DDD entre parênteses, sem parênteses e com hífen.
- Placa no formato antigo e no formato Mercosul, em maiúsculas e minúsculas.

**Textos que não devem ser mascarados**

- Preço no formato `R$ 119,90`.
- Data no formato `2026-07-15`.
- Idade e ano isolados, como `35 anos` e `2022`.

Os textos sem dado pessoal devem passar inalterados.

## 9. Critérios de aceite técnicos

1. Todos os casos do corpus da seção 8 passam.
2. Nenhum valor original detectado aparece na saída de `mascarar_entrada` nem de `mascarar_saida`.
3. Nenhum registro de log contém o valor original.
4. A ordem de precedência da seção 4 é respeitada, e nenhum marcador é mascarado de novo.
5. Textos sem dado pessoal passam sem alteração.

## 10. Riscos e limites aceitos

- **Falso positivo.** Um número de protocolo com oito dígitos pode ser lido como CEP e mascarado. Aceito, conforme a RFC-0008.
- **Formato não previsto.** Um telefone escrito de forma diferente das variações do corpus pode escapar. A mitigação é ampliar o corpus quando o caso aparecer.
- **Nome do lead.** Não é mascarado nesta fase, conforme a RFC-0008. Esse risco fica registrado.

## 11. Decisões relacionadas

- [[rfc-0008-mascaramento-de-dados-pessoais]]: regras de negócio do mascaramento.
- [[adr-0020-padroes-deteccao-pii]]: padrões e ordem de aplicação.
- [[fdd-0002-cliente-da-cotacao]]: o cliente recebe o CEP original do estado, nunca o mascarado.
- [[fdd-0001-fluxo-de-conversa-e-coleta]]: pontos de coleta de CEP e CPF.
