"""Trava de turno por conversa, gravada no banco (FDD-0007, seção 7; FDD-0004, seção 5)."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from psycopg_pool import ConnectionPool

from autoseguro.banco.repositorios import conversas


class TravaOcupada(RuntimeError):
    """Já existe um turno em andamento nesta conversa."""


@contextmanager
def turno_travado(pool: ConnectionPool, conversa_id: uuid.UUID, agora: datetime | None = None) -> Iterator[None]:
    """Adquire a trava, executa o bloco e libera a trava mesmo em erro (FDD-0007, seção 6, passo 6)."""
    with pool.connection() as conexao:
        adquirida = conversas.adquirir_trava(conexao, conversa_id, agora=agora)
    if not adquirida:
        raise TravaOcupada("turno em andamento")
    try:
        yield
    finally:
        with pool.connection() as conexao:
            conversas.liberar_trava(conexao, conversa_id)
