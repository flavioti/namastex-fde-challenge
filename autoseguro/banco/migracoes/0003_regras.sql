-- Catálogo de planos, regras e trechos vetorizados (FDD-0004, seção 6).

CREATE TABLE regras.planos (
    id text PRIMARY KEY CHECK (id IN ('essencial', 'completo', 'premium')),
    nome text NOT NULL,
    base_mensal numeric(12, 2) NOT NULL,
    franquia numeric(12, 2) NOT NULL,
    coberturas text[] NOT NULL
);

CREATE TABLE regras.regras (
    id uuid PRIMARY KEY,
    tipo text NOT NULL CHECK (tipo IN ('faixa_etaria', 'idade_veiculo', 'regiao_cep', 'carencia', 'pro_rata')),
    dados jsonb NOT NULL,
    impressao_digital text NOT NULL,
    ativa boolean NOT NULL DEFAULT true
);

-- A coluna texto_busca é gerada pelo Postgres. A aplicação nunca a escreve (FDD-0004, seção 6).
CREATE TABLE regras.trechos (
    id uuid PRIMARY KEY,
    regra_id uuid NOT NULL REFERENCES regras.regras (id),
    texto text NOT NULL,
    texto_busca tsvector GENERATED ALWAYS AS (to_tsvector('portuguese'::regconfig, texto)) STORED,
    embedding vector(384) NOT NULL,
    modelo_id text NOT NULL,
    dimensao integer NOT NULL CHECK (dimensao = 384),
    impressao_digital text NOT NULL,
    gerado_em timestamptz NOT NULL
);
