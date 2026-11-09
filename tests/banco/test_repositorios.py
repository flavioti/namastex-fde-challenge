"""Repositórios: trava de turno, mensagens, cotações, encaminhamento, trace e catálogo (FDD-0004 e FDD-0007)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from autoseguro.banco.repositorios import avaliacoes, conversas, cotacoes, encaminhamentos
from autoseguro.banco.repositorios import mensagens, regras, trechos

AGORA = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


def _conversa(conexao) -> uuid.UUID:
    return conversas.criar_conversa(conexao, "Lead Teste", "11999990000", agora=AGORA)


def test_trava_adquirida_uma_vez_e_liberada(conexao):
    conversa_id = _conversa(conexao)
    assert conversas.adquirir_trava(conexao, conversa_id, agora=AGORA) is True
    assert conversas.adquirir_trava(conexao, conversa_id, agora=AGORA + timedelta(seconds=5)) is False
    conversas.liberar_trava(conexao, conversa_id)
    assert conversas.adquirir_trava(conexao, conversa_id, agora=AGORA + timedelta(seconds=6)) is True


def test_trava_expirada_pode_ser_adquirida(conexao):
    conversa_id = _conversa(conexao)
    assert conversas.adquirir_trava(conexao, conversa_id, agora=AGORA)
    depois_de_16_minutos = AGORA + timedelta(minutes=16)
    assert conversas.adquirir_trava(conexao, conversa_id, agora=depois_de_16_minutos) is True


def test_status_invalido_nao_e_gravado(conexao):
    conversa_id = _conversa(conexao)
    with pytest.raises(ValueError):
        conversas.atualizar_status(conexao, conversa_id, "inventado")


def test_mensagens_seguem_ordem_e_guardam_texto_mascarado(conexao):
    conversa_id = _conversa(conexao)
    assert mensagens.registrar_mensagem(conexao, conversa_id, "lead", "Oi, meu CPF é [CPF]", agora=AGORA) == 1
    assert mensagens.registrar_mensagem(conexao, conversa_id, "agente", "Olá!", agora=AGORA) == 2
    lista = mensagens.listar_mensagens(conexao, conversa_id)
    assert [m["ordem"] for m in lista] == [1, 2]
    assert lista[0]["conteudo_mascarado"] == "Oi, meu CPF é [CPF]"


def test_cotacao_com_valores_decimais_em_jsonb(conexao):
    conversa_id = _conversa(conexao)
    planos = [{"plano_id": "essencial", "premio_mensal": "129.90"}]
    cotacoes.registrar_cotacao(conexao, conversa_id, "sucesso", planos=planos, agora=AGORA)
    registro = cotacoes.listar_cotacoes(conexao, conversa_id)[0]
    assert registro["resultado"] == "sucesso"
    assert registro["planos"] == planos


def test_resultado_de_cotacao_invalido_nao_e_gravado(conexao):
    conversa_id = _conversa(conexao)
    with pytest.raises(ValueError):
        cotacoes.registrar_cotacao(conexao, conversa_id, "talvez")


def test_encaminhamento_guarda_cpf_e_e_unico(conexao):
    conversa_id = _conversa(conexao)
    encaminhamentos.registrar_encaminhamento(
        conexao, conversa_id, "pedido_humano", "Lead pediu vendedor", cpf="12345678909", agora=AGORA
    )
    registro = encaminhamentos.obter_encaminhamento(conexao, conversa_id)
    assert registro["cpf"] == "12345678909"
    with pytest.raises(Exception):
        encaminhamentos.registrar_encaminhamento(conexao, conversa_id, "pedido_humano", "de novo")


def test_referencia_de_trace_gravada_uma_vez(conexao):
    conversa_id = _conversa(conexao)
    avaliacoes.registrar_referencia_trace(conexao, conversa_id, "trace-1")
    avaliacoes.registrar_referencia_trace(conexao, conversa_id, "trace-2")
    assert avaliacoes.obter_referencia_trace(conexao, conversa_id) == "trace-1"


def test_resultado_de_avaliacao_com_regra_valida(conexao):
    avaliacoes.registrar_resultado_avaliacao(conexao, "rodada-1", "caso-1", "R1", True, agora=AGORA)
    with pytest.raises(ValueError):
        avaliacoes.registrar_resultado_avaliacao(conexao, "rodada-1", "caso-1", "R9", True)


def test_catalogo_upsert_e_desativacao_sem_apagar(conexao):
    regra_a = uuid.uuid5(uuid.NAMESPACE_URL, "faixa_etaria:18-24")
    regra_b = uuid.uuid5(uuid.NAMESPACE_URL, "carencia")
    regras.upsert_regra(conexao, regra_a, "faixa_etaria", {"idade_min": 18}, "h1")
    regras.upsert_regra(conexao, regra_b, "carencia", {"dias": 30}, "h2")
    regras.upsert_regra(conexao, regra_a, "faixa_etaria", {"idade_min": 18}, "h1-novo")
    assert regras.obter_regra(conexao, regra_a)["impressao_digital"] == "h1-novo"

    desativadas = regras.desativar_regras_ausentes(conexao, [regra_a])
    assert desativadas >= 1
    assert regras.obter_regra(conexao, regra_b)["ativa"] is False
    assert regras.obter_regra(conexao, regra_a) is not None


def test_plano_upsert_com_decimal(conexao):
    regras.upsert_plano(conexao, "essencial", "Essencial", Decimal("100.00"), Decimal("500.00"), ["Incêndio"])
    regras.upsert_plano(conexao, "essencial", "Essencial", Decimal("129.90"), Decimal("500.00"), ["Incêndio"])
    planos = {p["id"]: p for p in regras.listar_planos(conexao)}
    assert planos["essencial"]["base_mensal"] == Decimal("129.90")


def test_trecho_com_um_por_regra_e_upsert(conexao):
    regra = uuid.uuid4()
    regras.upsert_regra(conexao, regra, "pro_rata", {}, "h")
    vetor = [0.0] * 384
    trechos.upsert_trecho(conexao, regra, "texto antigo", vetor, "e5", "h1", agora=AGORA)
    trechos.upsert_trecho(conexao, regra, "texto novo", vetor, "e5", "h2", agora=AGORA)
    assert trechos.obter_impressao_trecho(conexao, regra) == "h2"
    total = conexao.execute(
        "SELECT count(*) FROM regras.trechos WHERE regra_id = %s", (regra,)
    ).fetchone()[0]
    assert total == 1


def test_trecho_com_dimensao_errada_nao_e_gravado(conexao):
    regra = uuid.uuid4()
    regras.upsert_regra(conexao, regra, "pro_rata", {}, "h")
    with pytest.raises(ValueError):
        trechos.upsert_trecho(conexao, regra, "x", [0.0] * 3, "e5", "h")
