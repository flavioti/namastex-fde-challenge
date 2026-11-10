"""Frases fixas de cada tipo de regra (FDD-0008, seção 6). O texto é preenchido com os valores da regra,
nunca escrito à mão. A frase de recusa é própria e recebe o motivo do plans.json como complemento."""

from __future__ import annotations

import hashlib

from autoseguro.catalogo.config import MODELO_ID, VERSAO_TEXTOS
from autoseguro.catalogo.regras import Regra


def _numero(valor: float | int) -> str:
    """Número no formato brasileiro, sem zeros desnecessários: 1.6 vira 1,6 e 1.0 vira 1."""
    texto = f"{float(valor):g}"
    return texto.replace(".", ",")


def texto_da_regra(regra: Regra) -> str:
    d = regra.dados
    if regra.tipo == "faixa_etaria":
        if d.get("recusar"):
            return (
                f"Não é possível cotar para idade de {d['idade_min']} a {d['idade_max']} anos. "
                f"{d.get('motivo', '')}".rstrip()
            )
        return (
            f"Para motorista com idade de {d['idade_min']} a {d['idade_max']} anos, "
            f"o multiplicador do prêmio é {_numero(d['multiplicador'])}."
        )
    if regra.tipo == "idade_veiculo":
        if d.get("recusar"):
            return (
                f"Não é possível cotar veículo com {d['anos_min']} a {d['anos_max']} anos. "
                f"{d.get('motivo', '')}".rstrip()
            )
        return (
            f"Para veículo com {d['anos_min']} a {d['anos_max']} anos, "
            f"o multiplicador do prêmio é {_numero(d['multiplicador'])}."
        )
    if regra.tipo == "regiao_cep":
        prefixos = ", ".join(d["prefixos_alto_risco"])
        return (
            f"CEPs com os prefixos {prefixos} são de alto risco, "
            f"com multiplicador {_numero(d['multiplicador'])}."
        )
    if regra.tipo == "carencia":
        coberturas = ", ".join(d["coberturas_com_carencia"])
        return (
            f"As coberturas {coberturas} têm carência de {d['dias']} dias, "
            f"contados da data de início da vigência."
        )
    if regra.tipo == "pro_rata":
        return (
            "Quando a vigência começa no meio do mês, o primeiro pagamento é proporcional "
            "aos dias restantes do mês. Os meses seguintes são integrais."
        )
    raise ValueError(f"tipo de regra sem frase: {regra.tipo!r}")


def impressao_do_trecho(texto: str, modelo_id: str = MODELO_ID) -> str:
    """SHA-256 de texto, modelo e versão das frases. Mudar qualquer um força o recálculo (FDD-0008, seção 7)."""
    return hashlib.sha256(f"{texto}|{modelo_id}|{VERSAO_TEXTOS}".encode("utf-8")).hexdigest()
