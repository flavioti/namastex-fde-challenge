"""Modelos de entrada e de resultado da cotação (FDD-0002, seção 5; ADR-0010; ADR-0015)."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


def para_decimal(valor: object) -> Decimal:
    """Converte número vindo da API em Decimal com duas casas, por Decimal(str(...))."""
    return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class DadosCotacao(BaseModel):
    """Dados já validados pela conversa. O plano é definido pelo cliente, uma chamada por plano."""

    idade: int
    veiculo_ano: int
    cep: Optional[str] = None
    data_inicio: date


class PlanoCotado(BaseModel):
    plano_id: str
    plano_nome: str
    premio_mensal: Decimal
    franquia: Decimal
    coberturas: list[str]
    carencia_dias: int
    primeiro_pagamento_pro_rata: Optional[Decimal] = None


class CotacaoSucesso(BaseModel):
    tipo: Literal["sucesso"] = "sucesso"
    planos: list[PlanoCotado]


class CotacaoRecusada(BaseModel):
    tipo: Literal["recusada"] = "recusada"
    motivo: str


class CotacaoIndisponivel(BaseModel):
    tipo: Literal["indisponivel"] = "indisponivel"
    motivo: str = Field(..., max_length=200)


class CotacaoPayloadInvalido(BaseModel):
    tipo: Literal["payload_invalido"] = "payload_invalido"
    detalhe: str


ResultadoCotacao = Annotated[
    Union[CotacaoSucesso, CotacaoRecusada, CotacaoIndisponivel, CotacaoPayloadInvalido],
    Field(discriminator="tipo"),
]
