"""Montagem do StateGraph e do checkpoint no esquema agente (FDD-0005, seção 5; FDD-0004, seção 4)."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from autoseguro.agente.estado import EstadoConversa
from autoseguro.agente.nos import Dependencias, criar_nos


def criar_pool_agente(url: str) -> ConnectionPool:
    """Pool do checkpoint. O search_path aponta para o esquema agente (FDD-0004, seção 4)."""
    return ConnectionPool(
        conninfo=make_conninfo(url, options="-c search_path=agente"),
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )


def _proxima(estado: Any) -> str:
    valor = estado.proxima if hasattr(estado, "proxima") else estado.get("proxima")
    return valor or "fim"


def construir(deps: Dependencias, checkpointer: PostgresSaver):
    nos = criar_nos(deps)
    grafo = StateGraph(EstadoConversa)
    for nome, funcao in nos.items():
        grafo.add_node(nome, funcao)

    grafo.add_edge(START, "entrada")
    grafo.add_conditional_edges(
        "entrada", _proxima,
        {"coleta": "coleta", "encaminhamento": "encaminhamento", "fim": END},
    )
    grafo.add_conditional_edges(
        "coleta", _proxima,
        {"cotacao": "cotacao", "juiz": "juiz", "resposta": "resposta",
         "encaminhamento": "encaminhamento", "encerramento": "encerramento", "fim": END},
    )
    grafo.add_conditional_edges("cotacao", _proxima, {"coleta": "coleta", "encaminhamento": "encaminhamento"})
    grafo.add_conditional_edges(
        "juiz", _proxima,
        {"resposta": "resposta", "coleta": "coleta", "encaminhamento": "encaminhamento"},
    )
    for terminal in ("resposta", "encaminhamento", "encerramento"):
        grafo.add_edge(terminal, END)
    return grafo.compile(checkpointer=checkpointer)
