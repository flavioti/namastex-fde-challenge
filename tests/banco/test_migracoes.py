"""Migrações: ordem, reexecução sem efeito e esquema resultante (FDD-0004, seção 12)."""

from __future__ import annotations

from autoseguro.banco.migrar import aplicar_migracoes, listar_migracoes


def test_migracoes_registradas_em_ordem(conexao):
    nomes = [linha[0] for linha in conexao.execute(
        "SELECT nome FROM public.migracoes_aplicadas ORDER BY nome"
    ).fetchall()]
    esperados = [arquivo.name for arquivo in listar_migracoes()]
    assert nomes == esperados
    assert nomes == [
        "0001_esquemas.sql",
        "0002_registro.sql",
        "0003_regras.sql",
        "0004_indices.sql",
    ]


def test_reexecucao_nao_aplica_nada(url_banco):
    assert aplicar_migracoes(url_banco) == []


def test_esquemas_criados(conexao):
    esquemas = {linha[0] for linha in conexao.execute(
        "SELECT schema_name FROM information_schema.schemata"
    ).fetchall()}
    assert {"registro", "regras", "agente"} <= esquemas


def test_tabelas_do_registro_e_regras_existem(conexao):
    tabelas = {(linha[0], linha[1]) for linha in conexao.execute(
        "SELECT table_schema, table_name FROM information_schema.tables "
        "WHERE table_schema IN ('registro', 'regras')"
    ).fetchall()}
    assert tabelas == {
        ("registro", "conversas"),
        ("registro", "mensagens"),
        ("registro", "cotacoes"),
        ("registro", "encaminhamentos"),
        ("registro", "referencias_trace"),
        ("registro", "resultados_avaliacao"),
        ("regras", "planos"),
        ("regras", "regras"),
        ("regras", "trechos"),
    }


def test_extensao_vector_instalada(conexao):
    existe = conexao.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'").fetchone()
    assert existe is not None
