"""Redação antes do envio ao LangSmith (FDD-0006, seção 6; FDD-0003).

Todo texto que sai da aplicação para o LangSmith passa por aqui. Os valores originais de CPF e CEP
ficam no estado, e nunca chegam a este módulo. Este módulo só vê o que já foi mascarado, e ainda assim
aplica o mascaramento de novo, como garantia.
"""

from __future__ import annotations

from typing import Any

from autoseguro.logs import obter_logger
from autoseguro.mascaramento import mascarar_saida

_log = obter_logger("autoseguro.observabilidade")


class RedacaoFalhou(RuntimeError):
    """A redação não conseguiu produzir um payload seguro."""


def _redigir_valor(valor: Any) -> Any:
    if isinstance(valor, str):
        return mascarar_saida(valor).texto
    if isinstance(valor, dict):
        return {str(chave): _redigir_valor(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_redigir_valor(item) for item in valor]
    return valor


def redigir(payload: Any) -> Any:
    """Devolve uma cópia do payload com todo dado pessoal substituído. Nunca devolve o original.

    Lança RedacaoFalhou se algo der errado. Quem chama decide o que enviar nesse caso.
    """
    try:
        return _redigir_valor(payload)
    except Exception as erro:
        _log.error("redação falhou, conteúdo não enviado", extra={"evento": "redacao_falhou"})
        raise RedacaoFalhou("redação falhou") from erro
