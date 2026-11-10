"""Catálogo real carregado com o modelo e5 num banco de teste (ADR-0004, RFC-0003)."""

from __future__ import annotations

import psycopg
import pytest

from autoseguro.catalogo.carga import sincronizar
from autoseguro.catalogo.config import ARQUIVO_PLANS
from autoseguro.catalogo.embeddings import ErroModelo, EmbedderE5


@pytest.fixture(scope="module")
def catalogo_com_modelo(url_banco):
    """Carrega o catálogo com o modelo real. Se o modelo não estiver disponível, pula os casos."""
    embedder = EmbedderE5()
    try:
        embedder.gerar(["query: teste"])
    except ErroModelo as erro:
        pytest.skip(f"modelo de embeddings indisponível: {erro}")
    with psycopg.connect(url_banco) as conexao:
        sincronizar(conexao, embedder, ARQUIVO_PLANS)
        conexao.commit()
    return url_banco, embedder
