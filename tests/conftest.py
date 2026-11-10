"""Banco de teste compartilhado: cada execução cria um banco novo, com as migrações aplicadas (FDD-0004, seção 12)."""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from autoseguro.banco.migrar import aplicar_migracoes


@pytest.fixture(scope="session")
def url_banco():
    """URL de um banco novo, criado a partir de DATABASE_URL e removido ao fim."""
    url_servidor = os.environ.get("DATABASE_URL")
    if not url_servidor:
        pytest.skip("DATABASE_URL não definida: os testes de banco precisam do serviço 'banco' no ar")

    nome = f"autoseguro_teste_{uuid.uuid4().hex[:12]}"
    base = conninfo_to_dict(url_servidor)
    url_admin = make_conninfo(**{**base, "dbname": "postgres"})
    url_teste = make_conninfo(**{**base, "dbname": nome})

    with psycopg.connect(url_admin, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
    aplicar_migracoes(url_teste)

    yield url_teste

    with psycopg.connect(url_admin, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nome)))


@pytest.fixture
def conexao(url_banco):
    """Conexão com transação que é desfeita ao fim do teste, para isolar os dados."""
    with psycopg.connect(url_banco) as c:
        # Abre a transação antes do teste. Assim, transaction() dentro do código vira savepoint,
        # e o commit que a carga faz numa conexão ociosa não vaza para outros testes.
        c.execute("SELECT 1")
        yield c
        c.rollback()


@pytest.fixture(autouse=True)
def pasta_de_execucoes(tmp_path, monkeypatch):
    """Os testes gravam os logs de execução numa pasta temporária, nunca em execucoes/."""
    monkeypatch.setenv("AUTOSEGURO_EXECUCOES", str(tmp_path / "execucoes"))
