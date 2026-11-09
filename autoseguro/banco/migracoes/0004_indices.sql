-- Índices (FDD-0004, seção 7).

CREATE UNIQUE INDEX mensagens_conversa_ordem_idx ON registro.mensagens (conversa_id, ordem);
CREATE UNIQUE INDEX encaminhamentos_conversa_idx ON registro.encaminhamentos (conversa_id);
CREATE INDEX cotacoes_conversa_consulta_idx ON registro.cotacoes (conversa_id, consultada_em);

CREATE INDEX trechos_texto_busca_idx ON regras.trechos USING GIN (texto_busca);
-- Parâmetros do HNSW ficam nos padrões do pgvector nesta fase (ADR-0004).
CREATE INDEX trechos_embedding_idx ON regras.trechos USING hnsw (embedding vector_cosine_ops);
