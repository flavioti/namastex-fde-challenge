---
name: system-design
description: Atualiza e gera de novo o system design visual do AutoSeguro (HTML animado em cenas, widescreen, em duas versões paralelas: system-design/autoseguro-system-design-geral.html, com documentos aprovados e não aprovados, e system-design/autoseguro-system-design-aprovado.html, só com o que foi aprovado) a partir dos PRDs, RFCs, ADRs e FDDs em docs/. Use quando o usuário pedir para atualizar, refazer ou gerar o system design ou o diagrama de arquitetura; quando um PRD, RFC, ADR ou FDD for criado, aprovado, aceito, rejeitado ou substituído e o diagrama precisar refletir isso; ou quando pedir para mudar componentes, conexões ou cenas do diagrama.
---

# System design do AutoSeguro

O diagrama representa a arquitetura do agente de cotação da AutoSeguro, descrito no `CLAUDE.md` da raiz. Os documentos de design ficam em `docs/prd/`, `docs/rfc/`, `docs/adr/` e `docs/fdd/`.

Arquivos envolvidos:

| Arquivo | Papel | Quem edita |
| --- | --- | --- |
| `system-design/autoseguro-system-design.json` | Componentes, posições, conexões, cenas e metadados. **Fonte única das duas versões** | Você, nesta skill |
| `.claude/skills/system-design/assets/template.html` | Desenho, estilo e animação | Ninguém, a menos que o usuário peça uma mudança **visual** |
| `system-design/autoseguro-system-design-geral.html` | Versão **geral**: tudo o que está no JSON, aprovados e não aprovados (decidido, proposto e futuro) | Só o script. **Nunca edite à mão** |
| `system-design/autoseguro-system-design-aprovado.html` | Versão **aprovada**: só os nós com `status: decidido` (ADR aceito) | Só o script. **Nunca edite à mão** |

### As duas versões

As duas existem em paralelo e saem do mesmo JSON, para nunca divergirem. Não mantenha um segundo JSON.

- **Geral:** o JSON inteiro, como está.
- **Aprovado:** o script filtra os nós com `status: decidido`, as conexões cujas duas pontas ficam nesses nós e as cenas que ainda têm algum nó aceso (as cenas de visão geral ficam sempre). Ele também:
  - troca o selo por `aprovado · ADR-NNNN a NNNN · AAAA-MM-DD`, com os ADRs citados em `fonte` pelos nós decididos;
  - troca a legenda da última cena por "só o que tem ADR aceito";
  - sem nenhum nó decidido, gera uma cena única "nada aprovado ainda".

Para um componente passar à versão aprovada, basta mudar o `status` dele para `decidido` e citar o ADR aceito em `fonte`. Títulos e subtítulos das cenas são os mesmos nas duas versões, então devem fazer sentido também só com os componentes decididos.

O script `scripts/gerar.py` valida o JSON, gera o HTML e, se pedido, tira uma captura por cena.

## Regeneração e aviso de documentos

Os hooks do projeto (`.claude/settings.json`) rodam os dois scripts abaixo depois de cada `Edit`, `Write` ou `Bash` do Claude e a cada mensagem do usuário. Eles também funcionam à mão.

### Pendências entre documentos e diagrama (`scripts/aprovacoes.py`)

- **O que acompanha:** todos os PRDs, RFCs, ADRs e FDDs de `docs/` (pelo frontmatter `tipo` e `status`).
- **Como compara:** confronta o status atual de cada um com `meta.documentos_status` no JSON (`{"adr-0001-exemplo": "aceito", ...}`). Avisa quando um documento é **novo**, quando o **status muda** (ex.: `rascunho` → `aprovado`, `proposto` → `aceito`) e quando um registrado **some ou é renomeado**.
- **Rastreabilidade:** avisa quando um documento acompanhado não é citado em `docs/rastreabilidade.md`. Ao aparecer esse aviso, registre o documento nesse arquivo.
- **Ao rodar a skill por causa desse aviso:**
  1. Atualize `meta.documentos_status` **logo no início**, para o aviso parar de se repetir.
  2. Siga o fluxo normal.
  3. Diga ao usuário qual mudança disparou a atualização.
- **Para conferir à mão:** `python3 .claude/skills/system-design/scripts/aprovacoes.py` (código de saída 1 se houver pendência).

### Regeneração dos HTMLs (`scripts/sincronizar.py`)

- Quando o JSON fica mais recente que algum dos dois HTMLs, o script roda o `gerar.py` (sem capturas) e regenera as versões geral e aprovada.
- Se a geração falhar, os erros aparecem na saída, e o JSON precisa ser corrigido.
- A regeneração é mecânica: ela **não** substitui a skill. Decidir o que muda no JSON, e conferir as capturas quando a mudança for visual, continua sendo trabalho do fluxo abaixo.
- **Para rodar à mão:** `python3 .claude/skills/system-design/scripts/sincronizar.py`.

## Fluxo

1. **Leia as fontes.** Leia `docs/adr/`, `docs/rfc/`, `docs/prd/` e `docs/fdd/`, além do `CLAUDE.md`. Leia também o JSON atual e veja `meta.documentos_lidos` para saber o que a versão anterior considerou.
2. **Monte a lista de mudanças antes de editar.** Para cada componente, conexão ou cena, diga o que entra, o que sai e o que muda, e cite o documento de cada item (ex.: "ADR-0003 aceito: banco de dados vira PostgreSQL → nó `postgres` passa a `decidido`"). Se a mudança for grande ou ambígua, mostre a lista ao usuário antes de aplicar.
3. **Edite o JSON** seguindo as regras abaixo.
4. **Gere e valide** (gera as duas versões):
   ```bash
   python3 .claude/skills/system-design/scripts/gerar.py --capturas tmp/system-design
   ```
   Erros interrompem a geração; corrija-os. Leia cada aviso e corrija ou justifique ao usuário. Os avisos de "sem fonte" são aceitáveis só para componentes que são propostas declaradas.
5. **Confira as capturas** em `tmp/system-design/geral/cena-NN.png` e `tmp/system-design/aprovado/cena-NN.png` (a pasta `tmp/` não é versionada). Abra **todas** e procure texto estourando a caixa, nós ou rótulos sobrepostos, linhas atravessando caixas e conexões que não acendem na cena delas. Corrija e gere de novo até ficar limpo.
6. **Registre no histórico.** Acrescente cada mudança de status em `docs/rastreabilidade.md` e atualize `meta.documentos_status`.
7. **Responda ao usuário** com a lista de mudanças, os avisos que ficaram e o caminho das duas versões. Diga se a versão aprovada mudou. Não faça commit sem pedido.

## Regras de conteúdo

- **Não invente componentes.** Todo nó novo precisa de `fonte`: wikilink curto para o documento que o justifica (`[[adr-0003-banco-de-dados]]`, `[[prd-0001-cotacao]] (RF: ...)`). Sem documento, o nó só entra como proposta explícita (`"fonte": null`, `"status": "proposto"`) e você avisa o usuário.
- **Status de cada nó**, a partir dos documentos:

  | Situação no repositório | `status` | `future` |
  | --- | --- | --- |
  | ADR com `status: aceito` | `decidido` | — |
  | ADR `proposto`, RFC em discussão ou derivação do PRD | `proposto` | — |
  | Ainda não existe, depende de terceiros ou "a confirmar" | `futuro` | `true` (fica tracejado) |
  | ADR `rejeitado` | remova o nó, salvo se outro documento o sustentar | |
  | ADR `substituido` | siga `substituido_por` e use o ADR novo | |

  O status `decidido` exige um ADR aceito citado em `fonte` (wikilink `[[adr-NNNN-...]]`); o script avisa quando falta.
- **Nomes:** use os termos definidos nos PRDs e no `CLAUDE.md`, sem sinônimos. Rótulos curtos, em minúsculas, em português (`cotação`, `agente`, `harness de PII`). Nomes de tecnologia só entram com ADR aceito (ex.: o rótulo `postgres` só com o ADR que escolheu o PostgreSQL).
- **Fatos de terceiros** sem confirmação no texto oficial levam a tag `a confirmar`.
- **Selo** (`meta.selo`, canto inferior direito):
  - sem ADR aceito: `geral · sem ADR aceito`;
  - com ADRs aceitos: `ADR-0001 a 0004 · AAAA-MM-DD`;
  - se houver nós `proposto` junto com `decidido`: `ADR-0001 a 0004 + propostas · AAAA-MM-DD`.
- Atualize `meta.atualizado` (rode `date +%F`) e `meta.documentos_lidos`.
- A última cena (visão final) termina com uma legenda que deixa claro o que está decidido. Enquanto nada tiver ADR aceito, ela deve dizer "geral · nada decidido ainda"; troque o texto quando houver ADRs aceitos.

## Formato do JSON

Exemplo ilustrativo. Os nomes são placeholders e não representam decisões tomadas.

```jsonc
{
  "meta": { "titulo": "AutoSeguro — system design", "selo": "...", "atualizado": "AAAA-MM-DD",
            "documentos_status": {"adr-0001-exemplo": "aceito"},
            "documentos_lidos": ["[[adr-0001-exemplo]]"] },
  "nodes": {
    "agente": { "type": "app", "x": 700, "y": 400, "label": "agente",
                "status": "proposto", "fonte": null },
    "quote": { "type": "ext", "x": 1100, "y": 400, "label": "quote-service", "sub": "cotação",
               "status": "decidido", "fonte": "[[adr-0001-exemplo]]" }
  },
  "edges": {
    "e_agente_quote": { "pts": [[760,400],[1050,400]] }
  },
  "scenes": [
    { "title": ["1. ", "cotação"], "sub": ["agente ", "consulta o preço"],
      "cap": "uma chamada por cotação",
      "nodes": ["agente", "quote"], "packets": ["e_agente_quote"] }
  ]
}
```

**Nós.** `x` e `y` são o centro, num quadro de 1600×900.

| `type` | Uso | Tamanho | Campos extras |
| --- | --- | --- | --- |
| `phone` | Canal do usuário (ex.: WhatsApp) | 34×54, rótulo à direita | |
| `dot` | Junção das linhas | 12×12 | sem `label` |
| `lb` | Load balancer / gateway | `w`×`h` (190×40) | `w`, `h` |
| `app` | Serviço que atende requisições (ciano, `</>`) | 120×64 | |
| `ext` | Serviço externo (LLM, API de terceiros) | `w`×`h` (96×64) | `sub` |
| `db` | Banco de dados (cilindro azul) | 110×80 | |
| `worker` | Processo em segundo plano (roxo, ⚙) | `w`×56 | `w` |
| `bucket` | Armazenamento de arquivos | 120×62 | `sub` |
| `source` | Fonte externa de dados | 150×50, tag abaixo | `tag`, `tagColor` (`green`, `muted`…) |

Todos aceitam `future: true` (tracejado), `status` e `fonte`.

**Conexões.** `pts` é uma polilinha ortogonal **na ordem do fluxo**: os pacotes andam do primeiro ponto ao último. As pontas devem ficar na borda dos nós, a no máximo 80 px na horizontal e 56 px na vertical do centro, senão a linha não acende na cena. Outros campos:
- `future: true`: tracejada;
- `hidden: true`: não é desenhada e só serve de trajeto para pacotes;
- `decorative: true`: linha sem fluxo próprio, que acende só nas cenas de visão geral.

**Cenas.** `title` e `sub` são `[texto, texto em destaque]`: no título o destaque fica em azul e no subtítulo em ciano. `cap` é a legenda em pílula, com até ~40 caracteres. `nodes` lista os nós acesos (`"*"` para todos), e `packets` lista as conexões com pacotes animados. Mantenha o padrão: cena 0 de visão geral, uma cena numerada por passo do fluxo e uma visão final.

## Layout

O quadro tem faixas fixas: o título (y < 95, centro), a legenda das cores (canto superior esquerdo, até x 270 e y 250) e o rodapé com subtítulo, pílula e selo (y > 765). O script avisa se um nó invadir alguma delas.

- Planeje as colunas antes de posicionar os nós: o fluxo principal segue da esquerda para a direita ou de cima para baixo.
- Use barramentos horizontais ou verticais para conexões que partem do mesmo ponto.
- Mantenha 6 px ou mais entre caixas; o script avisa sobre sobreposições.
- Se um quarto item entrar numa linha, redistribua as colunas e ajuste barramentos, conexões e pontas.

## Mudanças visuais

Mudanças de estilo, cor, fonte ou animação são feitas em `assets/template.html`, só quando o usuário pedir. O estilo atual usa fundo escuro, apps em ciano com `</>`, bancos em cilindro azul, processos em roxo e linhas cinza finas, com título branco com uma palavra em azul e legenda em pílula no rodapé. Preserve isso ao alterar o template.

O template precisa manter os marcadores `__TITULO__` e `/*__DADOS__*/`. Depois de mudar o template, gere de novo e confira todas as capturas.
