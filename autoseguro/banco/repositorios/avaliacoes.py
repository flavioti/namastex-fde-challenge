"""Referências de trace e resultados de avaliação (FDD-0004 seção 5; FDD-0006 seção 7)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from psycopg import Connection

REGRAS_VALIDAS = ("R1", "R2", "R3", "R4")


def registrar_referencia_trace(conexao: Connection, conversa_id: uuid.UUID, trace_id: str) -> None:
    """Grava o trace raiz da conversa uma única vez. Turnos seguintes reaproveitam a referência."""
    conexao.execute(
        "INSERT INTO registro.referencias_trace (conversa_id, trace_id) VALUES (%s, %s) "
        "ON CONFLICT (conversa_id) DO NOTHING",
        (conversa_id, trace_id),
    )


def obter_referencia_trace(conexao: Connection, conversa_id: uuid.UUID) -> str | None:
    linha = conexao.execute(
        "SELECT trace_id FROM registro.referencias_trace WHERE conversa_id = %s",
        (conversa_id,),
    ).fetchone()
    return linha[0] if linha else None


def registrar_resultado_avaliacao(
    conexao: Connection,
    rodada: str,
    caso: str,
    regra: str,
    aprovado: bool,
    motivo: str | None = None,
    agora: datetime | None = None,
) -> uuid.UUID:
    if regra not in REGRAS_VALIDAS:
        raise ValueError(f"regra inválida: {regra!r}")
    resultado_id = uuid.uuid4()
    conexao.execute(
        "INSERT INTO registro.resultados_avaliacao "
        "(id, rodada, caso, regra, aprovado, motivo, criado_em) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (resultado_id, rodada, caso, regra, aprovado, motivo, agora or datetime.now(timezone.utc)),
    )
    return resultado_id
