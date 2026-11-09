"""Cliente do serviço de cotação (FDD-0002)."""

from autoseguro.cotacao.cliente import CotacaoClient
from autoseguro.cotacao.modelos import DadosCotacao, PlanoCotado, ResultadoCotacao

__all__ = ["CotacaoClient", "DadosCotacao", "PlanoCotado", "ResultadoCotacao"]
