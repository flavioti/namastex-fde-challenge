# AutoSeguro: agente de cotação, guia de uso e desenvolvimento

Este documento explica como rodar o projeto, como usar a simulação e como trabalhar no código. O `README.md` é o enunciado do desafio e não foi alterado.

O projeto é um MVP de demonstração. Um agente conversa com um lead de seguro de veículo, coleta os dados, consulta a cotação e decide se resolve ou encaminha para um humano. A conversa acontece numa interface Streamlit que simula o WhatsApp.

## 1. Requisitos

| Ferramenta | Uso |
| --- | --- |
| Python 3.12 | Linguagem do projeto. O `uv` instala a versão certa. |
| uv | Gerenciador de dependências e de execução. |
| Docker e Docker Compose | Sobem o Postgres com pgvector e o serviço de cotação. |
| Chave da API da Anthropic | Necessária só para o modo `RESPONDEDOR=agente`. |
| Conta do LangSmith | Opcional. Sem ela, o tracing fica desligado. |
| Internet na primeira execução | Baixa o modelo de embeddings, de cerca de 470 MB. |

## 2. Configuração

Copie o modelo de configuração e preencha os valores:

```bash
cp .env.example .env
```

| Variável | Obrigatória | Para que serve |
| --- | --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Sim | Credenciais do serviço `banco` no Compose. |
| `DATABASE_URL` | Sim | Conexão da aplicação com o banco. |
| `COTACAO_BASE_URL` | Não | URL do serviço de cotação. Padrão: `http://localhost:8000`. |
| `ANTHROPIC_API_KEY` | Só no modo `agente` | Chave do modelo de linguagem. |
| `LANGSMITH_API_KEY` | Só com tracing | Chave da conta do LangSmith. |
| `LANGSMITH_TRACING` | Não | `true` envia os traces ao LangSmith. Padrão: `false`. |
| `RESPONDEDOR` | Não | `teste` (padrão) ou `agente`. Ver a seção 4. |
| `AUTOSEGURO_MODELOS` | Não | Caminho alternativo para o cache do modelo de embeddings. |

O arquivo `.env` não é versionado. O `.env.example` é versionado e não tem valores.

## 3. Subindo o ambiente

Execute os passos nesta ordem, a partir da raiz do projeto.

**Passo 1: subir a infraestrutura.**

```bash
docker compose up -d banco quote-api
```

O serviço `banco` é um Postgres 18 com pgvector. Os dados ficam em `database/`, que não é versionada. O serviço `quote-api` é a API de cotação, na porta 8000. Ele simula falhas: cerca de 20% das chamadas falham com erro 5xx, e cerca de 10% demoram 8 segundos. Esses valores podem ser ajustados no `docker-compose.yml`.

**Passo 2: aplicar as migrações.**

```bash
uv run --env-file .env python -m autoseguro.banco.migrar
```

O comando aplica os arquivos de `autoseguro/banco/migracoes/` em ordem. Rodar de novo não altera nada.

**Passo 3: carregar o catálogo.**

```bash
uv run --env-file .env python -m autoseguro.catalogo
```

A carga lê `quote-service/data/plans.json`, grava os planos, as regras e os trechos vetorizados. Na primeira execução, o modelo de embeddings é baixado para `database/modelos`. Nas execuções seguintes, só os trechos alterados são recalculados.

**Passo 4: abrir a simulação.**

```bash
uv run --env-file .env streamlit run ui-app/app.py
```

A página abre em `http://localhost:8501`.

## 4. Usando a simulação

A barra lateral tem o botão **Nova conversa**, que cria um lead com nome e telefone fictícios. Esses dados vêm de `ui-app/leads.toml`, que pode ser editado sem mudar o código.

A lista de conversas mostra as mais recentes primeiro. Clique numa conversa para abri-la.

A aba **Conversa** tem o chat à esquerda e o painel à direita. O chat mostra as mensagens como ficaram guardadas, com marcadores como `[CPF]` e `[CEP]`. O painel mostra o status, os dados coletados e a cotação mais recente. O CEP aparece como `[CEP]`, e o CPF nunca aparece no painel.

A aba **Encaminhados** lista as conversas que foram passadas para um humano, com o motivo e o CPF sem máscara. Essa aba é somente leitura.

### Modos de resposta

| `RESPONDEDOR` | Comportamento |
| --- | --- |
| `teste` (padrão) | Responde sempre com uma frase fixa sobre a AutoSeguro. Não usa modelo, não cota e não encaminha. Útil para testar a interface. |
| `agente` | Usa o agente completo. Exige `ANTHROPIC_API_KEY`. |

### Fluxo de uma conversa com o agente

1. O agente pede, nesta ordem, a idade, o ano do veículo, o CEP e a data de início da vigência.
2. Com os quatro dados, ele consulta a cotação dos três planos.
3. O lead escolhe um plano.
4. O agente pede autorização para coletar o CPF. Se o lead recusar, a conversa é encaminhada, e a cotação continua registrada.
5. Com o CPF, a conversa fica com status `cotada`.

Uma conversa é encaminhada quando a cotação é recusada por regra, quando a cotação falha de forma persistente, quando o lead pede um atendente, quando o CPF não é autorizado, quando um dado inválido é informado três vezes seguidas, quando o modelo ou o juiz falham, e quando a conversa atinge o limite de tokens. Conversas encaminhadas e encerradas não recebem mais mensagens.

Cada turno é protegido por uma trava no banco. Se a mesma conversa estiver com um turno em andamento, a nova mensagem é recusada com o aviso "turno em andamento". A trava expira após 15 minutos.

## 5. Testes

```bash
DATABASE_URL="postgresql://autoseguro:SENHA@localhost:5432/autoseguro" uv run pytest
```

Os testes de banco, do agente e da interface criam um banco temporário a partir de `DATABASE_URL`, aplicam as migrações e o removem ao final. Sem `DATABASE_URL`, esses testes são pulados. Os demais testes não precisam de rede nem de modelo.

Os testes de recuperação em `tests/recuperacao/` usam o modelo de embeddings já baixado. Se o modelo não estiver disponível, eles são pulados.

Os testes do agente usam modelos substitutos. Nenhum teste chama a API da Anthropic.

## 6. Estrutura do código

```
autoseguro/
  agente/         grafo LangGraph, estado, nós, ferramenta de cotação e integração com o modelo
  banco/          pool de conexões, migrações SQL, repositórios e busca híbrida
  catalogo/       carga de plans.json, embeddings e textos dos trechos
  cotacao/        cliente HTTP do serviço de cotação
  interface/      página Streamlit, trava de turno, respondedor de teste e leads
  juiz/           verificação R1 em código e R2 a R4 pelo modelo
  mascaramento/   detecção e substituição de dados pessoais
  observabilidade/ redação antes do envio ao LangSmith e feedback do juiz
ui-app/           ponto de entrada da simulação e leads.toml
quote-service/    API de cotação, fornecida pelo desafio. Não deve ser alterada.
tests/            testes, espelhando a estrutura de autoseguro/
docs/             PRD, RFCs, ADRs, FDDs, rastreabilidade e tasks.md
system-design/    diagrama de arquitetura, gerado a partir de JSON
```

## 7. Documentação e decisões

Toda decisão de arquitetura ou de regra de negócio está em `docs/`, nesta ordem de abstração: PRD, RFCs, ADRs e FDDs. Antes de mudar um componente, leia o FDD correspondente. O arquivo `docs/rastreabilidade.md` registra cada alteração dos documentos e a decisão que a motivou.

O arquivo `docs/tasks.md` lista as dúvidas e os desvios que surgiram na implementação, com a decisão tomada e o status de cada item. Ele serve de base para a revisão final.

### Diagrama de arquitetura

O diagrama fica em `system-design/`, em duas versões: `autoseguro-system-design-geral.html`, com todos os documentos, e `autoseguro-system-design-aprovado.html`, só com o que foi aprovado. Os dois são gerados a partir de `system-design/autoseguro-system-design.json` e das subpáginas em `system-design/subsistemas/`.

Para validar os documentos e o diagrama:

```bash
python3 .claude/skills/system-design/scripts/aprovacoes.py
python3 .claude/skills/system-design/scripts/gerar.py --so-validar
```

## 8. Convenções de desenvolvimento

- Documentação, comentários e mensagens de commit são em português.
- Valores monetários usam `Decimal`, nunca ponto flutuante.
- Datas são guardadas em UTC e exibidas em horário de Brasília.
- Identificadores são UUID. As regras do catálogo usam UUID v5, para que recarregar o catálogo não crie identificadores novos.
- Logs são JSON e nunca contêm o texto digitado pelo lead nem a resposta do agente.
- Nenhuma consulta SQL monta texto por interpolação. Sempre use parâmetros do driver.
- O `.env` nunca é commitado. Revise `ai-logs/` antes de qualquer commit.

## 9. Alterando o catálogo

A fonte oficial das regras é `quote-service/data/plans.json`. Para mudar uma regra:

1. Edite o `plans.json`, ou consulte antes a equipe, porque a tabela é a fonte da cotação.
2. Rode `uv run --env-file .env python -m autoseguro.catalogo`.
3. Se uma frase de regra mudou, aumente `VERSAO_TEXTOS` em `autoseguro/catalogo/config.py`. Assim, todos os trechos daquele tipo são recalculados na próxima carga.
4. Refaça os casos de recuperação com `uv run pytest tests/recuperacao`.

Uma regra removida do `plans.json` não é apagada. Ela fica inativa e sai da busca.

## 10. Solução de problemas

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| "Banco indisponível" ao rodar qualquer comando | O serviço `banco` não está no ar ou `DATABASE_URL` está errada. | Rode `docker compose ps` e confira a URL no `.env`. |
| `docker compose` reclama de variável não definida | Faltam `POSTGRES_*` no `.env`. | Preencha as três variáveis, conforme o `.env.example`. |
| Carga do catálogo falha ao baixar o modelo | Não há internet, e o modelo ainda não está em `database/modelos`. | Rode de novo com internet. O download acontece uma vez. |
| `Permission denied` em `database/modelos` | `database/` está com outro dono. | Ajuste o dono da pasta `database/`, sem `-R`, para não afetar o Postgres. Ou use `AUTOSEGURO_MODELOS`. |
| Todas as cotações falham | O serviço `quote-api` não está no ar, ou a taxa de falhas está alta. | Rode `docker compose up -d quote-api`. Os valores de falha estão em `docker-compose.yml`. |
| Modo `agente` responde com erro | Chave da Anthropic ausente ou inválida. | Confira `ANTHROPIC_API_KEY` no `.env`. |
| "turno em andamento" persiste | Uma execução caiu no meio de um turno. | Aguarde 15 minutos, ou libere a trava pelo banco. |

## 11. Limitações conhecidas

- O tracing com o LangSmith ainda não foi verificado de ponta a ponta, porque depende da chave da conta.
- O pedido de humano e a desistência são detectados por listas fixas de frases.
- O juiz verifica valores por expressão regular. Um número com separador decimal fora da cotação, como um multiplicador, reprova a resposta.
- O nome do lead não é mascarado, conforme a RFC-0008.
- O modelo de embeddings tem parâmetros HNSW nos padrões do pgvector.
- O consumo do modelo do juiz no teto é contado, mas o consumo das tentativas que falharam não entra.
- Os textos dos roteiros foram revisados, mas o tom final depende do produto.

## 12. Referências

- `docs/prd/prd-0001-agente-de-cotacao.md`: requisitos e metas.
- `docs/fdd/`: comportamento de cada componente.
- `docs/rastreabilidade.md`: histórico das decisões.
- `docs/tasks.md`: dúvidas, desvios e status da implementação.
