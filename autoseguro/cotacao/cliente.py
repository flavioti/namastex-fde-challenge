"""Cliente do serviço de cotação (FDD-0002; RFC-0006; ADR-0008).

O cliente é o único módulo que chama o serviço. Não valida regras de negócio: traduz as respostas
em um resultado tipado. Nenhum preço é inventado quando o serviço falha.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable, Optional

import httpx
from pydantic import ValidationError

from autoseguro.cotacao import config
from autoseguro.cotacao.modelos import (
    CotacaoIndisponivel,
    CotacaoPayloadInvalido,
    CotacaoRecusada,
    CotacaoSucesso,
    DadosCotacao,
    PlanoCotado,
    ResultadoCotacao,
    para_decimal,
)
from autoseguro.logs import obter_logger

_log = obter_logger("autoseguro.cotacao")

# Ordem de prioridade na agregação: erro de payload indica bug e aparece antes de qualquer outra situação.
_PRIORIDADE = ("payload_invalido", "recusada", "indisponivel")

_TRANSITORIOS = {500, 502, 503}


class _Falha(Exception):
    """Resultado de uma tentativa que não é sucesso. `transitoria` decide se a tentativa é repetida."""

    def __init__(self, resultado: ResultadoCotacao, transitoria: bool = False):
        self.resultado = resultado
        self.transitoria = transitoria


class CotacaoClient:
    def __init__(
        self,
        base_url: str,
        transporte: Optional[httpx.BaseTransport] = None,
        sleep: Callable[[float], None] = time.sleep,
        relogio: Callable[[], float] = time.monotonic,
        timeout: float = config.TIMEOUT_TENTATIVA_SEGUNDOS,
        prazo_total: float = config.PRAZO_TOTAL_SEGUNDOS,
        tentativas: int = config.TENTATIVAS,
        esperas: tuple[float, ...] = config.ESPERAS_SEGUNDOS,
    ):
        self._http = httpx.Client(base_url=base_url, transport=transporte)
        self._sleep = sleep
        self._relogio = relogio
        self._timeout = timeout
        self._prazo_total = prazo_total
        self._tentativas = tentativas
        self._esperas = esperas

    def fechar(self) -> None:
        self._http.close()

    def cotar(self, dados: DadosCotacao, conversa_id: uuid.UUID | None = None) -> ResultadoCotacao:
        """Cota os três planos em sequência, dentro de um único prazo total."""
        prazo_limite = self._relogio() + self._prazo_total
        resultados = [
            self._cotar_plano(plano, dados, prazo_limite, conversa_id) for plano in config.PLANOS
        ]
        return self._agregar(resultados)

    # ----- por plano -------------------------------------------------------

    def _cotar_plano(
        self,
        plano_id: str,
        dados: DadosCotacao,
        prazo_limite: float,
        conversa_id: uuid.UUID | None,
    ) -> ResultadoCotacao:
        corpo = {
            "plano_id": plano_id,
            "idade": dados.idade,
            "veiculo_ano": dados.veiculo_ano,
            "data_inicio": dados.data_inicio.isoformat(),
        }
        if dados.cep:
            corpo["cep"] = dados.cep

        ultimo_motivo = "tentativas esgotadas"
        for numero in range(1, self._tentativas + 1):
            restante = prazo_limite - self._relogio()
            if restante <= 0:
                return CotacaoIndisponivel(motivo="prazo total da cotação esgotado")
            try:
                return self._tentar(plano_id, corpo, min(self._timeout, restante), numero, conversa_id)
            except _Falha as falha:
                if not falha.transitoria:
                    return falha.resultado
                ultimo_motivo = getattr(falha.resultado, "motivo", ultimo_motivo)
                if numero < self._tentativas:
                    espera = self._esperas[min(numero - 1, len(self._esperas) - 1)]
                    if self._relogio() + espera >= prazo_limite:
                        return CotacaoIndisponivel(motivo="prazo total da cotação esgotado")
                    self._sleep(espera)
        return CotacaoIndisponivel(motivo=ultimo_motivo)

    def _tentar(
        self,
        plano_id: str,
        corpo: dict,
        timeout: float,
        numero: int,
        conversa_id: uuid.UUID | None,
    ) -> ResultadoCotacao:
        inicio = self._relogio()
        status: int | None = None
        try:
            resposta = self._http.post("/quote", json=corpo, timeout=httpx.Timeout(timeout))
            status = resposta.status_code
        except (httpx.TimeoutException, httpx.TransportError) as erro:
            self._registrar(plano_id, numero, None, inicio, "transitorio", conversa_id, type(erro).__name__)
            raise _Falha(CotacaoIndisponivel(motivo="falha de comunicação com a cotação"), transitoria=True)

        try:
            resultado = self._interpretar(resposta)
        except _Falha as falha:
            transitoria = falha.transitoria
            self._registrar(plano_id, numero, status, inicio, "transitorio" if transitoria else "definitivo",
                            conversa_id)
            raise
        self._registrar(plano_id, numero, status, inicio, resultado.tipo, conversa_id)
        return resultado

    def _interpretar(self, resposta: httpx.Response) -> ResultadoCotacao:
        status = resposta.status_code

        if status == 200:
            try:
                return CotacaoSucesso(planos=[self._plano(resposta.json())])
            except (ValueError, KeyError, TypeError, ValidationError):
                _log.warning("resposta de cotação malformada", extra={"evento": "cotacao_malformada"})
                raise _Falha(CotacaoIndisponivel(motivo="resposta malformada da cotação"))

        if status == 422:
            corpo = _json_seguro(resposta)
            if corpo.get("error") == "cotacao_recusada":
                raise _Falha(CotacaoRecusada(motivo=str(corpo.get("motivo", "cotação recusada"))))
            if "detail" in corpo or corpo.get("error") == "payload_invalido":
                raise _Falha(CotacaoPayloadInvalido(detalhe=str(corpo.get("detail", corpo.get("detalhe", "")))))
            raise _Falha(CotacaoIndisponivel(motivo=f"status {status} inesperado da cotação"))

        if status == 400:
            corpo = _json_seguro(resposta)
            raise _Falha(CotacaoPayloadInvalido(detalhe=str(corpo.get("detalhe", "payload inválido"))))

        if status in _TRANSITORIOS:
            raise _Falha(CotacaoIndisponivel(motivo="serviço de cotação indisponível"), transitoria=True)

        raise _Falha(CotacaoIndisponivel(motivo=f"status {status} inesperado da cotação"))

    @staticmethod
    def _plano(corpo: dict) -> PlanoCotado:
        """Converte a resposta de um plano. A API devolve o pro-rata como objeto, e o valor fica em
        valor_primeiro_pagamento."""
        pro_rata = corpo.get("primeiro_pagamento_pro_rata")
        valor_pro_rata = None
        if isinstance(pro_rata, dict) and pro_rata.get("valor_primeiro_pagamento") is not None:
            valor_pro_rata = para_decimal(pro_rata["valor_primeiro_pagamento"])
        carencia = corpo.get("carencia") or {}
        return PlanoCotado(
            plano_id=corpo["plano_id"],
            plano_nome=corpo["plano_nome"],
            premio_mensal=para_decimal(corpo["premio_mensal"]),
            franquia=para_decimal(corpo["franquia"]),
            coberturas=list(corpo["coberturas"]),
            carencia_dias=int(carencia.get("dias", 0)),
            primeiro_pagamento_pro_rata=valor_pro_rata,
        )

    # ----- agregação e log ---------------------------------------------------

    @staticmethod
    def _agregar(resultados: list[ResultadoCotacao]) -> ResultadoCotacao:
        if all(isinstance(r, CotacaoSucesso) for r in resultados):
            planos = [plano for r in resultados for plano in r.planos]
            return CotacaoSucesso(planos=planos)
        for tipo in _PRIORIDADE:
            for r in resultados:
                if r.tipo == tipo:
                    return r
        return CotacaoIndisponivel(motivo="resultado inesperado")

    def _registrar(
        self,
        plano_id: str,
        numero: int,
        status: int | None,
        inicio: float,
        resultado: str,
        conversa_id: uuid.UUID | None,
        erro: str | None = None,
    ) -> None:
        duracao_ms = round((self._relogio() - inicio) * 1000, 1)
        _log.info(
            "tentativa de cotação",
            extra={
                "evento": "tentativa_cotacao",
                "conversa_id": str(conversa_id) if conversa_id else None,
                "detalhe": {
                    "plano": plano_id,
                    "tentativa": numero,
                    "status": status,
                    "duracao_ms": duracao_ms,
                    "resultado": resultado,
                    "erro": erro,
                },
            },
        )


def _json_seguro(resposta: httpx.Response) -> dict:
    try:
        corpo = resposta.json()
    except ValueError:
        return {}
    return corpo if isinstance(corpo, dict) else {}
