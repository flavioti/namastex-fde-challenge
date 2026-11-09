"""Mascaramento de dados pessoais (FDD-0003)."""

from autoseguro.mascaramento.mascara import Achado, ResultadoMascara, detectar, mascarar_entrada, mascarar_saida

__all__ = ["Achado", "ResultadoMascara", "detectar", "mascarar_entrada", "mascarar_saida"]
