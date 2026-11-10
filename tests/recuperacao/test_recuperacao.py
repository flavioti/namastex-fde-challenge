"""Casos de recuperação da busca híbrida com o modelo real (ADR-0004; RFC-0003, seção 7).

Cada caso diz a consulta, o tipo de regra esperado e até qual posição ele deve aparecer.
"""

from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pytest
from pgvector.psycopg import register_vector

from autoseguro.banco import busca

CASOS = json.loads((Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("caso", CASOS, ids=[c["consulta"] for c in CASOS])
def test_caso_de_recuperacao(catalogo_com_modelo, caso):
    url, embedder = catalogo_com_modelo
    vetor = embedder.gerar(["query: " + caso["consulta"]])[0]
    with psycopg.connect(url) as conexao:
        register_vector(conexao)
        resultado = busca.buscar_trechos(conexao, caso["consulta"], vetor, k=caso["posicao"])
    tipos = [item["tipo"] for item in resultado]
    assert caso["tipo"] in tipos, f"esperado {caso['tipo']} em até {caso['posicao']}, veio {tipos}"
