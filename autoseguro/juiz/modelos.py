"""Modelos do juiz (FDD-0009, seções 4, 8 e 11)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VeredictoJuiz(BaseModel):
    """Saída estruturada do modelo do juiz para R2, R3 e R4."""

    aprovado: bool
    regra: Optional[Literal["R2", "R3", "R4"]] = None
    motivo: str = Field("", max_length=200)


class DecisaoJuiz(BaseModel):
    """Decisão devolvida ao agente. `regra` é R1 quando a verificação em código reprovou."""

    aprovado: bool
    regra: Optional[Literal["R1", "R2", "R3", "R4"]] = None
    motivo: str = ""
    tentativas: int = 0
    tokens: int = 0  # consumo do modelo do juiz nesta decisão, somado ao teto do agente (ADR-0013)
