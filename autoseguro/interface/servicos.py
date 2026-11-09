"""Montagem dos serviços da interface: banco, respondedor ou agente (FDD-0007, seção 6).

A escolha é feita pela variável RESPONDEDOR: "teste" (padrão) ou "agente".
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from autoseguro.agente import Agente, Dependencias, criar_pool_agente
from autoseguro.agente.llm import MODELO_AGENTE, MODELO_JUIZ, ModeloAnthropic
from autoseguro.banco.conexao import abrir_pool
from autoseguro.cotacao import CotacaoClient
from autoseguro.cotacao.config import url_base
from autoseguro.interface.respondedor import RespondedorTeste
from autoseguro.juiz import Juiz

_log = logging.getLogger("autoseguro.interface")


@dataclass
class Servicos:
    pool: Any
    responder: Any  # RespondedorTeste ou Agente, com o método turno(conversa_id, texto)
    modo: str


def montar_agente(url: str, pool) -> Agente:
    deps = Dependencias(
        modelo_agente=ModeloAnthropic(MODELO_AGENTE),
        juiz=Juiz(ModeloAnthropic(MODELO_JUIZ)),
        cotacao=CotacaoClient(url_base()),
        pool=pool,
    )
    return Agente(deps, criar_pool_agente(url))


def montar_servicos() -> Servicos:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL não definida. Preencha o .env a partir do .env.example.")
    pool = abrir_pool(url)
    modo = os.environ.get("RESPONDEDOR", "teste").strip().lower()
    if modo == "agente":
        return Servicos(pool=pool, responder=montar_agente(url, pool), modo=modo)
    return Servicos(pool=pool, responder=RespondedorTeste(pool), modo="teste")
