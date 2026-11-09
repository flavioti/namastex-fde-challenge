"""Fluxo de um turno na interface: trava, chamada ao respondedor ou agente, e mensagem neutra em erro (FDD-0007, seção 6)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from autoseguro.banco.repositorios import conversas
from autoseguro.interface.trava import TravaOcupada, turno_travado

_log = logging.getLogger("autoseguro.interface")
MENSAGEM_NEUTRA = "não foi possível responder agora"
STATUS_BLOQUEADOS = ("encaminhada", "encerrada")


@dataclass(frozen=True)
class ResultadoTurno:
    texto_agente: Optional[str]
    ocupada: bool = False
    erro: bool = False
    bloqueada: bool = False


def processar_turno(pool: Any, responder: Any, conversa_id: uuid.UUID, texto: str,
                    agora: Optional[datetime] = None) -> ResultadoTurno:
    with pool.connection() as conexao:
        conversa = conversas.obter_conversa(conexao, conversa_id)
    if conversa is None or conversa["status"] in STATUS_BLOQUEADOS:
        return ResultadoTurno(texto_agente=None, bloqueada=True)

    try:
        with turno_travado(pool, conversa_id, agora=agora):
            resposta = responder.turno(conversa_id, texto)
    except TravaOcupada:
        return ResultadoTurno(texto_agente=None, ocupada=True)
    except Exception as erro:
        # Log sem texto digitado nem resposta (FDD-0007, seção 11).
        _log.error("turno falhou", extra={"evento": "turno_falhou", "conversa_id": str(conversa_id),
                                          "detalhe": {"tipo": type(erro).__name__,
                                                      "horario": datetime.now(timezone.utc).isoformat()}})
        return ResultadoTurno(texto_agente=MENSAGEM_NEUTRA, erro=True)

    texto_agente = resposta if isinstance(resposta, str) else getattr(resposta, "texto", None)
    return ResultadoTurno(texto_agente=texto_agente)
