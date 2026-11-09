"""Regras extraídas do catálogo, com chave estável e impressão digital (FDD-0008, seções 5 e 7).

Cada regra tem:
- chave textual, formada pelo tipo e pelos limites, como faixa_etaria:18-24;
- identificador UUID v5 derivado da chave, estável entre cargas;
- impressão digital do conteúdo, SHA-256 da representação canônica dos dados.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass

from autoseguro.catalogo.config import NAMESPACE_REGRAS
from autoseguro.catalogo.fonte import Catalogo


@dataclass(frozen=True)
class Regra:
    chave: str
    tipo: str
    dados: dict
    id: uuid.UUID
    impressao_digital: str


def impressao_digital(conteudo: object) -> str:
    canonico = json.dumps(conteudo, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _regra(chave: str, tipo: str, dados: dict) -> Regra:
    return Regra(
        chave=chave,
        tipo=tipo,
        dados=dados,
        id=uuid.uuid5(NAMESPACE_REGRAS, chave),
        impressao_digital=impressao_digital(dados),
    )


def extrair(catalogo: Catalogo) -> list[Regra]:
    """Uma regra por faixa etária, por faixa de veículo, por região, por carência e pelo pro-rata."""
    regras: list[Regra] = []
    for faixa in catalogo.faixas_etarias:
        chave = f"faixa_etaria:{faixa['idade_min']}-{faixa['idade_max']}"
        regras.append(_regra(chave, "faixa_etaria", dict(faixa)))
    for faixa in catalogo.faixas_veiculo:
        chave = f"idade_veiculo:{faixa['anos_min']}-{faixa['anos_max']}"
        regras.append(_regra(chave, "idade_veiculo", dict(faixa)))
    regras.append(_regra("regiao_cep", "regiao_cep", dict(catalogo.regiao_cep)))
    regras.append(_regra("carencia", "carencia", dict(catalogo.carencia)))
    regras.append(_regra("pro_rata", "pro_rata", dict(catalogo.entrada_meio_mes)))
    return regras
