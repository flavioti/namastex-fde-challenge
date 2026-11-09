---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0007 — Interface de simulação (Streamlit)

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0001-simulador-de-conversa]] |
| **Documentos relacionados** | [[rfc-0010-contrato-interface-agente]] · [[fdd-0001-fluxo-de-conversa-e-coleta]] · [[fdd-0003-mascaramento-de-dados-pessoais]] · [[fdd-0004-banco-e-migracoes]] · [[fdd-0005-agente]] · [[fdd-0006-observabilidade]] · [[adr-0012-datas-utc-e-exibicao-brasil]] · [[adr-0011-logging-json-padrao]] · [[adr-0016-biblioteca-de-testes-pytest]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve a estrutura da aplicação Streamlit, o layout, o fluxo de um turno, a trava por conversa, a aba de encaminhados e os testes da interface.

## 1. Escopo

A interface simula uma conversa de WhatsApp. O avaliador cria leads fictícios, conversa com o agente, acompanha o estado no painel lateral e consulta as conversas encaminhadas na aba própria.

A interface não contém regra de negócio. Ela lê o estado do banco e chama a função de turno do agente, conforme a [[rfc-0010-contrato-interface-agente]].

## 2. Stack e dependências

| Item | Escolha |
| --- | --- |
| Interface | Streamlit, na versão do lock |
| Linguagem | Python 3.12 |
| Acesso a dados | Pool e repositórios do FDD-0004 |
| Agente | Função de turno e leitura de estado do FDD-0005 |
| Testes | pytest, com `streamlit.testing.v1.AppTest` |

A interface não acessa o modelo, a cotação nem o LangSmith diretamente.

## 3. Estrutura de arquivos

```
ui-app/
  app.py                 ponto de entrada, fino, que chama o pacote
autoseguro/
  interface/
    __init__.py
    layout.py            montagem da barra lateral, das abas e do painel
    conversa.py          exibição do chat e envio de turnos
    trava.py             trava de turno no banco
    encaminhados.py      aba de conversas encaminhadas, somente leitura
    leads.py             geração de nome e telefone fictícios
    estado_visual.py     texto e estado exibidos no painel lateral
    respondedor.py       respondedor de teste, enquanto o agente não existe
tests/
  interface/
    test_app.py
    test_trava.py
    test_leads.py
```

`ui-app/app.py` apenas importa e executa a montagem do `autoseguro.interface`. Toda a lógica fica no pacote, para que possa ser testada sem subir a página.

## 4. Layout

**Barra lateral**

- Botão "Nova conversa", que cria um lead fictício e abre a conversa.
- Lista de conversas, com nome do lead, status e horário da última mensagem em Brasília.
- A lista é ordenada pela última atualização, da mais recente para a mais antiga, conforme a decisão do usuário.

**Área principal, com duas abas**

- **Conversa:** à esquerda, o chat. À direita, o painel de estado.
- **Encaminhados:** tabela somente leitura com as conversas encaminhadas.

**Painel de estado**

| Item | Fonte |
| --- | --- |
| Status | `registro.conversas.status` |
| Dados coletados | Estado do agente, lido pela função de leitura do FDD-0005 |
| Cotações dos três planos | `registro.cotacoes`, do resultado mais recente |
| Motivo do encaminhamento | `registro.encaminhamentos`, quando houver |

Valores de CEP no painel aparecem mascarados. O CPF não aparece no painel, apenas na aba de encaminhados.

## 5. Chat

- Cada mensagem é exibida com o papel, lead ou agente, e o horário em Brasília.
- O texto exibido é o `conteudo_mascarado` de `registro.mensagens`, conforme a [[fdd-0003-mascaramento-de-dados-pessoais]].
- O campo de texto fica desabilitado quando o status é `encaminhada` ou `encerrada`, com um aviso fixo sobre o estado da conversa.
- O campo fica desabilitado também enquanto um turno está em andamento, na mesma conversa.

## 6. Fluxo de um turno

1. O avaliador envia um texto no campo do chat.
2. A interface tenta adquirir a trava da conversa, conforme a seção 7.
3. Se a trava não for adquirida, mostra "turno em andamento" e não envia o texto.
4. Se a trava for adquirida, mostra o indicador de digitando e chama a função de turno do agente, com o identificador da conversa e o texto.
5. Ao receber a resposta, a interface libera a trava, atualiza o chat e o painel.
6. Se a função de turno lançar erro, a interface mostra "não foi possível responder agora" no chat, registra o erro em log sem conteúdo, libera a trava e mantém a conversa aberta.

A liberação da trava acontece em um bloco que sempre é executado, inclusive em erro.

### Respondedor de teste

Enquanto o agente não está disponível, a interface usa `respondedor.py`, conforme a [[rfc-0001-simulador-de-conversa]].

- Implementa a mesma assinatura de `turno`, sem modelo de linguagem.
- Responde sempre com uma frase fixa sobre a AutoSeguro, informando que é uma empresa de seguros.
- Não altera o status da conversa, e não cota nem encaminha.
- A escolha entre respondedor de teste e agente é feita por configuração, `RESPONDEDOR`, com o valor `teste` como padrão, até o agente estar pronto.

## 7. Trava de turno

A trava usa a coluna `turno_em_andamento_desde`, de `registro.conversas`, conforme a [[fdd-0004-banco-e-migracoes]].

- **Adquirir:** um comando atualiza a linha definindo `turno_em_andamento_desde` como o horário atual, somente se a coluna estiver nula. Se nenhuma linha for alterada, a trava não foi adquirida.
- **Liberar:** o mesmo comando define a coluna como nula, somente para a conversa de que a trava foi adquirida.
- **Trava expirada:** se a coluna tiver um horário com mais de 15 minutos, a trava é considerada expirada e pode ser adquirida. Isso cobre o caso de a aplicação ter caído no meio de um turno.

O valor de 15 minutos cobre um turno longo, com cotação lenta e reescrita do juiz, conforme decisão do usuário.

## 8. Criação de lead

Um novo lead recebe nome e telefone gerados aleatoriamente, conforme a [[rfc-0001-simulador-de-conversa]].

- O nome é composto de um primeiro nome e um sobrenome, escolhidos das listas do arquivo de configuração `leads.toml`, em português.
- O telefone tem DDD da lista do mesmo arquivo e um número aleatório. O formato é fictício, e não corresponde a números reais atribuídos.
- A conversa é criada com status `em_andamento` e `criada_em` igual ao horário atual.

## 9. Aba de encaminhados

- Lista as conversas com status `encaminhada`, com o motivo, o resumo e o CPF, quando houver.
- O CPF aparece sem máscara, conforme a RF-10 do PRD.
- A aba é somente leitura. Não há botão de resposta, nem alteração de status.
- A lista é ordenada pelo horário do encaminhamento, da mais recente para a mais antiga.

## 10. Datas e horários

Todos os horários exibidos são convertidos de UTC para Brasília, conforme a [[adr-0012-datas-utc-e-exibicao-brasil]]. Nenhuma data é gravada na interface.

## 11. Logs

Os erros da interface seguem a [[adr-0011-logging-json-padrao]]: evento, identificador da conversa, tipo do erro e horário em UTC. O registro não contém o texto digitado nem a resposta do agente.

## 12. Testes

Os testes usam `AppTest`, que executa a página sem navegador, e uma função de turno substituída por um dublê.

| Arquivo | O que verifica |
| --- | --- |
| `test_app.py` | Criação de lead, envio de turno, campo desabilitado após encaminhamento, aba de encaminhados somente leitura, mensagem neutra em erro |
| `test_trava.py` | Aquisição, liberação, conflito e expiração da trava |
| `test_leads.py` | Nome e telefone sempre vêm das listas do `leads.toml`, e o formato do telefone é válido |

**Casos de interface**

- Dois envios seguidos na mesma conversa: o segundo mostra "turno em andamento" enquanto o primeiro não termina.
- Erro na função de turno: a mensagem neutra aparece, a trava é liberada e a conversa segue aberta.
- Conversa encaminhada: o campo de texto fica desabilitado e a aba de encaminhados mostra o CPF sem máscara.
- Lista de conversas: a conversa com atualização mais recente aparece primeiro.

## 13. Critérios de aceite técnicos

1. Nenhum turno é executado sem a trava adquirida.
2. A trava é liberada mesmo quando o agente falha.
3. Nenhuma mensagem exibida no chat contém CPF, CEP, e-mail, telefone ou placa em texto.
4. O CPF aparece apenas na aba de encaminhados, e sem edição.
5. Todos os horários exibidos estão em Brasília.
6. Nenhum log contém o texto digitado ou a resposta do agente.
7. Os testes da seção 12 passam sem chamada de rede nem de modelo.

## 14. Decisões de exibição e configuração

- **Chat mascarado.** O chat mostra a mensagem como ficou guardada, com marcadores como `[CPF]`.
- **Listas editáveis.** Nomes e DDDs ficam no arquivo `leads.toml`, versionado e editável sem mudança de código.
- **Trava de 15 minutos,** conforme a seção 7.

## 15. Decisões relacionadas

- [[rfc-0001-simulador-de-conversa]]: tela, painel e aba de encaminhados.
- [[rfc-0010-contrato-interface-agente]]: função de turno e leitura do estado.
- [[fdd-0004-banco-e-migracoes]]: tabelas e trava por conversa.
- [[fdd-0005-agente]]: função de turno e leitura do estado.
