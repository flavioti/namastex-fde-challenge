"""Mensagens da conversa. Guardam apenas o texto mascarado (FDD-0004 seção 5; FDD-0003)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from psycopg import Connection
from psycopg.rows import dict_row

PAPEIS_VALIDOS = ("lead", "agente")


STATUS_VALIDOS = ("recebida", "enviada", "descartada")


def registrar_mensagem(
    conexao: Connection,
    conversa_id: uuid.UUID,
    papel: str,
    conteudo_mascarado: str,
    agora: datetime | None = None,
    status: str | None = None,
) -> int:
    """Grava a mensagem na próxima posição da conversa e devolve a ordem usada.

    Sem status explícito, mensagens do lead ficam 'recebida' e do agente ficam 'enviada'.
    """
    if papel not in PAPEIS_VALIDOS:
        raise ValueError(f"papel inválido: {papel!r}")
    status = status or ("recebida" if papel == "lead" else "enviada")
    if status not in STATUS_VALIDOS:
        raise ValueError(f"status inválido: {status!r}")
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "INSERT INTO registro.mensagens (id, conversa_id, ordem, papel, conteudo_mascarado, criada_em, status) "
            "SELECT %s, %s, COALESCE(MAX(ordem), 0) + 1, %s, %s, %s, %s "
            "FROM registro.mensagens WHERE conversa_id = %s "
            "RETURNING ordem",
            (
                uuid.uuid4(),
                conversa_id,
                papel,
                conteudo_mascarado,
                agora or datetime.now(timezone.utc),
                status,
                conversa_id,
            ),
        )
        return cur.fetchone()["ordem"]


def listar_mensagens(conexao: Connection, conversa_id: uuid.UUID) -> list[dict]:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT ordem, papel, conteudo_mascarado, criada_em, status FROM registro.mensagens "
            "WHERE conversa_id = %s ORDER BY ordem",
            (conversa_id,),
        )
        return cur.fetchall()
