"""Padrões de detecção de dados pessoais, em ordem fixa de aplicação (FDD-0003 seção 4; ADR-0020).

A ordem importa: quando um mesmo trecho casa com dois padrões, o primeiro da lista vence.
Os padrões não validam dígito verificador de CPF (RFC-0008).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True)
class Padrao:
    tipo: str
    marcador: str
    regex: Pattern[str]


_FLAGS = re.IGNORECASE

PADROES: tuple[Padrao, ...] = (
    Padrao("cpf", "[CPF]", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", _FLAGS)),
    Padrao("email", "[EMAIL]", re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", _FLAGS)),
    Padrao("cep", "[CEP]", re.compile(r"\b\d{5}-?\d{3}\b", _FLAGS)),
    Padrao(
        "telefone",
        "[TELEFONE]",
        re.compile(r"(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}\b", _FLAGS),
    ),
    Padrao(
        "placa",
        "[PLACA]",
        re.compile(r"\b[a-z]{3}-?\d{4}\b|\b[a-z]{3}\d[a-z]\d{2}\b", _FLAGS),
    ),
)

# Marcador de saída, usado quando o texto vai para o lead ou para o modelo na resposta (FDD-0003 seção 5).
MARCADOR_SAIDA = "[dado omitido]"
