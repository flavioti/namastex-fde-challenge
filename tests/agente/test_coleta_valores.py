"""Extração determinística de cada campo (FDD-0005, seção 7; FDD-0001, seção 3)."""

from __future__ import annotations

from datetime import date

import pytest

from autoseguro.agente import coleta_valores as cv

HOJE = date(2026, 11, 9)


@pytest.mark.parametrize("texto, esperado", [("35", 35), (" 35 ", 35), ("35 anos", 35), ("1", 1), ("120", 120)])
def test_idade_aceita(texto, esperado):
    assert cv.extrair_idade(texto) == esperado


@pytest.mark.parametrize("texto", ["0", "121", "tenho uns 35", "trinta", "", "35,5"])
def test_idade_recusada(texto):
    assert cv.extrair_idade(texto) is None


def test_ano_veiculo_dentro_da_faixa():
    assert cv.extrair_ano_veiculo("2022", HOJE) == 2022
    assert cv.extrair_ano_veiculo("1950", HOJE) == 1950


@pytest.mark.parametrize("texto", ["1800", "2030", "22", "ano 2022"])
def test_ano_veiculo_recusado(texto):
    assert cv.extrair_ano_veiculo(texto, HOJE) is None


@pytest.mark.parametrize("texto, esperado", [("01310-100", "01310-100"), ("01310100", "01310-100")])
def test_cep_com_ou_sem_hifen(texto, esperado):
    assert cv.extrair_cep(texto) == esperado


def test_cep_com_oito_digitos_errados_recusado():
    assert cv.extrair_cep("0131010") is None


def test_data_no_formato_brasileiro():
    assert cv.extrair_data_inicio("15/12/2026", HOJE) == date(2026, 12, 15)
    assert cv.extrair_data_inicio("15-12-2026", HOJE) == date(2026, 12, 15)


def test_data_anterior_a_hoje_recusada():
    assert cv.extrair_data_inicio("01/01/2026", HOJE) is None


def test_data_inexistente_recusada():
    assert cv.extrair_data_inicio("31/02/2027", HOJE) is None


def test_data_de_hoje_aceita():
    assert cv.extrair_data_inicio("09/11/2026", HOJE) == HOJE


@pytest.mark.parametrize("texto, esperado", [
    ("123.456.789-09", "12345678909"),
    ("12345678909", "12345678909"),
])
def test_cpf_com_ou_sem_pontuacao(texto, esperado):
    assert cv.extrair_cpf(texto) == esperado


def test_cpf_incompleto_recusado():
    assert cv.extrair_cpf("123.456.789") is None


@pytest.mark.parametrize("texto, esperado", [
    ("quero o premium", "premium"),
    ("Essencial, por favor", "essencial"),
    ("não sei", None),
    ("completo ou premium", None),
])
def test_plano(texto, esperado):
    assert cv.extrair_plano(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("sim", True),
    ("pode coletar", True),
    ("não autorizo", False),
    ("nao", False),
    ("talvez", None),
])
def test_consentimento(texto, esperado):
    assert cv.extrair_consentimento(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("Para que serve esse serviço?", True),
    ("qual o preço?", True),
    ("Oi, boa noite", True),
    ("obrigado", True),
    ("trinta", False),
    ("tenho uns 35", False),
    ("35", False),
])
def test_outro_contexto(texto, esperado):
    assert cv.eh_outro_contexto(texto) == esperado
