"""Planos e regras do catálogo (FDD-0004 seção 6; FDD-0008 seção 8)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

TIPOS_VALIDOS = ("faixa_etaria", "idade_veiculo", "regiao_cep", "carencia", "pro_rata")


def upsert_plano(
    conexao: Connection,
    plano_id: str,
    nome: str,
    base_mensal: Decimal,
    franquia: Decimal,
    coberturas: list[str],
) -> None:
    conexao.execute(
        "INSERT INTO regras.planos (id, nome, base_mensal, franquia, coberturas) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, base_mensal = EXCLUDED.base_mensal, "
        "franquia = EXCLUDED.franquia, coberturas = EXCLUDED.coberturas",
        (plano_id, nome, base_mensal, franquia, coberturas),
    )


def listar_planos(conexao: Connection) -> list[dict]:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM regras.planos ORDER BY id")
        return cur.fetchall()


def upsert_regra(
    conexao: Connection,
    regra_id: uuid.UUID,
    tipo: str,
    dados: dict,
    impressao_digital: str,
    ativa: bool = True,
) -> None:
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo de regra inválido: {tipo!r}")
    conexao.execute(
        "INSERT INTO regras.regras (id, tipo, dados, impressao_digital, ativa) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET tipo = EXCLUDED.tipo, dados = EXCLUDED.dados, "
        "impressao_digital = EXCLUDED.impressao_digital, ativa = EXCLUDED.ativa",
        (regra_id, tipo, Jsonb(dados), impressao_digital, ativa),
    )


def obter_regra(conexao: Connection, regra_id: uuid.UUID) -> dict | None:
    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM regras.regras WHERE id = %s", (regra_id,))
        return cur.fetchone()


def desativar_regras_ausentes(conexao: Connection, ids_presentes: list[uuid.UUID]) -> int:
    """Marca como inativas as regras que não estão mais no catálogo. Não apaga nada."""
    cursor = conexao.execute(
        "UPDATE regras.regras SET ativa = false WHERE ativa AND NOT (id = ANY(%s))",
        (ids_presentes,),
    )
    return cursor.rowcount
