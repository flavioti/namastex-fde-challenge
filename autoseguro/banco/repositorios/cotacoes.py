"""Histórico de cotações da conversa (FDD-0004 seção 5). Os planos gravados não trazem CEP."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

RESULTADOS_VALIDOS = ("sucesso", "recusada", "indisponivel", "payload_invalido")


def registrar_cotacao(
    conexao: Connection,
    conversa_id: uuid.UUID,
    resultado: str,
    planos: list[dict] | None = None,
    motivo: str | None = None,
    agora: datetime | None = None,
) -> uuid.UUID:
    if resultado not in RESULTADOS_VALIDOS:
        raise ValueError(f"resultado inválido: {resultado!r}")
    cotacao_id = uuid.uuid4()
    conexao.execute(
        "INSERT INTO registro.cotacoes (id, conversa_id, resultado, planos, motivo, consultada_em) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            cotacao_id,
            conversa_id,
            resultado,
            Jsonb(planos) if planos is not None else None,
            motivo,
            agora or datetime.now(timezone.utc),
        ),
    )
    return cotacao_id


def listar_cotacoes(conexao: Connection, conversa_id: uuid.UUID) -> list[dict]:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM registro.cotacoes WHERE conversa_id = %s ORDER BY consultada_em",
            (conversa_id,),
        )
        return cur.fetchall()

