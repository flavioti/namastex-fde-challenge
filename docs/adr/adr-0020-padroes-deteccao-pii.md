---
tipo: adr
status: aceito
data: 2026-11-09
---

# ADR-0020 — Padrões de detecção de dados pessoais e ordem de precedência

| Campo | Valor |
| --- | --- |
| **Status** | Aceito |
| **Data** | 2026-11-09 |
| **Decisor** | Usuário, na sessão de resolução dos bloqueios do FDD |
| **Autor do registro** | Paulo (Tech Lead) |

## Contexto

A [[rfc-0008-mascaramento-de-dados-pessoais]] define o mascaramento por tipo, sem validação de dígito verificador, e exige padrões de detecção e uma ordem fixa de aplicação. Sem essas definições, o FDD de mascaramento não pode ser escrito.

Alguns formatos se parecem entre si. Um número de telefone pode ter a forma de um CEP, e um CPF pode ser lido como telefone se a ordem não for controlada.

## Decisão

- Os tipos detectados são CPF, e-mail, CEP, telefone e placa, cada um com marcador próprio, como `[CPF]`.
- A ordem de aplicação é fixa: CPF, e-mail, CEP, telefone e placa.
- **CPF:** onze dígitos, com ou sem pontuação. Sem validação de dígito verificador.
- **E-mail:** formato usual de endereço, com um arroba e domínio.
- **CEP:** oito dígitos, com ou sem hífen.
- **Telefone:** com e sem o código do país, +55, e com DDD com ou sem parênteses. Exemplos: +55 11 91234-5678, (11) 91234-5678 e 11 912345678.
- **Placa:** formato antigo, três letras e quatro números, e formato Mercosul, três letras, um número, uma letra e dois números.
- Mascarar em excesso é aceito. Um número que tenha a forma de dado pessoal é mascarado, mesmo que não seja.

## Consequências

- A ordem fixa evita que um CEP seja lido como telefone e mascarado com o marcador errado.
- Os padrões são testados com um corpus que cobre todas as variações da lista acima, conforme a RFC-0011.
- Um formato novo de dado pessoal exige revisão deste ADR e dos testes.

## Alternativas consideradas

- Telefone apenas com +55: deixa passar números locais, o que foi descartado pelo usuário.
- Telefone antes do CEP: pode mascarar CEPs com formato de telefone, o que foi descartado pelo usuário.
- Placa apenas no formato antigo: deixa passar placas Mercosul, o que foi descartado pelo usuário.

## Decisões relacionadas

- [[rfc-0008-mascaramento-de-dados-pessoais]]
- [[rfc-0011-avaliacao-e-testes]]
- [[fdd-0001-fluxo-de-conversa-e-coleta]]
