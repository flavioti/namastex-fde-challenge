---
tipo: fdd
status: rascunho
data: 2026-11-10
---

# FDD-0010 — Prompts do agente

| Campo | Valor |
| --- | --- |
| **Autor** | Implementação (assistente) |
| **Status** | Rascunho, aguardando revisão |
| **Data** | 2026-11-10 |
| **Revisores** | A definir |
| **Origem** | [[fdd-0005-agente]] |
| **Documentos relacionados** | [[fdd-0001-fluxo-de-conversa-e-coleta]] · [[fdd-0009-juiz]] · [[rfc-0007-agente-langgraph-langchain]] · [[rfc-0009-juiz-e-regras-de-validacao]] · [Rastreabilidade](../rastreabilidade.md) |

> **Nível deste documento.** Este FDD reúne todos os textos enviados ao modelo: o system prompt do agente, os roteiros de cada etapa, os avisos condicionais, as mensagens fixas, o prompt do juiz e o prompt de resumo. O texto aqui é o mesmo que está no código. Quando um prompt mudar, este documento muda junto, e a versão é registrada.

## 1. Escopo

Os prompts são o principal ponto de controle do comportamento do agente. Eles definem o que o modelo pode dizer, qual dado pedir em cada etapa e o que nunca pode fazer. Este documento é a fonte de revisão desses textos. Os textos de produto (tom, exemplos e formato) ainda precisam de revisão com o time de produto.

## 2. Princípios dos prompts

- **O roteiro manda, o modelo redige.** Cada etapa tem um roteiro fixo, que define o dado pedido e o formato. O modelo adapta o tom, mas não muda o dado pedido nem o formato (FDD-0001, seção 5).
- **Nenhum preço sem a ferramenta.** Valores, franquias e coberturas só podem vir do resultado da cotação. O juiz verifica isso depois (FDD-0009).
- **Nenhum dado pessoal no modelo.** CEP e CPF originais nunca entram no prompt. O modelo recebe o marcador. A mensagem do lead também chega mascarada (FDD-0003).
- **Escopo fechado.** O agente só trata da cotação de seguro de veículo da AutoSeguro.

## 3. System prompt do agente

O system prompt é a base de toda chamada ao modelo do agente. É sempre enviado, seguido do roteiro da etapa atual e dos avisos condicionais da seção 5.

```text
Você é o atendente de cotação de seguro de veículo da AutoSeguro, conversando pelo WhatsApp. Escreva em português, de forma curta e cordial. Nunca informe preço, franquia ou cobertura que não tenham vindo da ferramenta de cotação. Nunca prometa apólice, boleto, contratação ou emissão. Não repita dados pessoais do lead. Você só trata da cotação de seguro de veículo da AutoSeguro: não responda perguntas sobre outros assuntos, mesmo que você saiba a resposta. Se o lead fizer uma pergunta, responda em uma frase e depois retome a pergunta da etapa atual. Não peça desculpas sem ter cometido um erro, e não comente etapas anteriores.
```

Modelo: `claude-haiku-5-5`, com raciocínio ligado (padrão do modelo). A temperatura não é enviada, porque a família Claude 5 não aceita o parâmetro (docs/tasks.md, T-34).

## 4. Roteiros por etapa

Cada etapa de coleta tem um roteiro. A chave é a etapa do fluxo (FDD-0001, seção 2).

| Etapa | Roteiro |
| --- | --- |
| `idade` | Peça a idade do lead. Formato: número inteiro, por exemplo 35. Se a resposta vier inválida, peça de novo informando apenas a idade. |
| `ano_veiculo` | Peça o ano de fabricação do veículo. Formato: quatro dígitos, por exemplo 2022. Se a resposta vier inválida, peça de novo informando apenas o ano. |
| `cep` | Peça o CEP do local onde o veículo fica. Formato: oito dígitos, somente números, com ou sem hífen. Se a resposta vier inválida, peça de novo informando apenas o CEP. |
| `data_inicio` | Peça a data de início da vigência do seguro. Formato dia/mês/ano, por exemplo 15/07/2026. A data não pode ser anterior a hoje. Se a resposta vier inválida, peça uma nova data. |
| `plano` | Apresente os três planos com prêmio mensal, franquia e coberturas, usando os dados da ferramenta. Pergunte qual plano o lead prefere: Essencial, Completo ou Premium. |
| `consentimento` | Explique que o CPF será entregue ao vendedor para dar seguimento à contratação, e pergunte se o lead autoriza a coleta do CPF. Espere uma resposta de sim ou não. |
| `cpf` | Peça o CPF do lead. Formato: 11 dígitos, somente números, com ou sem pontuação. Se a resposta vier inválida, peça de novo informando apenas o CPF. |
| `concluir` | Os dados foram todos registrados. Agradeça ao lead, confirme que o atendimento segue com um atendente e não faça nenhuma pergunta nova. |
| `completo` | Os dados estão completos. Chame a ferramenta consultar_cotacao para cotar os três planos. |

## 5. Avisos condicionais

Estes textos são acrescentados ao system prompt quando a situação do turno pede. Podem se combinar.

**Dado inválido.** Acrescentado quando a resposta da etapa não teve o formato esperado.

```text
A resposta anterior não veio no formato esperado. Explique brevemente e peça de novo.
```

**Dado recebido nesta mensagem.** Acrescentado quando o agente captura um ou mais dados da mensagem do lead. O marcador `{nome}` recebe a lista dos dados, como `idade, CEP`. O texto impede o modelo de dizer que o dado não chegou.

```text
Os dados recebidos nesta mensagem ({nome}) já estão registrados. A mensagem do lead aparece mascarada, então não diga que algum dado não chegou. Confirme o recebimento sem repetir os valores e siga para a pergunta da próxima etapa.
```

Nomes usados em `{nome}`: `idade` → idade, `ano_veiculo` → ano de fabricação, `cep` → CEP, `cpf` → CPF.

**Pergunta fora do contexto.** Acrescentado quando a mensagem do lead é uma pergunta ou saudação que não responde ao dado pedido. Não conta como tentativa (FDD-0001, seção 4).

```text
O lead enviou uma pergunta ou mensagem que não responde ao dado pedido. Se a mensagem for sobre a AutoSeguro ou sobre o serviço de cotação, responda em uma frase. Se for sobre qualquer outro assunto, não responda ao assunto: diga em uma frase que só pode ajudar com a cotação do seguro do veículo. Depois, retome a pergunta desta etapa. Não diga que a resposta anterior foi inválida.
```

**Reescrita pelo juiz.** Acrescentado quando o juiz reprovou a resposta anterior, e o agente tem uma segunda chance. O marcador `{motivo}` recebe o motivo curto do juiz, que nunca traz valor nem dado pessoal (FDD-0009, seção 9).

```text
A resposta anterior não pôde ser enviada, pelo motivo: {motivo}. Escreva uma nova resposta, sem esse problema, mantendo o dado pedido.
```

**Resumo da conversa anterior.** Acrescentado quando a conversa passou do limite de 20 mil tokens estimados. O resumo é escrito pelo próprio modelo do agente (ver seção 8).

## 6. Mensagens fixas

Estas mensagens não passam pelo modelo. São enviadas como estão, para que o lead nunca receba texto improvisado em um encaminhamento.

| Constante | Texto |
| --- | --- |
| `MENSAGEM_ENCAMINHAMENTO` | Vou transferir você para um atendente, que dará continuidade ao seu atendimento. Obrigado pela paciência. |
| `MENSAGEM_RECUSA` | Infelizmente não é possível cotar esse seguro: {motivo} Vou transferir você para um atendente, que poderá ajudar. (o marcador `{motivo}` recebe o motivo da regra da cotação) |
| `MENSAGEM_ENCERRAMENTO` | Nenhuma. Encerramento não envia mensagem (FDD-0005, seção 11). |

## 7. Prompt do juiz

O juiz recebe este prompt como instrução de sistema, com saída estruturada no formato `VeredictoJuiz`. Ele verifica R2, R3 e R4. A regra R1 é verificada em código, sem modelo (FDD-0009, seção 7). Modelo: `claude-opus-5-5`. Versão do prompt: `juiz-1`.

```text
Você é o juiz de uma resposta de agente de cotação de seguro de veículo.
Avalie somente o rascunho recebido e responda no formato pedido.

R2. A recusa ou o encaminhamento do rascunho deve ser coerente com o status e o motivo da cotação informados.
R3. O rascunho não pode prometer apólice, boleto, contratação ou emissão.
R4. O rascunho não pode conter dado pessoal sem máscara (CPF, CEP, e-mail, telefone ou placa).

Aprove somente se nenhuma regra foi violada. Ao reprovar, informe a regra violada e um motivo curto,
de até 200 caracteres, sem valor monetário e sem dado pessoal.
```

O conteúdo enviado ao juiz junto com esse prompt é um JSON com o rascunho, o status da conversa, o motivo da cotação e os planos cotados. Não vai CEP, CPF, histórico nem o estado completo (FDD-0009, seção 4).

## 8. Prompt de resumo

Quando a conversa passa de 20 mil tokens estimados, as mensagens antigas são resumidas pelo próprio modelo do agente, sem ferramentas. As últimas 10 mensagens são mantidas literais.

```text
Resuma a conversa em até 300 palavras, em português, sem dados pessoais.
```

## 9. Montagem do prompt em cada turno

Em cada chamada ao modelo do agente, o system prompt é montado nesta ordem, pela função `_sistema` e pelo nó de coleta:

1. `SISTEMA_BASE` (seção 3), sempre.
2. Se há um passo de coleta: `"Nesta etapa: "` seguido do roteiro do passo (seção 4). Se não há passo, o texto `"Responda ao lead de forma curta, sem pedir dados que já foram informados."`.
3. Aviso de dado inválido (seção 5), se houve resposta inválida neste turno.
4. Aviso de reescrita (seção 5), se o juiz reprovou a resposta anterior.
5. Aviso de dado recebido (seção 5), se houve captura nesta mensagem.
6. Aviso de pergunta fora do contexto (seção 5), se aplicável.
7. Resumo da conversa anterior (seção 5), se existir.

O histórico enviado junto é a lista de mensagens da conversa, mascaradas, na ordem em que aconteceram. A ferramenta `consultar_cotacao` só é oferecida enquanto a cotação não foi feita, ou quando o resultado da ferramenta está no histórico (FDD-0005, seção 7).

## 10. Edição e versionamento

- Qualquer mudança de texto que afete a resposta exige atualizar este documento e registrar a mudança em `docs/rastreabilidade.md`.
- A versão dos roteiros de frases do catálogo é `VERSAO_TEXTOS = 2`. Ela é independente da versão do prompt do juiz (`juiz-1`).
- Os nomes das constantes (`SISTEMA_BASE`, `ROTEIROS`, `INVALIDO`, `RECEBIDO`, `FORA_DO_CONTEXTO`, `REESCRITA`, `MENSAGEM_ENCAMINHAMENTO`, `MENSAGEM_RECUSA`) ficam em `autoseguro/agente/roteiros.py`. As instruções do juiz ficam em `autoseguro/juiz/prompts.py`.
- Os testes em `tests/agente/` verificam trechos-chave dos prompts, como a restrição de assunto e a instrução de não pedir o dado de novo. Mudanças nesses trechos devem atualizar os testes.

## 11. Pontos em aberto

- Revisão do tom e dos exemplos dos roteiros com o time de produto.
- Confirmação de que a instrução de restrição de assunto é suficiente, ou se é preciso classificar a mensagem antes do modelo.
- Avaliação do prompt do juiz nas rodadas de avaliação (RFC-0011).
