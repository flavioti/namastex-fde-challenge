"""Orquestração do juiz: R1 em código, depois R2 a R4 pelo modelo (FDD-0009 seções 7 a 10).

Nenhuma falha do juiz libera o rascunho. Falha fechada, conforme a RFC-0009.
"""

from __future__ import annotations

import json
import time
from typing import Callable

from pydantic import ValidationError

from autoseguro.juiz import prompts, r1
from autoseguro.juiz.modelos import DecisaoJuiz, VeredictoJuiz
from autoseguro.logs import obter_logger
from autoseguro.mascaramento import detectar
from autoseguro.juiz.extracao import extrair_valores

_log = obter_logger("autoseguro.juiz")

TENTATIVAS = 3
ESPERAS = (0.5, 1.0)
MOTIVO_FALHA = "falha do juiz"
MOTIVO_OMITIDO = "motivo omitido"


class Juiz:
    def __init__(self, modelo, sleep: Callable[[float], None] = time.sleep):
        """`modelo` implementa `estruturar(sistema, conteudo, schema)`, que devolve uma instância de schema."""
        self._modelo = modelo
        self._sleep = sleep

    def avaliar(
        self,
        rascunho: str,
        planos: list[dict] | None,
        status: str,
        motivo_cotacao: str | None,
    ) -> DecisaoJuiz:
        r1_resultado = r1.verificar(rascunho, planos)
        if not r1_resultado.aprovado:
            _log.info("juiz reprovou em R1", extra={"evento": "juiz", "detalhe": {"regra": "R1"}})
            return DecisaoJuiz(aprovado=False, regra="R1", motivo=r1_resultado.motivo, tentativas=0)

        conteudo = json.dumps(
            {
                "rascunho": rascunho,
                "status": status,
                "motivo_cotacao": motivo_cotacao,
                "planos": planos or [],
            },
            ensure_ascii=False,
            default=str,
        )
        ultimo_erro: Exception | None = None
        for numero in range(1, TENTATIVAS + 1):
            try:
                veredicto = self._modelo.estruturar(prompts.INSTRUCOES, conteudo, VeredictoJuiz)
                if not isinstance(veredicto, VeredictoJuiz):
                    raise TypeError("saída fora do formato VeredictoJuiz")
                return self._decidir(veredicto, numero)
            except (ValidationError, TypeError, ValueError, RuntimeError) as erro:
                ultimo_erro = erro
                _log.warning("falha do juiz, tentativa", extra={"evento": "juiz_falha",
                                                                "detalhe": {"tentativa": numero}})
                if numero < TENTATIVAS:
                    self._sleep(ESPERAS[numero - 1])
        _log.error("juiz falhou após três tentativas", extra={"evento": "juiz_falha_total",
                                                              "detalhe": {"tipo": type(ultimo_erro).__name__}})
        return DecisaoJuiz(aprovado=False, regra=None, motivo=MOTIVO_FALHA, tentativas=TENTATIVAS)

    @staticmethod
    def _decidir(veredicto: VeredictoJuiz, tentativas: int) -> DecisaoJuiz:
        motivo = _sanitizar_motivo(veredicto.motivo)
        if veredicto.aprovado:
            return DecisaoJuiz(aprovado=True, regra=None, motivo="", tentativas=tentativas)
        return DecisaoJuiz(aprovado=False, regra=veredicto.regra, motivo=motivo, tentativas=tentativas)


def _sanitizar_motivo(motivo: str) -> str:
    """O motivo vai para os traces. Se tiver valor monetário ou dado pessoal, é omitido (FDD-0009, seção 9)."""
    if extrair_valores(motivo) or detectar(motivo) or "R$" in motivo:
        return MOTIVO_OMITIDO
    return motivo
