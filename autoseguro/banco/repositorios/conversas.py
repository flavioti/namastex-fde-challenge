"""Conversas e trava de turno (FDD-0004 seção 5; FDD-0007 seção 7)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from psycopg import Connection
from psycopg.rows import dict_row

# Uma conversa só pode estar em um dos status da FDD-0004.
STATUS_VALIDOS = ("em_andamento", "cotada", "encaminhada", "encerrada")

# Trava expirada após 15 minutos, para cobrir queda da aplicação no meio de um turno (FDD-0007).
TRAVA_EXPIRA_APOS = timedelta(minutes=15)


def _agora(agora: datetime | None) -> datetime:
    return agora or datetime.now(timezone.utc)


def criar_conversa(
    conexao: Connection,
    nome_lead: str,
    telefone_lead: str,
    agora: datetime | None = None,
) -> uuid.UUID:
    """Cria uma conversa em andamento e devolve o identificador."""
    conversa_id = uuid.uuid4()
    momento = _agora(agora)
    conexao.execute(
        "INSERT INTO registro.conversas "
        "(id, nome_lead, telefone_lead, status, criada_em, atualizada_em) "
        "VALUES (%s, %s, %s, 'em_andamento', %s, %s)",
        (conversa_id, nome_lead, telefone_lead, momento, momento),
    )
    return conversa_id


def obter_conversa(conexao: Connection, conversa_id: uuid.UUID) -> dict | None:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM registro.conversas WHERE id = %s", (conversa_id,))
        return cur.fetchone()


def listar_conversas(conexao: Connection) -> list[dict]:
    """Conversas mais recentes primeiro (FDD-0007, seção 5)."""
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM registro.conversas ORDER BY atualizada_em DESC")
        return cur.fetchall()


def atualizar_status(
    conexao: Connection,
    conversa_id: uuid.UUID,
    status: str,
    agora: datetime | None = None,
) -> None:
    if status not in STATUS_VALIDOS:
        raise ValueError(f"status inválido: {status!r}")
    conexao.execute(
        "UPDATE registro.conversas SET status = %s, atualizada_em = %s WHERE id = %s",
        (status, _agora(agora), conversa_id),
    )


def adquirir_trava(
    conexao: Connection,
    conversa_id: uuid.UUID,
    agora: datetime | None = None,
) -> bool:
    """Tenta marcar um turno em andamento. Vence se a coluna está nula ou expirada.

    Devolve True se a trava foi adquirida. Nenhuma linha alterada significa trava ocupada.
    """
    momento = _agora(agora)
    cursor = conexao.execute(
        "UPDATE registro.conversas SET turno_em_andamento_desde = %s "
        "WHERE id = %s AND (turno_em_andamento_desde IS NULL OR turno_em_andamento_desde < %s)",
        (momento, conversa_id, momento - TRAVA_EXPIRA_APOS),
    )
    return cursor.rowcount == 1


def liberar_trava(conexao: Connection, conversa_id: uuid.UUID) -> None:
    conexao.execute(
        "UPDATE registro.conversas SET turno_em_andamento_desde = NULL WHERE id = %s",
        (conversa_id,),
    )
