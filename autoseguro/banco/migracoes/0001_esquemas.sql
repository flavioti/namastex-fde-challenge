-- Esquemas e extensão vetorial (FDD-0004, seção 4).
-- O esquema agente é usado pelo checkpoint do LangGraph, que cria suas próprias tabelas.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS registro;
CREATE SCHEMA IF NOT EXISTS regras;
CREATE SCHEMA IF NOT EXISTS agente;
