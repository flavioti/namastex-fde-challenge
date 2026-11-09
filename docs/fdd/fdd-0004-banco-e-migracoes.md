---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0004 — Banco de dados, migrações e busca híbrida

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0003-banco-postgres-pgvector]] |
| **Documentos relacionados** | [[adr-0002-acesso-banco-e-migracoes]] · [[adr-0004-indice-vetorial-e-metrica]] · [[adr-0005-busca-hibrida-rrf]] · [[adr-0009-identificadores-uuid]] · [[adr-0010-valores-monetarios-decimal]] · [[adr-0012-datas-utc-e-exibicao-brasil]] · [[adr-0018-mensagens-em-tabela-propria]] · [[fdd-0002-cliente-da-cotacao]] · [[fdd-0003-mascaramento-de-dados-pessoais]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve esquemas, tabelas, índices, migrações, pool de conexões, consultas de busca e testes do banco.

## 1. Escopo

O banco guarda três áreas, em uma única instância Postgres:

- **Registro**, com conversas, mensagens, cotações, encaminhamentos, referências de trace e resultados de avaliação.
- **Regras**, com o catálogo de planos e regras, e os trechos com embeddings e busca textual.
- **Agente**, com as tabelas de checkpoint do LangGraph, gerenciadas pela própria biblioteca.

## 2. Stack e dependências

| Item | Escolha | Referência |
| --- | --- | --- |
| Banco | Postgres, versão mais recente estável com pgvector | [[rfc-0003-banco-postgres-pgvector]] |
| Driver | psycopg 3 | [[adr-0002-acesso-banco-e-migracoes]] |
| Pool | `psycopg_pool`, compartilhado pela aplicação | Decisão do usuário |
| Vetores | Pacote `pgvector`, para registrar o tipo com o psycopg | [[adr-0004-indice-vetorial-e-metrica]] |
| Migrações | Arquivos SQL numerados, aplicados por script | [[adr-0002-acesso-banco-e-migracoes]] |
| Testes | pytest, com banco real em contêiner de teste | [[adr-0016-biblioteca-de-testes-pytest]] |

A versão maior do Postgres é fixada no `docker-compose.yml` na implementação, e não usa a tag `latest`, conforme a [[rfc-0012-ambiente-de-execucao]].

## 3. Estrutura de arquivos

```
autoseguro/
  banco/
    __init__.py
    conexao.py          pool de conexões e contexto de transação
    migrar.py           aplica os arquivos de migração em ordem
    migracoes/
      0001_esquemas.sql
      0002_registro.sql
      0003_regras.sql
      0004_indices.sql
    repositorios/
      conversas.py
      mensagens.py
      cotacoes.py
      encaminhamentos.py
      avaliacoes.py
      regras.py
      trechos.py
    busca.py            consulta híbrida de trechos
tests/
  banco/
    test_migracoes.py
    test_repositorios.py
    test_busca.py
```

## 4. Esquemas

| Esquema | Dono | Conteúdo |
| --- | --- | --- |
| `registro` | Aplicação | Dados de negócio e histórico da simulação |
| `regras` | Aplicação | Catálogo de planos e regras, trechos e vetores |
| `agente` | Biblioteca do LangGraph | Checkpoint do estado do grafo |

O esquema `agente` é criado pela migração 0001. As tabelas dentro dele são criadas pela própria biblioteca, na primeira execução. A aplicação não altera essas tabelas.

## 5. Tabelas do registro

Todas as chaves primárias são UUID, conforme a [[adr-0009-identificadores-uuid]]. Todas as datas são `timestamptz`, em UTC, conforme a [[adr-0012-datas-utc-e-exibicao-brasil]].

**`registro.conversas`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `nome_lead` | text | Nome fictício, gerado pela simulação |
| `telefone_lead` | text | Telefone fictício, gerado pela simulação |
| `status` | text | Um de `em_andamento`, `cotada`, `encaminhada` ou `encerrada` |
| `criada_em` | timestamptz | Obrigatória |
| `atualizada_em` | timestamptz | Obrigatória |
| `turno_em_andamento_desde` | timestamptz, opcional | Preenchida enquanto um turno da conversa está em execução. Nula quando livre. Usada pela trava da interface |

**`registro.mensagens`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `conversa_id` | uuid | Referência a `registro.conversas`, sem exclusão em cascata |
| `ordem` | integer | Única dentro da conversa |
| `papel` | text | `lead` ou `agente` |
| `conteudo_mascarado` | text | Texto já mascarado, conforme a [[fdd-0003-mascaramento-de-dados-pessoais]] |
| `criada_em` | timestamptz | Obrigatória |

**`registro.cotacoes`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `conversa_id` | uuid | Referência a `registro.conversas` |
| `resultado` | text | Um de `sucesso`, `recusada`, `indisponivel` ou `payload_invalido` |
| `planos` | jsonb, opcional | Planos cotados, sem CEP |
| `motivo` | text, opcional | Motivo da recusa ou da falha |
| `consultada_em` | timestamptz | Obrigatória |

**`registro.encaminhamentos`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `conversa_id` | uuid | Única. Uma conversa tem no máximo um encaminhamento |
| `motivo` | text | Um dos motivos da [[fdd-0001-fluxo-de-conversa-e-coleta]] |
| `resumo` | text | Resumo para o vendedor |
| `cpf` | text, opcional | Sem máscara, conforme a RF-10 do PRD |
| `criado_em` | timestamptz | Obrigatória |

**`registro.referencias_trace`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `conversa_id` | uuid | Chave primária e referência a `registro.conversas` |
| `trace_id` | text | Obrigatório |

**`registro.resultados_avaliacao`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `rodada` | text | Identificador da rodada de avaliação |
| `caso` | text | Identificador do caso |
| `regra` | text | Regra avaliada, de R1 a R4 |
| `aprovado` | boolean | Obrigatório |
| `motivo` | text, opcional | Motivo da reprovação |
| `criado_em` | timestamptz | Obrigatória |

## 6. Tabelas de regras

**`regras.planos`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | text | Chave primária: `essencial`, `completo` ou `premium` |
| `nome` | text | Obrigatório |
| `base_mensal` | numeric(12,2) | Conforme a [[adr-0010-valores-monetarios-decimal]] |
| `franquia` | numeric(12,2) | Conforme a [[adr-0010-valores-monetarios-decimal]] |
| `coberturas` | text[] | Obrigatória |

**`regras.regras`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `tipo` | text | Um de `faixa_etaria`, `idade_veiculo`, `regiao_cep`, `carencia` ou `pro_rata` |
| `dados` | jsonb | Parâmetros da regra, vindos de `plans.json` |
| `impressao_digital` | text | Hash do conteúdo, para detectar mudança na carga |
| `ativa` | boolean | Padrão verdadeiro. Falso quando a regra sai do `plans.json`, sem ser apagada |

**`regras.trechos`**

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | uuid | Chave primária |
| `regra_id` | uuid | Referência a `regras.regras` |
| `texto` | text | Trecho em português, derivado da regra |
| `texto_busca` | tsvector | Gerado pelo Postgres a partir de `texto`, com configuração em português |
| `embedding` | vector(384) | Vetor do modelo local |
| `modelo_id` | text | Identificador do modelo usado |
| `dimensao` | integer | Igual a 384 |
| `impressao_digital` | text | Hash do texto, para recalcular só o que mudou |
| `gerado_em` | timestamptz | Obrigatória |

A coluna `texto_busca` é gerada pelo próprio Postgres, conforme a decisão do usuário. Não há trigger.

## 7. Índices

| Tabela | Índice | Finalidade |
| --- | --- | --- |
| `regras.trechos` | GIN sobre `texto_busca` | Busca textual |
| `regras.trechos` | HNSW sobre `embedding`, com `vector_cosine_ops` | Busca vetorial por cosseno |
| `registro.mensagens` | Único sobre `(conversa_id, ordem)` | Ordem das mensagens |
| `registro.encaminhamentos` | Único sobre `conversa_id` | Um encaminhamento por conversa |
| `registro.cotacoes` | Sobre `(conversa_id, consultada_em)` | Consulta do histórico |

## 8. Migrações

- Cada arquivo SQL roda em uma transação própria.
- A tabela `public.migracoes_aplicadas` guarda o nome de cada arquivo aplicado e a data.
- O script `migrar.py` lê os arquivos em ordem numérica, pula os já aplicados e para no primeiro erro.
- Rodar o script duas vezes não altera o banco.
- Nenhuma migração apaga dados. Mudanças destrutivas exigem um novo arquivo com justificativa no cabeçalho.

## 9. Conexões

- A aplicação abre um pool no início, com tamanho mínimo de 1 e máximo de 5 conexões.
- Cada operação pega uma conexão do pool e a devolve ao fim do bloco.
- Cada turno da conversa é uma transação. Se o turno falhar, nada é gravado parcialmente.
- A URL de conexão vem de `DATABASE_URL`, no `.env`.
- O pool é fechado ao fim da execução.

## 10. Consultas

Todas as consultas usam parâmetros do driver. Nenhuma consulta monta SQL com interpolação de texto.

**Busca híbrida**

A função `busca.buscar_trechos` considera apenas trechos de regras com `ativa` verdadeiro. Recebe o texto da consulta, o vetor da consulta, um limite `k` e um filtro opcional por tipo de regra. Ela executa:

1. uma busca textual, com `plainto_tsquery` na configuração portuguesa, ordenada por `ts_rank`, com até 20 candidatos;
2. uma busca vetorial, ordenada pela distância cosseno, com até 20 candidatos;
3. a fusão dos dois rankings por RRF, com a soma de `1 / (60 + posição)` em cada lista.

O resultado é ordenado pela pontuação fundida e limitado a `k` trechos. A constante 60 é o valor padrão do RRF, e fica em configuração para ajuste nos testes, conforme a [[adr-0005-busca-hibrida-rrf]].

**Carga do catálogo**

A carga lê `plans.json`, calcula a impressão digital de cada regra e de cada trecho, e atualiza apenas os trechos cuja impressão digital mudou, conforme a [[rfc-0004-geracao-de-embeddings]].

## 11. Erros

| Situação | Tratamento |
| --- | --- |
| Banco indisponível na abertura do pool | Erro explícito na inicialização, com mensagem para o avaliador |
| Violação de chave única | Erro de programação. Não é tratado como caso de negócio |
| Dimensão de vetor diferente de 384 | Falha na carga, antes de gravar |
| Falha em transação de turno | Transação revertida. O turno é encaminhado conforme a [[fdd-0001-fluxo-de-conversa-e-coleta]] |

## 12. Testes

Os testes de banco rodam contra uma instância Postgres real, em contêiner de teste, com o mesmo pgvector da aplicação. Cada execução cria um banco novo.

| Arquivo | O que verifica |
| --- | --- |
| `test_migracoes.py` | Aplicação em ordem, reexecução sem efeito e registro em `migracoes_aplicadas` |
| `test_repositorios.py` | Restrições: status válido, ordem única de mensagens, um encaminhamento por conversa e papel válido |
| `test_busca.py` | Termo exato encontrado pela parte textual, sinônimo encontrado pela parte vetorial e fusão por RRF com ordem esperada |

**Casos de busca**

- Consulta com o termo "pro-rata" retorna o trecho de pro-rata entre os primeiros.
- Consulta por um sinônimo retorna o trecho pela parte vetorial.
- Filtro por tipo de regra não retorna trechos de outros tipos.
- Trecho com `impressao_digital` igual não é regravado na carga.

## 13. Critérios de aceite técnicos

1. As quatro migrações aplicam em ordem e podem ser reexecutadas sem alterar o banco.
2. Toda tabela de registro usa UUID como chave primária e `timestamptz` para datas.
3. Valores monetários usam `numeric(12,2)`, nunca ponto flutuante.
4. A coluna `texto_busca` é gerada pelo Postgres e nunca é escrita pela aplicação.
5. A busca híbrida retorna os casos da seção 12.
6. Nenhuma consulta usa interpolação de texto.
7. O encaminhamento guarda o CPF sem máscara, e as mensagens guardam apenas o texto mascarado.

## 14. Decisões de versão e ranking

- **Versão do Postgres:** a versão maior mais recente estável, validada com pgvector na implementação. A versão exata é fixada no compose.
- **Constante do RRF:** 60, o valor padrão, ajustável nos testes de busca.

## 15. Decisões relacionadas

- [[rfc-0003-banco-postgres-pgvector]]: decisões de banco, esquemas e busca.
- [[rfc-0004-geracao-de-embeddings]]: carga e recálculo dos trechos.
- [[adr-0002-acesso-banco-e-migracoes]]: driver e migrações.
- [[adr-0005-busca-hibrida-rrf]]: fusão dos rankings.
