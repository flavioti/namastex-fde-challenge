"""Geração de leads fictícios a partir de leads.toml (FDD-0007, seção 8; RFC-0001)."""

from __future__ import annotations

import random
import tomllib
from dataclasses import dataclass
from pathlib import Path

from autoseguro.catalogo.config import RAIZ_PROJETO

CAMINHO_PADRAO = RAIZ_PROJETO / "ui-app" / "leads.toml"


@dataclass(frozen=True)
class Lead:
    nome: str
    telefone: str


@dataclass(frozen=True)
class ListasLeads:
    primeiros: tuple[str, ...]
    sobrenomes: tuple[str, ...]
    ddds: tuple[int, ...]


def carregar_listas(caminho: Path = CAMINHO_PADRAO) -> ListasLeads:
    with caminho.open("rb") as arquivo:
        dados = tomllib.load(arquivo)
    listas = ListasLeads(
        primeiros=tuple(dados["nomes"]["primeiros"]),
        sobrenomes=tuple(dados["nomes"]["sobrenomes"]),
        ddds=tuple(int(d) for d in dados["telefone"]["ddds"]),
    )
    if not (listas.primeiros and listas.sobrenomes and listas.ddds):
        raise ValueError("leads.toml precisa ter nomes e DDDs")
    return listas


def gerar_lead(listas: ListasLeads, rng: random.Random | None = None) -> Lead:
    """Nome das listas e telefone com DDD da lista e número aleatório, no formato (DDD) 9xxxx-xxxx."""
    rng = rng or random.Random()
    nome = f"{rng.choice(listas.primeiros)} {rng.choice(listas.sobrenomes)}"
    ddd = rng.choice(listas.ddds)
    numero = "9" + "".join(rng.choices("0123456789", k=8))
    return Lead(nome=nome, telefone=f"({ddd:02d}) {numero[:5]}-{numero[5:]}")
