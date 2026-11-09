-- Tabelas do registro (FDD-0004, seção 5). Chaves UUID e datas em timestamptz (UTC).

CREATE TABLE registro.conversas (
    id uuid PRIMARY KEY,
    nome_lead text NOT NULL,
    telefone_lead text NOT NULL,
    status text NOT NULL CHECK (status IN ('em_andamento', 'cotada', 'encaminhada', 'encerrada')),
    criada_em timestamptz NOT NULL,
    atualizada_em timestamptz NOT NULL,
    turno_em_andamento_desde timestamptz
);

CREATE TABLE registro.mensagens (
    id uuid PRIMARY KEY,
    conversa_id uuid NOT NULL REFERENCES registro.conversas (id),
    ordem integer NOT NULL,
    papel text NOT NULL CHECK (papel IN ('lead', 'agente')),
    conteudo_mascarado text NOT NULL,
    criada_em timestamptz NOT NULL
);

CREATE TABLE registro.cotacoes (
    id uuid PRIMARY KEY,
    conversa_id uuid NOT NULL REFERENCES registro.conversas (id),
    resultado text NOT NULL CHECK (resultado IN ('sucesso', 'recusada', 'indisponivel', 'payload_invalido')),
    planos jsonb,
    motivo text,
    consultada_em timestamptz NOT NULL
);

CREATE TABLE registro.encaminhamentos (
    id uuid PRIMARY KEY,
    conversa_id uuid NOT NULL REFERENCES registro.conversas (id),
    motivo text NOT NULL,
    resumo text NOT NULL,
    cpf text,
    criado_em timestamptz NOT NULL
);

CREATE TABLE registro.referencias_trace (
    conversa_id uuid PRIMARY KEY REFERENCES registro.conversas (id),
    trace_id text NOT NULL
);

CREATE TABLE registro.resultados_avaliacao (
    id uuid PRIMARY KEY,
    rodada text NOT NULL,
    caso text NOT NULL,
    regra text NOT NULL CHECK (regra IN ('R1', 'R2', 'R3', 'R4')),
    aprovado boolean NOT NULL,
    motivo text,
    criado_em timestamptz NOT NULL
);
