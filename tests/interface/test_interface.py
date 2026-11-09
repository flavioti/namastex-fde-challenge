"""Trava, leads, fluxo de turno e página com AppTest, sem rede nem modelo (FDD-0007, seção 12)."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from autoseguro.banco.conexao import abrir_pool
from autoseguro.banco.repositorios import conversas
from autoseguro.interface import consultas, leads
from autoseguro.interface.respondedor import FRASE_FIXA, RespondedorTeste
from autoseguro.interface.trava import TravaOcupada, turno_travado
from autoseguro.interface.turno import MENSAGEM_NEUTRA, processar_turno

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "ui-app" / "app.py"
AGORA = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def pool(url_banco):
    pool = abrir_pool(url_banco)
    yield pool
    pool.close()


def _conversa(pool, status="em_andamento") -> uuid.UUID:
    with pool.connection() as conexao:
        cid = conversas.criar_conversa(conexao, "Lead Teste", "(11) 91234-5678", agora=AGORA)
        if status != "em_andamento":
            conversas.atualizar_status(conexao, cid, status, agora=AGORA)
    return cid


# ----- trava ------------------------------------------------------------------

def test_trava_conflita_com_turno_em_andamento(pool):
    cid = _conversa(pool)
    with turno_travado(pool, cid, agora=AGORA):
        with pytest.raises(TravaOcupada):
            with turno_travado(pool, cid, agora=AGORA + timedelta(seconds=1)):
                pass


def test_trava_liberada_mesmo_quando_o_turno_falha(pool):
    cid = _conversa(pool)
    with pytest.raises(ValueError):
        with turno_travado(pool, cid, agora=AGORA):
            raise ValueError("falha simulada")
    with turno_travado(pool, cid, agora=AGORA + timedelta(seconds=2)):
        pass


def test_trava_expirada_pode_ser_adquirida(pool):
    cid = _conversa(pool)
    with pool.connection() as conexao:
        conversas.adquirir_trava(conexao, cid, agora=AGORA)
    with turno_travado(pool, cid, agora=AGORA + timedelta(minutes=16)):
        pass


# ----- leads ------------------------------------------------------------------

def test_leads_vem_das_listas_do_arquivo():
    listas = leads.carregar_listas()
    lead = leads.gerar_lead(listas, random.Random(7))
    primeiro, sobrenome = lead.nome.split(" ", 1)
    assert primeiro in listas.primeiros and sobrenome in listas.sobrenomes


def test_telefone_tem_ddd_da_lista_e_formato_valido():
    listas = leads.carregar_listas()
    for semente in range(20):
        lead = leads.gerar_lead(listas, random.Random(semente))
        assert lead.telefone[1:3].isdigit() and int(lead.telefone[1:3]) in listas.ddds
        assert lead.telefone[4] == " " and lead.telefone[10] == "-"  # (DD) 9xxxx-xxxx
        assert len("".join(ch for ch in lead.telefone if ch.isdigit())) == 11


# ----- turno ------------------------------------------------------------------

def test_turno_com_respondedor_grava_mensagens_mascaradas(pool):
    cid = _conversa(pool)
    resultado = processar_turno(pool, RespondedorTeste(pool), cid, "meu CPF é 123.456.789-09", agora=AGORA)
    assert resultado.texto_agente == FRASE_FIXA
    textos = [m["texto"] for m in consultas.mensagens_da_conversa(pool, cid)]
    assert "[CPF]" in textos[0] and "123.456.789-09" not in textos[0]


class RespondedorQueFalha:
    def turno(self, conversa_id, texto):
        raise RuntimeError("erro interno com texto do lead")


def test_erro_no_turno_mostra_mensagem_neutra_e_libera_a_trava(pool):
    cid = _conversa(pool)
    resultado = processar_turno(pool, RespondedorQueFalha(), cid, "oi", agora=AGORA)
    assert resultado.erro and resultado.texto_agente == MENSAGEM_NEUTRA
    with turno_travado(pool, cid, agora=AGORA + timedelta(seconds=1)):
        pass


def test_conversa_encaminhada_nao_recebe_turno(pool):
    cid = _conversa(pool, status="encaminhada")
    resultado = processar_turno(pool, RespondedorTeste(pool), cid, "oi", agora=AGORA)
    assert resultado.bloqueada


def test_turno_em_andamento_nao_envia(pool):
    cid = _conversa(pool)
    with turno_travado(pool, cid, agora=AGORA):
        resultado = processar_turno(pool, RespondedorTeste(pool), cid, "oi", agora=AGORA + timedelta(seconds=1))
    assert resultado.ocupada and resultado.texto_agente is None


def test_encaminhados_mostra_cpf_sem_mascara(pool):
    from autoseguro.banco.repositorios import encaminhamentos

    cid = _conversa(pool)
    with pool.connection() as conexao:
        encaminhamentos.registrar_encaminhamento(conexao, cid, "Pedido do lead", "resumo", cpf="12345678909",
                                                 agora=AGORA)
    linhas = consultas.encaminhados(pool)
    assert any(linha["cpf"] == "12345678909" for linha in linhas)


# ----- página -----------------------------------------------------------------

@pytest.fixture
def ambiente_app(url_banco, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url_banco)
    monkeypatch.setenv("RESPONDEDOR", "teste")


def test_pagina_cria_conversa_e_responde_no_chat(ambiente_app):
    at = AppTest.from_file(str(APP), default_timeout=20)
    at.run()
    assert not at.exception
    botao = [b for b in at.button if b.label == "Nova conversa"][0]
    botao.click().run()
    assert not at.exception
    at.chat_input[0].set_value("oi").run()
    assert not at.exception
    textos = [md.value for md in at.markdown]
    assert any(FRASE_FIXA in t for t in textos)


def test_pagina_mostra_turno_em_andamento(ambiente_app, url_banco):
    at = AppTest.from_file(str(APP), default_timeout=20)
    at.run()
    [b for b in at.button if b.label == "Nova conversa"][0].click().run()
    cid = at.session_state["conversa_id"]
    pool = abrir_pool(url_banco)
    try:
        with turno_travado(pool, cid):
            at.chat_input[0].set_value("oi").run()
            assert any("turno em andamento" in w.value for w in at.warning)
    finally:
        pool.close()
