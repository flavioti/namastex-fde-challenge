"""Feedback do juiz no trace do turno (FDD-0006, seção 8; FDD-0009, seção 11).

A pontuação vai como 1 ou 0. O comentário é o código da regra e uma frase curta, sem valor nem dado pessoal.
"""

from __future__ import annotations

import uuid
from typing import Any

from autoseguro.juiz.modelos import DecisaoJuiz
from autoseguro.logs import obter_logger

_log = obter_logger("autoseguro.observabilidade")
REGRAS = ("R1", "R2", "R3", "R4")


def feedbacks_do_juiz(decisao: DecisaoJuiz) -> list[dict[str, Any]]:
    """Lista de feedbacks: uma chave por regra e a decisão final."""
    itens: list[dict[str, Any]] = []
    for regra in REGRAS:
        violada = decisao.regra == regra
        itens.append({
            "key": f"juiz_regra_{regra[1]}",  # R1 vira juiz_regra_1
            "score": 0 if violada else 1,
            "comment": f"{regra} reprovada" if violada else "ok",
        })
    itens.append({"key": "juiz_decisao", "score": 1 if decisao.aprovado else 0,
                  "comment": decisao.regra or "aprovado"})
    return itens


def registrar_feedbacks(cliente, run_id: uuid.UUID, decisao: DecisaoJuiz) -> int:
    """Envia os feedbacks ao trace. Falha de envio não altera a decisão (FDD-0006, seção 8)."""
    enviados = 0
    for item in feedbacks_do_juiz(decisao):
        try:
            cliente.create_feedback(run_id, item["key"], score=item["score"], comment=item["comment"])
            enviados += 1
        except Exception:
            _log.warning("falha ao enviar feedback do juiz", extra={"evento": "feedback_falhou",
                                                                   "detalhe": {"chave": item["key"]}})
    return enviados
