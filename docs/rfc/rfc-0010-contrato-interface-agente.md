---
tipo: rfc
status: aprovado
data: 2026-11-09
---

# RFC-0010 — Contrato entre a interface e o agente

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0001-simulador-de-conversa]] |
| **Documentos relacionados** | [[rfc-0003-banco-postgres-pgvector]] · [[rfc-0007-agente-langgraph-langchain]] · [[rfc-0009-juiz-e-regras-de-validacao]] · [Rastreabilidade](../rastreabilidade.md) · [CLAUDE.md](../../CLAUDE.md) |

> **Nível deste documento.** Esta RFC define o contrato conceitual entre a simulação e o agente: o que a interface envia, o que recebe e o que lê do banco. Não é especificação final. Nomes de funções, formatos de dados e a estrutura de pastas ficam para a implementação.

## 1. Resumo executivo (TL;DR)

A interface Streamlit e o agente rodam no mesmo processo. A interface chama o agente diretamente, a cada mensagem do lead, e recebe a resposta completa. Enquanto espera, mostra um indicador de digitando.

A interface não recebe o estado do agente. Ela lê o estado no Postgres, nas tabelas de registro e no checkpoint. Assim, cotações, status e encaminhamento aparecem na tela a partir do banco.

Quando o agente falha de forma inesperada, o chat mostra uma mensagem neutra, e o erro completo fica registrado para análise.

## 2. Contexto e problema

A [[rfc-0001-simulador-de-conversa]] define a tela, o painel lateral e o campo desativado após o encaminhamento. Ela deixou o contrato entre a interface e o agente para uma RFC própria. Esta RFC cumpre esse papel.

O agente é descrito na [[rfc-0007-agente-langgraph-langchain]], e a verificação das respostas na [[rfc-0009-juiz-e-regras-de-validacao]]. A interface precisa de um contrato simples, que não dependa dos detalhes internos do grafo.

## 3. Proposta conceitual

### 3.1 Chamada

A interface chama o agente com duas informações: o identificador da conversa e a mensagem do lead. O agente processa um turno e devolve a resposta.

A chamada é feita no mesmo processo, sem rede entre as duas partes. A fronteira existe no código, para que a interface não dependa dos nós do grafo.

### 3.2 Resposta

A resposta de cada turno traz:

- o texto a ser mostrado ao lead, já aprovado pelo juiz;
- a indicação de que a conversa foi encaminhada, quando for o caso.

A resposta chega inteira. A interface mostra um indicador de digitando durante a espera, e exibe o texto quando ele estiver pronto. Só o texto aprovado pelo juiz sai do agente.

### 3.3 Leitura do estado

Tudo que a interface mostra além do chat vem do Postgres:

- as cotações recebidas, da área de registro;
- o status da conversa;
- o motivo do encaminhamento, quando houver;
- os dados coletados, do estado do grafo, quando forem necessários à tela.

A interface não guarda estado próprio da conversa. Ao reabrir, ela lê o banco e mostra o mesmo estado.

### 3.4 Campo desativado

Depois do encaminhamento, a interface desativa o campo do lead. A decisão vem da leitura do status no banco, e não de um sinal enviado pelo agente. Assim, a tela não depende de o agente lembrar de avisar.

### 3.5 Concorrência

A interface processa um turno por conversa de cada vez. A trava é gravada no banco, na própria conversa, conforme o FDD-0007. Enquanto um turno está em andamento, o campo do lead fica bloqueado, em qualquer aba. Assim, duas mensagens da mesma conversa não se misturam no estado.

### 3.6 Erros

Se o agente falhar de forma inesperada, a interface mostra uma mensagem neutra no chat, sem detalhe técnico. O erro completo, com a etapa em que ocorreu e o identificador da conversa, é registrado para análise.

Erros previstos, como a cotação indisponível, não são tratados aqui. Eles já têm comportamento definido pelo agente, conforme a [[rfc-0007-agente-langgraph-langchain]].

### 3.7 Criação de conversa

A interface cria o lead fictício, com nome e telefone gerados aleatoriamente, conforme a [[rfc-0001-simulador-de-conversa]]. Depois da criação, a conversa passa a existir no registro, e o agente a recebe pelo identificador.

## 4. Alternativas consideradas

| # | Alternativa | Trade-off que motivou o descarte |
| --- | --- | --- |
| ALT-1 | **Agente como API HTTP separada** | Mais isolado, mas adiciona um processo a subir. Foi descartada pelo usuário, que escolheu chamada direta. |
| ALT-2 | **Resposta em streaming, token a token** | Mais parecida com o WhatsApp, mas o juiz precisaria validar antes de mostrar qualquer parte. Foi descartada pelo usuário. |
| ALT-3 | **Agente devolve o estado a cada turno** | Duplica a fonte de verdade entre o agente e o banco. Foi descartada pelo usuário, que escolheu ler do banco. |
| ALT-4 | **Erro técnico visível na tela** | Ajuda a depurar, mas expõe detalhes internos na demonstração. Foi descartada pelo usuário. |

## 5. Questões resolvidas

| # | Questão | Decisão |
| --- | --- | --- |
| QA-1 | Forma de chamada | Mesmo processo, chamada direta. |
| QA-2 | Forma da resposta | Resposta inteira, com indicador de digitando. |
| QA-3 | Origem do estado | Leitura do banco. |
| QA-4 | Tratamento de erro inesperado | Mensagem neutra, com registro do erro. |

## 6. Premissas assumidas

- Um turno por conversa de cada vez. A interface bloqueia o campo durante o processamento.
- A interface não envia mensagens duplicadas automaticamente. Um reenvio é ação do avaliador.
- A fronteira no código é uma função com entrada e saída definidas, sem depender dos nós do grafo.

## 7. Impacto e riscos

**Impacto**

- **Código:** a interface passa a depender de uma única função de turno do agente, e de consultas de leitura no banco.
- **Banco:** a interface lê as tabelas de registro e o checkpoint, sem escrever no estado do grafo.
- **Testes:** a fronteira pode ser testada sem a interface, e a interface pode ser testada com um agente de teste.

**Riscos**

| Risco | Efeito | Mitigação proposta |
| --- | --- | --- |
| Interface e agente divergem sobre o estado | Tela mostra status diferente do banco | A tela lê só do banco, sem estado próprio. |
| Turno demorado trava a interface | Avaliador percebe lentidão | Indicador de digitando e limite de tempo do turno, definido na implementação. |
| Erro inesperado é registrado sem contexto | Análise difícil depois | O registro inclui o identificador da conversa e a etapa. |
| Acoplamento ao grafo cresce | Mudança no agente quebra a interface | Fronteira com função de turno, e testes de contrato. |

## 8. Decisões relacionadas

- [[rfc-0001-simulador-de-conversa]]: tela, painel e campo desativado.
- [[rfc-0003-banco-postgres-pgvector]]: registro e checkpoint lidos pela interface.
- [[rfc-0007-agente-langgraph-langchain]]: agente e etapas do fluxo.
- [[rfc-0009-juiz-e-regras-de-validacao]]: respostas só saem após aprovação.
