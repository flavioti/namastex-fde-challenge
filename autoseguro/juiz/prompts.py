"""Instruções do juiz para R2, R3 e R4, e gatilho de acionamento (FDD-0009, seções 5 e 8)."""

from __future__ import annotations

import re

VERSAO_PROMPT = "juiz-1"

# Termos fixos de recusa ou indisponibilidade que também acionam o juiz (FDD-0009, seção 5).
TERMOS_RECUSA = (
    "não é possível cotar",
    "nao e possivel cotar",
    "não consegui cotar",
    "recusad",
    "indisponív",
    "indisponiv",
)

_VALOR_RS = re.compile(r"R\$")
_NUMERO_COM_SEPARADOR = re.compile(r"\d+[.,]\d{1,2}\b")

INSTRUCOES = """Você é o juiz de uma resposta de agente de cotação de seguro de veículo.
Avalie somente o rascunho recebido e responda no formato pedido.

R2. A recusa ou o encaminhamento do rascunho deve ser coerente com o status e o motivo da cotação informados.
R3. O rascunho não pode prometer apólice, boleto, contratação ou emissão.
R4. O rascunho não pode conter dado pessoal sem máscara (CPF, CEP, e-mail, telefone ou placa).

Aprove somente se nenhuma regra foi violada. Ao reprovar, informe a regra violada e um motivo curto,
de até 200 caracteres, sem valor monetário e sem dado pessoal.
"""


def acionado(rascunho: str) -> bool:
    """O juiz é chamado quando o rascunho cita valor ou traz recusa ou indisponibilidade."""
    texto = rascunho.lower()
    if _VALOR_RS.search(rascunho) or _NUMERO_COM_SEPARADOR.search(rascunho):
        return True
    return any(termo in texto for termo in TERMOS_RECUSA)
