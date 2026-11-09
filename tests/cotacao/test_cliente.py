"""Cliente da cotação com MockTransport e sleep injetado, sem rede (FDD-0002, seção 11)."""

from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal

import httpx
import pytest

from autoseguro.cotacao import CotacaoClient, DadosCotacao

BASE = "http://quote.test"
DADOS = DadosCotacao(idade=35, veiculo_ano=2022, cep="01310-100", data_inicio=date(2026, 7, 15))


def _plano_ok(plano_id: str, premio: float = 119.9, pro_rata: bool = True) -> dict:
    corpo = {
        "plano_id": plano_id,
        "plano_nome": plano_id.capitalize(),
        "premio_mensal": premio,
        "franquia": 1500.0,
        "coberturas": ["Colisão", "Roubo e furto"],
        "carencia": {"coberturas": ["Roubo e furto"], "dias": 30, "observacao": "x"},
        "moeda": "BRL",
    }
    if pro_rata:
        corpo["primeiro_pagamento_pro_rata"] = {
            "dias_no_mes": 31, "dias_cobrados": 17, "valor_primeiro_pagamento": 65.7,
        }
    return corpo


def _cliente(handler, sleeps: list[float], relogio=None, **kwargs) -> CotacaoClient:
    return CotacaoClient(
        BASE,
        transporte=httpx.MockTransport(handler),
        sleep=sleeps.append,
        relogio=relogio or (lambda: 0.0),
        **kwargs,
    )


def _resposta_json(status: int, corpo: dict) -> httpx.Response:
    return httpx.Response(status, json=corpo)


def test_cotacao_completa_com_decimal_e_pro_rata():
    def handler(request: httpx.Request) -> httpx.Response:
        plano = json.loads(request.content)["plano_id"]
        return _resposta_json(200, _plano_ok(plano))

    sleeps: list[float] = []
    resultado = _cliente(handler, sleeps).cotar(DADOS)
    assert resultado.tipo == "sucesso"
    assert [p.plano_id for p in resultado.planos] == ["essencial", "completo", "premium"]
    primeiro = resultado.planos[0]
    assert isinstance(primeiro.premio_mensal, Decimal)
    assert primeiro.premio_mensal == Decimal("119.90")
    assert primeiro.primeiro_pagamento_pro_rata == Decimal("65.70")
    assert sleeps == []


def test_recusa_por_regra_com_motivo():
    def handler(request):
        return _resposta_json(422, {"error": "cotacao_recusada", "motivo": "Idade fora das faixas aceitas."})

    resultado = _cliente(handler, []).cotar(DADOS)
    assert resultado.tipo == "recusada"
    assert resultado.motivo == "Idade fora das faixas aceitas."


def test_payload_invalido_de_validacao_do_fastapi_nao_e_retentado():
    chamadas = []

    def handler(request):
        chamadas.append(1)
        return _resposta_json(422, {"detail": [{"loc": ["body", "idade"], "msg": "campo obrigatório"}]})

    resultado = _cliente(handler, []).cotar(DADOS)
    assert resultado.tipo == "payload_invalido"
    assert len(chamadas) == 3  # uma chamada por plano, nenhuma retentativa


def test_payload_invalido_400_nao_e_retentado():
    chamadas = []

    def handler(request):
        chamadas.append(1)
        return _resposta_json(400, {"error": "payload_invalido", "detalhe": "plano"})

    assert _cliente(handler, []).cotar(DADOS).tipo == "payload_invalido"
    assert len(chamadas) == 3


def test_falha_transitoria_e_recuperada_com_uma_espera():
    contagem: dict[str, int] = {}

    def handler(request):
        plano = json.loads(request.content)["plano_id"]
        contagem[plano] = contagem.get(plano, 0) + 1
        if plano == "essencial" and contagem[plano] == 1:
            return _resposta_json(503, {"error": "upstream_unavailable"})
        return _resposta_json(200, _plano_ok(plano))

    sleeps: list[float] = []
    resultado = _cliente(handler, sleeps).cotar(DADOS)
    assert resultado.tipo == "sucesso"
    assert sleeps == [0.5]


def test_falha_persistente_gera_indisponivel_com_esperas_de_meio_e_um_segundo():
    def handler(request):
        return _resposta_json(503, {"error": "upstream_unavailable"})

    sleeps: list[float] = []
    resultado = _cliente(handler, sleeps).cotar(DADOS)
    assert resultado.tipo == "indisponivel"
    # Cada um dos três planos tenta três vezes, com esperas de 0,5 s e 1 s.
    assert sleeps == [0.5, 1.0] * 3


def test_timeout_nas_tres_tentativas_gera_indisponivel():
    def handler(request):
        raise httpx.ReadTimeout("demorou", request=request)

    assert _cliente(handler, []).cotar(DADOS).tipo == "indisponivel"


def test_erro_de_conexao_e_retentado_e_recupera():
    contagem = {"n": 0}

    def handler(request):
        contagem["n"] += 1
        if contagem["n"] == 1:
            raise httpx.ConnectError("sem rede", request=request)
        plano = json.loads(request.content)["plano_id"]
        return _resposta_json(200, _plano_ok(plano))

    assert _cliente(handler, []).cotar(DADOS).tipo == "sucesso"


def test_status_inesperado_nao_e_retentado():
    chamadas = []

    def handler(request):
        chamadas.append(1)
        return httpx.Response(418, text="chá")

    assert _cliente(handler, []).cotar(DADOS).tipo == "indisponivel"
    assert len(chamadas) == 3


def test_resposta_200_malformada_vira_indisponivel():
    def handler(request):
        return httpx.Response(200, text="não é json")

    assert _cliente(handler, []).cotar(DADOS).tipo == "indisponivel"


def test_precedencia_payload_antes_de_recusa_e_recusa_antes_de_indisponivel():
    def handler(request):
        plano = json.loads(request.content)["plano_id"]
        if plano == "essencial":
            return _resposta_json(422, {"error": "cotacao_recusada", "motivo": "idade"})
        if plano == "completo":
            return _resposta_json(503, {"error": "upstream_unavailable"})
        return _resposta_json(200, _plano_ok(plano))

    assert _cliente(handler, []).cotar(DADOS).tipo == "recusada"

    def com_payload(request):
        plano = json.loads(request.content)["plano_id"]
        if plano == "premium":
            return _resposta_json(400, {"error": "payload_invalido", "detalhe": "x"})
        return _resposta_json(422, {"error": "cotacao_recusada", "motivo": "idade"})

    assert _cliente(com_payload, []).cotar(DADOS).tipo == "payload_invalido"


@pytest.mark.parametrize("valor, esperado", [(119.9, "119.90"), (10.005, "10.01")])
def test_conversao_de_valores_para_decimal(valor, esperado):
    def handler(request):
        plano = json.loads(request.content)["plano_id"]
        return _resposta_json(200, _plano_ok(plano, premio=valor))

    resultado = _cliente(handler, []).cotar(DADOS)
    assert resultado.planos[0].premio_mensal == Decimal(esperado)


def test_prazo_total_esgotado_encerra_como_indisponivel_sem_mais_tentativas():
    relogio = {"t": 0.0}

    def avanca(segundos: float):
        relogio["t"] += segundos

    chamadas = []

    def handler(request):
        chamadas.append(1)
        avanca(6.0)  # cada chamada consome 6 s de um prazo de 15 s
        return _resposta_json(503, {"error": "upstream_unavailable"})

    sleeps: list[float] = []
    cliente = _cliente(handler, sleeps, relogio=lambda: relogio["t"], prazo_total=15.0)
    resultado = cliente.cotar(DADOS)
    assert resultado.tipo == "indisponivel"
    # Plano essencial: t=6 (espera 0,5 s), t=12 (espera 1 s, t=13), t=19 (esgotou as tentativas).
    # Os planos completo e premium começam com o prazo já vencido e não chamam o serviço.
    assert len(chamadas) == 3
    assert sleeps == [0.5, 1.0]


def test_log_nao_contem_cep(caplog):
    def handler(request):
        plano = json.loads(request.content)["plano_id"]
        return _resposta_json(200, _plano_ok(plano))

    with caplog.at_level(logging.INFO, logger="autoseguro.cotacao"):
        _cliente(handler, []).cotar(DADOS)
    texto = " ".join(str(r.__dict__) for r in caplog.records)
    assert caplog.records
    assert "01310-100" not in texto and "01310100" not in texto


def test_corpo_enviado_tem_cep_do_estado_e_plano_correto():
    enviados = []

    def handler(request):
        enviados.append(json.loads(request.content))
        return _resposta_json(200, _plano_ok(enviados[-1]["plano_id"]))

    _cliente(handler, []).cotar(DADOS)
    assert [c["plano_id"] for c in enviados] == ["essencial", "completo", "premium"]
    assert all(c["cep"] == "01310-100" and c["data_inicio"] == "2026-07-15" for c in enviados)
