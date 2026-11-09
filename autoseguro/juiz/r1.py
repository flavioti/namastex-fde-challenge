"""Verificação R1 em código: todo valor do rascunho existe na cotação, no plano correto (FDD-0009, seção 7)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from autoseguro.juiz.extracao import extrair_valores


@dataclass(frozen=True)
class ResultadoR1:
    aprovado: bool
    motivo: str = ""


def _valores_do_plano(plano: dict) -> set[Decimal]:
    valores = {Decimal(str(plano["premio_mensal"])), Decimal(str(plano["franquia"]))}
    if plano.get("primeiro_pagamento_pro_rata") is not None:
        valores.add(Decimal(str(plano["primeiro_pagamento_pro_rata"])))
    return {v.quantize(Decimal("0.01")) for v in valores}


def _frases(texto: str) -> list[str]:
    return [f for f in re.split(r"(?<=[.;!?])\s+|\n+", texto) if f.strip()]


def verificar(rascunho: str, planos: list[dict] | None) -> ResultadoR1:
    """Aprova se todo valor do rascunho está permitido. Sem cotação, nenhum valor é permitido (OBJ-3)."""
    if not extrair_valores(rascunho):
        return ResultadoR1(True)
    if not planos:
        return ResultadoR1(False, "valor citado sem cotação")

    por_plano = {p["plano_nome"].lower(): _valores_do_plano(p) for p in planos}
    geral: set[Decimal] = set().union(*por_plano.values())

    for frase in _frases(rascunho):
        valores = extrair_valores(frase)
        if not valores:
            continue
        citados = [nome for nome in por_plano if nome in frase.lower()]
        permitidos = por_plano[citados[0]] if len(citados) == 1 else geral
        for valor, _ in valores:
            if valor.quantize(Decimal("0.01")) not in permitidos:
                return ResultadoR1(False, "valor fora da cotação oficial")
    return ResultadoR1(True)
