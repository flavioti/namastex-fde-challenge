"""Logs em JSON, com o módulo logging padrão (ADR-0011).

Nenhum registro deve conter dado pessoal. Quem chama passa contagens e identificadores, nunca valores.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

CAMPOS_EXTRAS = ("evento", "conversa_id", "ponto", "contagem", "detalhe")


class FormatoJson(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        corpo = {
            "nivel": registro.levelname,
            "horario": datetime.fromtimestamp(registro.created, tz=timezone.utc).isoformat(),
            "logger": registro.name,
            "mensagem": registro.getMessage(),
        }
        for campo in CAMPOS_EXTRAS:
            if hasattr(registro, campo):
                corpo[campo] = getattr(registro, campo)
        return json.dumps(corpo, ensure_ascii=False, default=str)


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Configura o logger raiz para saída JSON na saída padrão. Chamada uma vez por processo."""
    raiz = logging.getLogger()
    if any(isinstance(h.formatter, FormatoJson) for h in raiz.handlers):
        return
    manipulador = logging.StreamHandler(sys.stdout)
    manipulador.setFormatter(FormatoJson())
    raiz.addHandler(manipulador)
    raiz.setLevel(nivel)


def obter_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)
