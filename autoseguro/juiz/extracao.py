"""Reconhecimento de valores monetários no texto (FDD-0009, seção 6).

Reconhece valores com R$ e números com separador decimal. Inteiros sem R$ (prazos, idades, anos) são ignorados.
Formato brasileiro: ponto é milhar e vírgula é decimal. Número com ponto decimal e sem vírgula usa o ponto como decimal.
"""

from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

# R$ 119,90 | R$ 4.500,00 | R$ 4500 | R$ 119.90
_VALOR_RS = re.compile(r"R\$\s?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?|\d+\.\d{1,2})")
# 119,90 | 4.500,00 | 119.90, sem R$
_VALOR_DECIMAL = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+,\d{1,2}|\d+,\d{1,2}|\d+\.\d{1,2})(?![\w,]|\.\d)"
)


def _converter(bruto: str, com_rs: bool) -> Decimal:
    if "," in bruto:
        numero = bruto.replace(".", "").replace(",", ".")
    elif com_rs and re.fullmatch(r"\d{1,3}(\.\d{3})+", bruto):
        numero = bruto.replace(".", "")  # R$ 4.500 é milhar, não decimal
    else:
        numero = bruto
    return Decimal(numero).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def extrair_valores(texto: str) -> list[tuple[Decimal, int]]:
    """Devolve (valor, posição) de cada valor reconhecido, em ordem de posição no texto."""
    encontrados: list[tuple[Decimal, int]] = []
    ocupados: list[tuple[int, int]] = []
    for casamento in _VALOR_RS.finditer(texto):
        encontrados.append((_converter(casamento.group(1), com_rs=True), casamento.start()))
        ocupados.append(casamento.span())
    for casamento in _VALOR_DECIMAL.finditer(texto):
        inicio, fim = casamento.span()
        if any(inicio < o_fim and fim > o_inicio for o_inicio, o_fim in ocupados):
            continue
        encontrados.append((_converter(casamento.group(1), com_rs=False), inicio))
    return sorted(encontrados, key=lambda par: par[1])
