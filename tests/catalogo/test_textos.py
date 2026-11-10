"""Frases fixas por tipo de regra e recusa com motivo (FDD-0008, seção 6 e seção 14)."""

from __future__ import annotations

from autoseguro.catalogo.regras import Regra, impressao_digital
import uuid

from autoseguro.catalogo.textos import impressao_do_trecho, texto_da_regra


def _regra(tipo: str, dados: dict) -> Regra:
    return Regra(chave=tipo, tipo=tipo, dados=dados, id=uuid.uuid4(), impressao_digital=impressao_digital(dados))


def test_faixa_etaria_com_virgula_decimal():
    regra = _regra("faixa_etaria", {"idade_min": 18, "idade_max": 24, "multiplicador": 1.6})
    assert texto_da_regra(regra) == "Para motorista com idade de 18 a 24 anos, o multiplicador do prêmio é 1,6."


def test_faixa_etaria_com_multiplicador_inteiro():
    regra = _regra("faixa_etaria", {"idade_min": 30, "idade_max": 59, "multiplicador": 1.0})
    assert texto_da_regra(regra) == "Para motorista com idade de 30 a 59 anos, o multiplicador do prêmio é 1."


def test_recusa_de_idade_usa_motivo_do_plans():
    regra = _regra("faixa_etaria", {
        "idade_min": 76, "idade_max": 200, "recusar": True,
        "motivo": "Idade acima do limite de aceitação (75 anos).",
    })
    assert texto_da_regra(regra) == (
        "Não é possível cotar para idade de 76 a 200 anos. Idade acima do limite de aceitação (75 anos)."
    )


def test_idade_do_veiculo_e_recusa():
    regra = _regra("idade_veiculo", {"anos_min": 6, "anos_max": 10, "multiplicador": 1.15})
    assert texto_da_regra(regra) == "Para veículo com 6 a 10 anos, o multiplicador do prêmio é 1,15."
    recusa = _regra("idade_veiculo", {"anos_min": 21, "anos_max": 200, "recusar": True, "motivo": "Não aceito."})
    assert texto_da_regra(recusa) == "Não é possível cotar veículo com 21 a 200 anos. Não aceito."


def test_regiao_de_risco_lista_prefixos():
    regra = _regra("regiao_cep", {"prefixos_alto_risco": ["07", "08"], "multiplicador": 1.3})
    assert texto_da_regra(regra) == (
        "CEPs com os prefixos 07, 08 são de alto risco, com multiplicador 1,3."
    )


def test_carencia_lista_coberturas():
    regra = _regra("carencia", {"coberturas_com_carencia": ["roubo", "furto"], "dias": 30})
    assert texto_da_regra(regra) == (
        "As coberturas roubo, furto têm carência de 30 dias, contados da data de início da vigência."
    )


def test_pro_rata_texto_fixo():
    regra = _regra("pro_rata", {"regra": "pro_rata_primeiro_mes"})
    assert texto_da_regra(regra).startswith("Quando a vigência começa no meio do mês")


def test_impressao_do_trecho_muda_com_texto_ou_modelo():
    base = impressao_do_trecho("texto", "modelo-a")
    assert impressao_do_trecho("texto", "modelo-a") == base
    assert impressao_do_trecho("outro", "modelo-a") != base
    assert impressao_do_trecho("texto", "modelo-b") != base
