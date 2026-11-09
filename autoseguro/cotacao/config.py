"""Constantes do cliente da cotação (FDD-0002, seção 4). Ficam em código, não no .env."""

from __future__ import annotations

import os

PLANOS = ("essencial", "completo", "premium")

TIMEOUT_TENTATIVA_SEGUNDOS = 5.0
PRAZO_TOTAL_SEGUNDOS = 15.0
TENTATIVAS = 3
ESPERAS_SEGUNDOS = (0.5, 1.0)

URL_BASE_PADRAO = "http://localhost:8000"


def url_base() -> str:
    """URL do serviço de cotação, vinda de COTACAO_BASE_URL, com padrão local."""
    return os.environ.get("COTACAO_BASE_URL", URL_BASE_PADRAO)
