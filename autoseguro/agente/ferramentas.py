"""Ferramenta de cotação exposta ao modelo (ADR-0015; FDD-0005, seções 7 e 8 e 16).

A ferramenta não tem parâmetros. O modelo decide quando chamá-la. A aplicação preenche os argumentos
a partir do estado, incluindo o CEP original. O retorno ao modelo traz planos e motivos, sem CEP nem CPF.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

NOME_FERRAMENTA = "consultar_cotacao"


@tool(NOME_FERRAMENTA)
def consultar_cotacao() -> str:
    """Cota os três planos de seguro com os dados já coletados. Não recebe argumentos.

    A execução real é feita pelo grafo, que preenche os argumentos a partir do estado.
    """
    return ""


def retorno_para_modelo(resultado: dict[str, Any]) -> str:
    """Serializa o resultado da cotação sem CEP e sem CPF. Não inclui valores além dos planos."""
    if resultado["tipo"] == "sucesso":
        planos = [
            {
                "plano_id": p["plano_id"],
                "plano_nome": p["plano_nome"],
                "premio_mensal": str(p["premio_mensal"]),
                "franquia": str(p["franquia"]),
                "coberturas": p["coberturas"],
                "carencia_dias": p["carencia_dias"],
                "primeiro_pagamento_pro_rata": (
                    str(p["primeiro_pagamento_pro_rata"]) if p.get("primeiro_pagamento_pro_rata") is not None else None
                ),
            }
            for p in resultado["planos"]
        ]
        return json.dumps({"resultado": "sucesso", "planos": planos}, ensure_ascii=False)
    if resultado["tipo"] == "recusada":
        return json.dumps({"resultado": "recusada", "motivo": resultado["motivo"]}, ensure_ascii=False)
    return json.dumps({"resultado": "indisponivel"}, ensure_ascii=False)
