"""Consultas de exibição: lista de conversas, chat, painel e aba de encaminhados (FDD-0007, seções 4, 5 e 9).

Os horários são convertidos de UTC para Brasília (ADR-0012). CPF aparece só na aba de encaminhados.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from autoseguro.banco.repositorios import conversas, cotacoes, mensagens

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
STATUS_BLOQUEADOS = ("encaminhada", "encerrada")


def formatar_horario(momento: Optional[datetime]) -> str:
    if momento is None:
        return ""
    return momento.astimezone(FUSO_BRASILIA).strftime("%d/%m/%Y %H:%M")


def listar_conversas(pool: ConnectionPool) -> list[dict[str, Any]]:
    """Mais recentes primeiro, pela última atualização (FDD-0007, seção 4)."""
    with pool.connection() as conexao:
        linhas = conversas.listar_conversas(conexao)
    return [
        {"id": linha["id"], "nome": linha["nome_lead"], "status": linha["status"],
         "atualizada_em": formatar_horario(linha["atualizada_em"]),
         "rotulo": f"{linha['nome_lead']} · {linha['status']} · {formatar_horario(linha['atualizada_em'])}"}
        for linha in linhas
    ]


def mensagens_da_conversa(pool: ConnectionPool, conversa_id: uuid.UUID) -> list[dict[str, str]]:
    """Texto como ficou guardado, mascarado (FDD-0007, seção 5)."""
    with pool.connection() as conexao:
        linhas = mensagens.listar_mensagens(conexao, conversa_id)
    return [{"papel": linha["papel"], "texto": linha["conteudo_mascarado"],
             "horario": formatar_horario(linha["criada_em"])} for linha in linhas]


def painel(pool: ConnectionPool, conversa_id: uuid.UUID, estado: Optional[dict] = None) -> dict[str, Any]:
    """Status, dados coletados (CEP mascarado), cotação mais recente e motivo do encaminhamento."""
    with pool.connection() as conexao:
        conversa = conversas.obter_conversa(conexao, conversa_id)
        historico = cotacoes.listar_cotacoes(conexao, conversa_id)
        with conexao.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT motivo FROM registro.encaminhamentos WHERE conversa_id = %s", (conversa_id,))
            encaminhamento = cur.fetchone()
    ultima = historico[-1] if historico else None
    return {
        "status": conversa["status"] if conversa else None,
        "dados": (estado or {}).get("dados", {}),
        "cotacao": {
            "resultado": ultima["resultado"],
            "planos": [{"nome": p["plano_nome"], "premio": p["premio_mensal"]} for p in (ultima["planos"] or [])]
            if ultima and ultima["planos"] else [],
        } if ultima else None,
        "motivo_encaminhamento": encaminhamento["motivo"] if encaminhamento else None,
    }


def encaminhados(pool: ConnectionPool) -> list[dict[str, Any]]:
    """Conversas encaminhadas, com CPF sem máscara, mais recentes primeiro (FDD-0007, seção 9)."""
    with pool.connection() as conexao, conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT c.nome_lead, e.motivo, e.resumo, e.cpf, e.criado_em "
            "FROM registro.encaminhamentos e JOIN registro.conversas c ON c.id = e.conversa_id "
            "ORDER BY e.criado_em DESC"
        )
        linhas = cur.fetchall()
    return [
        {"lead": linha["nome_lead"], "motivo": linha["motivo"], "resumo": linha["resumo"],
         "cpf": linha["cpf"] or "", "encaminhado_em": formatar_horario(linha["criado_em"])}
        for linha in linhas
    ]
