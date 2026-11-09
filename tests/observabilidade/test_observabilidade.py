"""Redação antes do envio, chaves de metadado e feedback do juiz, sem rede (FDD-0006, seções 5 a 8)."""

from __future__ import annotations

import re
import uuid

import pytest

from autoseguro.juiz.modelos import DecisaoJuiz
from autoseguro.observabilidade import config
from autoseguro.observabilidade.cliente import PAYLOAD_VAZIO, _ocultar
from autoseguro.observabilidade.feedback import feedbacks_do_juiz, registrar_feedbacks
from autoseguro.observabilidade.redacao import RedacaoFalhou, redigir


def test_redacao_substitui_dados_pessoais_recursivamente():
    payload = {"entrada": "meu CPF é 123.456.789-09", "lista": ["CEP 01310-100"], "n": 3}
    redigido = redigir(payload)
    assert "123.456.789-09" not in str(redigido)
    assert "01310-100" not in str(redigido)
    assert redigido["n"] == 3


def test_redacao_nao_altera_o_original():
    original = {"texto": "CPF 123.456.789-09"}
    redigir(original)
    assert original == {"texto": "CPF 123.456.789-09"}


def test_falha_da_redacao_levanta_erro_e_ocultar_devolve_vazio(monkeypatch):
    def quebrar(valor):
        raise ValueError("falha simulada")

    monkeypatch.setattr("autoseguro.observabilidade.redacao._redigir_valor", quebrar)
    with pytest.raises(RedacaoFalhou):
        redigir({"a": "b"})
    assert _ocultar({"a": "b"}) == PAYLOAD_VAZIO


def test_chaves_de_metadado_sao_o_dicionario_unico():
    assert set(config.CHAVES) == {"conversa_id", "versao_prompt", "modelo", "etapa", "tipo_execucao"}
    assert config.PROJETO == "autoseguro-mvp"
    assert config.TAGS_VALIDAS == ("teste", "demonstracao", "avaliacao")


def test_tracing_desligado_por_padrao(monkeypatch):
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    assert config.tracing_ativo() is False
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    assert config.tracing_ativo() is True


def test_feedback_sem_violacao_pontua_todas_as_regras_como_aprovadas():
    itens = {i["key"]: i for i in feedbacks_do_juiz(DecisaoJuiz(aprovado=True))}
    assert [itens[f"juiz_regra_{n}"]["score"] for n in range(1, 5)] == [1, 1, 1, 1]
    assert itens["juiz_decisao"]["score"] == 1


def test_feedback_com_violacao_marca_a_regra_e_a_decisao():
    itens = {i["key"]: i for i in feedbacks_do_juiz(DecisaoJuiz(aprovado=False, regra="R2", motivo="x"))}
    assert itens["juiz_regra_2"]["score"] == 0
    assert itens["juiz_regra_1"]["score"] == 1
    assert itens["juiz_decisao"]["score"] == 0
    assert itens["juiz_regra_2"]["comment"] == "R2 reprovada"


def test_comentario_do_feedback_nunca_traz_valor_ou_dado_pessoal():
    decisao = DecisaoJuiz(aprovado=False, regra="R1", motivo="valor fora da cotação oficial")
    for item in feedbacks_do_juiz(decisao):
        # Só o código da regra (R1 a R4) pode ter dígito. Nada de valor monetário nem sequência numérica.
        assert "R$" not in item["comment"]
        assert not re.search(r"\d{2,}|\d[.,]\d", item["comment"])


class ClienteFalso:
    def __init__(self, falhar_em=()):
        self.enviados = []
        self.falhar_em = set(falhar_em)

    def create_feedback(self, run_id, key, score, comment):
        if key in self.falhar_em:
            raise RuntimeError("falha de rede simulada")
        self.enviados.append((key, score))


def test_falha_de_um_feedback_nao_impede_os_demais():
    cliente = ClienteFalso(falhar_em={"juiz_regra_3"})
    enviados = registrar_feedbacks(cliente, uuid.uuid4(), DecisaoJuiz(aprovado=True))
    assert enviados == 4  # cinco feedbacks ao todo, e um falhou
    assert ("juiz_decisao", 1) in cliente.enviados
