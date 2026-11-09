"""Trechos vetorizados das regras (FDD-0004 seção 6; FDD-0008 seções 7 e 8).

Cada regra tem exatamente um trecho. O identificador do trecho é derivado do identificador da regra,
para que a carga possa fazer upsert sem consultar outro campo.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from psycopg import Connection

ESPACO_TRECHO = uuid.UUID("6f1b2c1e-8d3a-5b7e-9f40-2a6c1d8e7b11")
DIMENSAO_ESPERADA = 384


def id_do_trecho(regra_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(ESPACO_TRECHO, str(regra_id))


def obter_impressao_trecho(conexao: Connection, regra_id: uuid.UUID) -> str | None:
    linha = conexao.execute(
        "SELECT impressao_digital FROM regras.trechos WHERE id = %s",
        (id_do_trecho(regra_id),),
    ).fetchone()
    return linha[0] if linha else None


def upsert_trecho(
    conexao: Connection,
    regra_id: uuid.UUID,
    texto: str,
    embedding: list[float],
    modelo_id: str,
    impressao_digital: str,
    agora: datetime | None = None,
) -> None:
    if len(embedding) != DIMENSAO_ESPERADA:
        raise ValueError(f"dimensão {len(embedding)} diferente de {DIMENSAO_ESPERADA}")
    vetor = "[" + ",".join(repr(float(x)) for x in embedding) + "]"
    conexao.execute(
        "INSERT INTO regras.trechos "
        "(id, regra_id, texto, embedding, modelo_id, dimensao, impressao_digital, gerado_em) "
        "VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET texto = EXCLUDED.texto, embedding = EXCLUDED.embedding, "
        "modelo_id = EXCLUDED.modelo_id, dimensao = EXCLUDED.dimensao, "
        "impressao_digital = EXCLUDED.impressao_digital, gerado_em = EXCLUDED.gerado_em",
        (
            id_do_trecho(regra_id),
            regra_id,
            texto,
            vetor,
            modelo_id,
            DIMENSAO_ESPERADA,
            impressao_digital,
            agora or datetime.now(timezone.utc),
        ),
    )
