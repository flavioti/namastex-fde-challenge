"""Nenhum valor original vaza para a saída, para os logs ou para o registro de log (FDD-0003, seções 7 e 9)."""

from __future__ import annotations

import logging

from autoseguro.mascaramento import mascarar_entrada, mascarar_saida

TEXTO_COM_DADOS = "CPF 123.456.789-09, mail ana@exemplo.com, CEP 01310-100, tel (11) 91234-5678, placa ABC-1234"
VALORES = ["123.456.789-09", "ana@exemplo.com", "01310-100", "91234-5678", "ABC-1234"]


def test_valores_originais_nao_aparecem_na_entrada_nem_na_saida():
    for valor in VALORES:
        assert valor not in mascarar_entrada(TEXTO_COM_DADOS).texto
        assert valor not in mascarar_saida(TEXTO_COM_DADOS).texto


def test_logs_de_mascaramento_nao_contem_valor(caplog):
    with caplog.at_level(logging.INFO, logger="autoseguro.mascaramento"):
        mascarar_entrada(TEXTO_COM_DADOS)
        mascarar_saida(TEXTO_COM_DADOS)
    mensagens = " ".join(registro.getMessage() for registro in caplog.records)
    extras = " ".join(str(registro.__dict__) for registro in caplog.records)
    assert caplog.records, "o mascaramento deve registrar cada chamada"
    for valor in VALORES:
        assert valor not in mensagens
        assert valor not in extras


def test_registro_de_log_traz_pontos_e_contagem(caplog):
    with caplog.at_level(logging.INFO, logger="autoseguro.mascaramento"):
        mascarar_entrada(TEXTO_COM_DADOS)
    registro = caplog.records[-1]
    assert registro.ponto == "entrada"
    assert registro.contagem == {"cpf": 1, "email": 1, "cep": 1, "telefone": 1, "placa": 1}
