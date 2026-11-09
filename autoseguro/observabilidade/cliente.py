"""Cliente do LangSmith com redação aplicada a entradas e saídas (FDD-0006, seções 2 e 6)."""

from __future__ import annotations

import os
from typing import Any

from langsmith import Client

from autoseguro.observabilidade.redacao import RedacaoFalhou, redigir

# Quando a redação falha, o run segue sem nenhum conteúdo. Assim nada sensível sai da aplicação.
# Ver docs/tasks.md (T-23): o FDD prevê descarte do run, e o SDK expõe apenas a ocultação do conteúdo.
PAYLOAD_VAZIO: dict[str, Any] = {}


def _ocultar(payload: dict) -> dict:
    try:
        return redigir(payload)
    except RedacaoFalhou:
        return PAYLOAD_VAZIO


def criar_cliente(api_key: str | None = None) -> Client:
    """Cliente do projeto. Entradas, saídas e metadados passam pela redação antes do envio."""
    return Client(
        api_key=api_key or os.environ.get("LANGSMITH_API_KEY"),
        hide_inputs=_ocultar,
        hide_outputs=_ocultar,
        hide_metadata=False,
    )
