"""Encaminhamentos para humano. Uma conversa tem no máximo um (FDD-0004 seções 5 e 7).

O CPF é guardado sem máscara, conforme a RF-10 do PRD. Nenhuma outra tabela recebe CPF.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from psycopg import Connection
from psycopg.rows import dict_row


def registrar_encaminhamento(
    conexao: Connection,
    conversa_id: uuid.UUID,
    motivo: str,
    resumo: str,
    cpf: str | None = None,
    agora: datetime | None = None,
) -> uuid.UUID:
    encaminhamento_id = uuid.uuid4()
    conexao.execute(
        "INSERT INTO registro.encaminhamentos (id, conversa_id, motivo, resumo, cpf, criado_em) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (encaminhamento_id, conversa_id, motivo, resumo, cpf, agora or datetime.now(timezone.utc)),
    )
    return encaminhamento_id


def obter_encaminhamento(conexao: Connection, conversa_id: uuid.UUID) -> dict | None:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM registro.encaminhamentos WHERE conversa_id = %s",
            (conversa_id,),
        )
        return cur.fetchone()
