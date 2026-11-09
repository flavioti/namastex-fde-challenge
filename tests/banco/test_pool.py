"""Pool de conexões: abre, entrega conexões utilizáveis e falha com mensagem clara (FDD-0004, seção 9 e 11)."""

from __future__ import annotations

import pytest

from autoseguro.banco.conexao import MENSAGEM_BANCO_INDISPONIVEL, BancoIndisponivel, abrir_pool


def test_pool_entrega_conexoes_utilizaveis(url_banco):
    pool = abrir_pool(url_banco)
    try:
        for _ in range(3):
            with pool.connection() as conexao:
                assert conexao.execute("SELECT 1").fetchone()[0] == 1
        with pool.connection() as conexao:
            assert conexao.execute(
                "SELECT count(*) FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()[0] == 1
    finally:
        pool.close()


def test_banco_inacessivel_gera_mensagem_para_o_avaliador():
    with pytest.raises(BancoIndisponivel) as erro:
        abrir_pool("postgresql://usuario:senha@127.0.0.1:1/inexistente", timeout=2.0)
    assert str(erro.value) == MENSAGEM_BANCO_INDISPONIVEL
