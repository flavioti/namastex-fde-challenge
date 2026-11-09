"""Leitura e validação de plans.json (FDD-0008, seção 4). Um arquivo inválido interrompe a carga antes de gravar."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from autoseguro.catalogo.config import ARQUIVO_PLANS


class FonteInvalida(ValueError):
    """plans.json ausente, malformado ou fora do formato esperado."""


@dataclass(frozen=True)
class PlanoFonte:
    id: str
    nome: str
    base_mensal: Decimal
    franquia: Decimal
    coberturas: list[str]


@dataclass(frozen=True)
class Catalogo:
    planos: list[PlanoFonte]
    faixas_etarias: list[dict] = field(default_factory=list)
    faixas_veiculo: list[dict] = field(default_factory=list)
    regiao_cep: dict = field(default_factory=dict)
    carencia: dict = field(default_factory=dict)
    entrada_meio_mes: dict = field(default_factory=dict)


def _exigir(objeto: dict, campos: tuple[str, ...], onde: str) -> None:
    faltando = [campo for campo in campos if campo not in objeto]
    if faltando:
        raise FonteInvalida(f"{onde}: campos obrigatórios ausentes: {', '.join(faltando)}")


def _decimal(valor: object, onde: str) -> Decimal:
    if isinstance(valor, bool) or not isinstance(valor, (int, float, str)):
        raise FonteInvalida(f"{onde}: valor monetário inválido")
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except ArithmeticError as erro:
        raise FonteInvalida(f"{onde}: valor monetário inválido") from erro


def validar(dados: dict) -> Catalogo:
    if not isinstance(dados, dict):
        raise FonteInvalida("plans.json deve conter um objeto")
    _exigir(dados, ("planos", "regras"), "raiz")
    regras = dados["regras"]
    _exigir(regras, ("faixa_etaria", "idade_veiculo", "regiao_cep", "carencia", "entrada_meio_mes"), "regras")

    planos = []
    for indice, plano in enumerate(dados["planos"]):
        onde = f"planos[{indice}]"
        _exigir(plano, ("id", "nome", "base_mensal", "franquia", "coberturas"), onde)
        planos.append(PlanoFonte(
            id=str(plano["id"]),
            nome=str(plano["nome"]),
            base_mensal=_decimal(plano["base_mensal"], onde),
            franquia=_decimal(plano["franquia"], onde),
            coberturas=[str(c) for c in plano["coberturas"]],
        ))
    if len(planos) != 3:
        raise FonteInvalida(f"esperados 3 planos, encontrados {len(planos)}")

    for indice, faixa in enumerate(regras["faixa_etaria"]):
        _exigir(faixa, ("idade_min", "idade_max"), f"faixa_etaria[{indice}]")
    for indice, faixa in enumerate(regras["idade_veiculo"]):
        _exigir(faixa, ("anos_min", "anos_max"), f"idade_veiculo[{indice}]")
    _exigir(regras["regiao_cep"], ("prefixos_alto_risco", "multiplicador"), "regiao_cep")
    _exigir(regras["carencia"], ("coberturas_com_carencia", "dias"), "carencia")

    return Catalogo(
        planos=planos,
        faixas_etarias=list(regras["faixa_etaria"]),
        faixas_veiculo=list(regras["idade_veiculo"]),
        regiao_cep=dict(regras["regiao_cep"]),
        carencia=dict(regras["carencia"]),
        entrada_meio_mes=dict(regras["entrada_meio_mes"]),
    )


def carregar(caminho: Path = ARQUIVO_PLANS) -> Catalogo:
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as erro:
        raise FonteInvalida(f"não foi possível ler {caminho}") from erro
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise FonteInvalida(f"{caminho} não é JSON válido") from erro
    return validar(dados)
