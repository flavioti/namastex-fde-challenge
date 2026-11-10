---
tipo: fdd
status: aprovado
data: 2026-11-09
---

# FDD-0008 — Carga do catálogo de regras e geração de embeddings

| Campo | Valor |
| --- | --- |
| **Autor** | Paulo (Tech Lead) |
| **Status** | Aprovado |
| **Data** | 2026-11-09 |
| **Revisores** | João (Product Manager) |
| **Origem** | [[rfc-0004-geracao-de-embeddings]] |
| **Documentos relacionados** | [[rfc-0003-banco-postgres-pgvector]] · [[rfc-0006-servico-de-cotacao]] · [[rfc-0012-ambiente-de-execucao]] · [[adr-0003-modelo-de-embeddings]] · [[adr-0004-indice-vetorial-e-metrica]] · [[adr-0010-valores-monetarios-decimal]] · [[adr-0014-recalculo-na-troca-de-modelo]] · [[fdd-0004-banco-e-migracoes]] |

> **Nível deste documento.** Este FDD é de baixo nível e serve de base para a implementação. Descreve como `plans.json` vira linhas no banco, como cada trecho é montado e embedado, como as mudanças são detectadas e como a carga é testada.

## 1. Escopo

A carga lê `quote-service/data/plans.json`, a fonte oficial das regras, e sincroniza o catálogo do banco com esse arquivo. Para cada regra, monta um trecho de texto, gera o vetor e grava no banco. Só o que mudou é recalculado.

A carga é executada por comando explícito do avaliador. Nada é carregado automaticamente ao subir a aplicação.

## 2. Stack e dependências

| Item | Escolha | Referência |
| --- | --- | --- |
| Modelo de embeddings | `multilingual-e5-small`, 384 dimensões | [[adr-0003-modelo-de-embeddings]] |
| Biblioteca de inferência | `sentence-transformers`, na versão do lock | [[rfc-0004-geracao-de-embeddings]] |
| Banco | `psycopg` com o pool do FDD-0004 | [[fdd-0004-banco-e-migracoes]] |
| Valores monetários | `Decimal` com duas casas | [[adr-0010-valores-monetarios-decimal]] |
| Impressão digital | SHA-256 da representação canônica | Padrão da biblioteca `hashlib` |
| Testes | pytest, com um embedder substituto | [[adr-0016-biblioteca-de-testes-pytest]] |

O modelo é baixado uma vez para o diretório de modelos dentro do volume `database/`, conforme a [[rfc-0012-ambiente-de-execucao]]. O diretório é definido como constante em `config.py`.

## 3. Estrutura de arquivos

```
autoseguro/
  catalogo/
    __init__.py
    config.py          caminhos, nome do modelo, dimensão esperada e diretório de cache
    fonte.py           leitura e validação de plans.json
    regras.py          extração das regras e chaves estáveis
    textos.py          modelos de frase por tipo de regra
    embeddings.py      embedder do e5, com prefixo de documento
    carga.py           sincronização: planos, regras, trechos e desativação
    __main__.py        comando de linha de comando
tests/
  catalogo/
    test_fonte.py
    test_textos.py
    test_carga.py
```

O comando de carga é executado com `python -m autoseguro.catalogo`.

## 4. Fonte

`plans.json` tem três partes, e a carga lê cada uma:

| Parte | Conteúdo | Destino |
| --- | --- | --- |
| `planos` | Três planos, com nome, preço base, franquia e coberturas | `regras.planos` |
| `regras.faixa_etaria` | Cinco faixas, uma delas com recusa | Uma regra por faixa, `tipo` igual a `faixa_etaria` |
| `regras.idade_veiculo` | Quatro faixas, uma delas com recusa | Uma regra por faixa, `tipo` igual a `idade_veiculo` |
| `regras.regiao_cep` | Prefixos de alto risco e multiplicador | Uma regra, `tipo` igual a `regiao_cep` |
| `regras.carencia` | Coberturas com carência e dias | Uma regra, `tipo` igual a `carencia` |
| `regras.entrada_meio_mes` | Regra de pro-rata | Uma regra, `tipo` igual a `pro_rata` |

A validação de `fonte.py` confere os campos obrigatórios e os tipos antes de qualquer gravação. Um arquivo inválido interrompe a carga antes de qualquer alteração no banco. Preços são lidos como `Decimal`, conforme a [[adr-0010-valores-monetarios-decimal]].

## 5. Chaves estáveis

Cada regra tem um identificador UUID derivado de uma chave textual, com UUID v5 e um namespace fixo do projeto. A chave é formada pelo tipo e pelos limites da faixa, como `faixa_etaria:18-24` ou `regiao_cep`.

Assim, recarregar o catálogo não cria identificadores novos para regras que continuam existindo. O histórico de cotações antigas continua apontando para a mesma regra.

## 6. Textos dos trechos

Cada tipo de regra tem um modelo de frase fixo em `textos.py`. O texto é preenchido com os valores da regra e nunca é escrito à mão.

| Tipo | Modelo |
| --- | --- |
| `faixa_etaria` | Para motorista com idade de {idade_min} a {idade_max} anos, o multiplicador do prêmio é {multiplicador}. |
| `faixa_etaria`, com recusa | Não é possível cotar para idade de {idade_min} a {idade_max} anos. {motivo} |
| `idade_veiculo` | Para veículo com {anos_min} a {anos_max} anos, o multiplicador do prêmio é {multiplicador}. |
| `idade_veiculo`, com recusa | Não é possível cotar veículo com {anos_min} a {anos_max} anos. {motivo} |
| `regiao_cep` | CEPs com os prefixos {prefixos} são de alto risco, com multiplicador {multiplicador}. |
| `carencia` | As coberturas {coberturas} têm carência de {dias} dias, contados da data de início da vigência. |
| `pro_rata` | Quando a vigência começa no meio do mês, o primeiro pagamento é proporcional aos dias restantes do mês. Os meses seguintes são integrais. |

**Revisão.** O texto de faixa etária passou a dizer "Para motorista com idade de". A versão dos textos passa a ser 2. Os casos de recuperação do ADR-0004 mostraram que a consulta "motorista de 19 anos" não encontrava a faixa de 18 a 24 anos com a redação anterior.

A versão do modelo de frase faz parte da impressão digital do trecho. Mudar uma frase exige recalcular os trechos desse tipo, mesmo que os valores não tenham mudado.

## 7. Impressões digitais

- **Impressão digital da regra:** SHA-256 da representação canônica de `dados`, em JSON com chaves ordenadas e sem espaços.
- **Impressão digital do trecho:** SHA-256 da concatenação do texto do trecho, do identificador do modelo e da versão dos modelos de frase.

A impressão digital de um trecho é comparada com a gravada no banco. Se forem iguais, o trecho é pulado.

## 8. Algoritmo da carga

A carga inteira roda em uma única transação.

1. Lê e valida `plans.json`.
2. Grava ou atualiza os três planos em `regras.planos`.
3. Para cada regra do arquivo, calcula a chave estável e a impressão digital. Cria a regra se não existir, ou atualiza `dados`, `impressao_digital` e `ativa` se mudou. Marca como ativa.
4. Marca como inativa toda regra do banco cuja chave não apareceu no arquivo. Os trechos dessas regras continuam gravados, mas saem da busca.
5. Para cada regra ativa, monta o texto do trecho e calcula a impressão digital do trecho.
6. Compara com o trecho existente. Se for igual, pula. Se for diferente ou novo, acumula para embedar.
7. Gera os embeddings em lote, com o embedder do e5, e grava os trechos alterados.
8. Confere a dimensão de cada vetor, que deve ser 384. Se não for, a transação é revertida.
9. Confirma a transação e emite o relatório: planos gravados, regras criadas, atualizadas, inalteradas e desativadas, e trechos reembedados.

Se qualquer etapa falhar, nada é gravado. O relatório mostra a etapa e o erro.

## 9. Embeddings

- Os textos dos trechos são precedidos do prefixo `passage: `, conforme exigido pelo modelo e5 para documentos.
- As consultas da busca, definidas no FDD-0004, são precedidas de `query: `. Esse prefixo é responsabilidade da busca, e não desta carga.
- Os vetores são normalizados antes da gravação, para que a distância cosseno seja equivalente ao produto interno.
- O modelo é carregado uma vez por execução da carga.

## 10. Recálculo na troca de modelo

Os trechos guardam o identificador e a dimensão do modelo, conforme a [[adr-0014-recalculo-na-troca-de-modelo]]. Se o modelo configurado for diferente do identificador gravado em algum trecho, a carga recalcula todos os trechos, e não só os alterados.

## 11. Erros

| Situação | Tratamento |
| --- | --- |
| `plans.json` ausente ou inválido | Interrompe antes de qualquer gravação |
| Modelo não encontrado no diretório de cache | Tenta baixar. Se falhar, interrompe com mensagem clara |
| Dimensão de vetor diferente de 384 | Reverte a transação |
| Falha no banco | Reverte a transação e mostra o erro |

## 12. Testes

Os testes usam um banco real, do FDD-0004, e um embedder substituto que devolve vetores determinísticos de 384 posições. Nenhum modelo real é carregado nos testes.

| Arquivo | O que verifica |
| --- | --- |
| `test_fonte.py` | Validação de campos obrigatórios e rejeição de arquivo inválido |
| `test_textos.py` | Cada tipo de regra gera a frase esperada, inclusive a de recusa |
| `test_carga.py` | Carga inicial, reexecução, alteração de um valor, remoção, falha e dimensão |

**Casos de carga**

- Carga inicial cria três planos e doze regras, com doze trechos embedados.
- Reexecução sem mudança não chama o embedder.
- Alterar um único valor recalcula apenas o trecho desse valor.
- Remover uma faixa do arquivo deixa a regra inativa, e ela não aparece na busca.
- Falha do embedder no meio da carga não grava nada.
- Vetor de dimensão diferente de 384 reverte a transação.
- Recarregar o catálogo mantém os mesmos identificadores de regra.

## 13. Critérios de aceite técnicos

1. A carga é idempotente: uma segunda execução sem mudança não altera nenhuma linha de trecho.
2. Cada regra de `plans.json` gera exatamente um trecho.
3. Nenhum trecho é embedado sem o prefixo de documento.
4. Nenhum trecho é gravado com dimensão diferente de 384.
5. Uma falha em qualquer etapa não deixa o banco parcialmente alterado.
6. Os identificadores das regras são estáveis entre cargas.
7. Os casos da seção 12 passam sem carregar o modelo real.

## 14. Decisões de texto e crescimento

- **Frase de recusa.** A recusa usa frase própria, com o motivo do `plans.json` como complemento.
- **Crescimento do catálogo.** A carga inicial não tem paginação. Com o tamanho atual, a carga é rápida. Se o catálogo crescer muito, a carga passa a ser revisada.

## 15. Decisões relacionadas

- [[rfc-0004-geracao-de-embeddings]]: unidade de embedding, gatilho e recálculo.
- [[rfc-0003-banco-postgres-pgvector]]: catálogo e trechos no banco.
- [[fdd-0004-banco-e-migracoes]]: tabelas `regras.planos`, `regras.regras` e `regras.trechos`.
- [[adr-0014-recalculo-na-troca-de-modelo]]: regra de recálculo na troca de modelo.
