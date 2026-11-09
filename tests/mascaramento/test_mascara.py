"""Corpus de variações e textos que não devem ser mascarados (FDD-0003, seções 4, 6 e 8)."""

from __future__ import annotations

import pytest

from autoseguro.mascaramento import detectar, mascarar_entrada, mascarar_saida


@pytest.mark.parametrize(
    "texto, tipo, valor",
    [
        ("meu CPF é 123.456.789-09", "cpf", "123.456.789-09"),
        ("meu CPF é 12345678909", "cpf", "12345678909"),
        ("cpf  123.456.789-09  ok", "cpf", "123.456.789-09"),
        ("contato ana.silva+seguro@mail.empresa.com.br", "email", "ana.silva+seguro@mail.empresa.com.br"),
        ("mande para joao_99@exemplo.com", "email", "joao_99@exemplo.com"),
        ("moro no CEP 01310-100", "cep", "01310-100"),
        ("moro no CEP 01310100", "cep", "01310100"),
        ("me liga no +55 11 91234-5678", "telefone", "+55 11 91234-5678"),
        ("telefone (11) 91234-5678", "telefone", "(11) 91234-5678"),
        ("telefone 11 912345678", "telefone", "11 912345678"),
        ("telefone 11 91234-5678", "telefone", "11 91234-5678"),
        ("placa ABC-1234 do carro", "placa", "ABC-1234"),
        ("placa ABC1234 do carro", "placa", "ABC1234"),
        ("placa BRA2E19 do carro", "placa", "BRA2E19"),
        ("placa bra2e19 do carro", "placa", "bra2e19"),
    ],
)
def test_dado_pessoal_e_detectado(texto, tipo, valor):
    achados = detectar(texto)
    assert [(a.tipo, a.valor) for a in achados] == [(tipo, valor)]


@pytest.mark.parametrize(
    "texto",
    [
        "o preço é R$ 119,90 por mês",
        "a vigência começa em 2026-07-15",
        "tenho 35 anos",
        "o carro é de 2022",
        "",
    ],
)
def test_texto_sem_dado_pessoal_passa_inalterado(texto):
    resultado = mascarar_entrada(texto)
    assert resultado.texto == texto
    assert resultado.achados == []
    assert resultado.contagem == {}


def test_entrada_usa_marcadores_por_tipo():
    texto = "CPF 123.456.789-09, CEP 01310-100, placa ABC-1234"
    resultado = mascarar_entrada(texto)
    assert resultado.texto == "CPF [CPF], CEP [CEP], placa [PLACA]"
    assert resultado.contagem == {"cpf": 1, "cep": 1, "placa": 1}


def test_saida_usa_texto_neutro():
    texto = "Seu CPF 123.456.789-09 está confirmado."
    resultado = mascarar_saida(texto)
    assert resultado.texto == "Seu CPF [dado omitido] está confirmado."


def test_marcador_nao_e_mascarado_de_novo():
    primeira = mascarar_entrada("CPF 123.456.789-09 e CEP 01310-100")
    segunda = mascarar_entrada(primeira.texto)
    assert segunda.texto == primeira.texto
    assert segunda.achados == []


def test_ordem_de_precedencia_cpf_antes_de_telefone():
    # 11 dígitos sem separador casam com CPF e com telefone. CPF vem antes na ordem fixa.
    achados = detectar("numero 11912345678")
    assert [a.tipo for a in achados] == ["cpf"]


def test_espacos_e_quebras_de_linha_sao_preservados():
    texto = "linha 1\n  CEP 01310-100\n\tfim"
    assert mascarar_entrada(texto).texto == "linha 1\n  CEP [CEP]\n\tfim"


def test_posicoes_apontam_para_o_texto_original():
    texto = "oi 01310-100 fim"
    achado = detectar(texto)[0]
    assert texto[achado.inicio:achado.fim] == "01310-100"
