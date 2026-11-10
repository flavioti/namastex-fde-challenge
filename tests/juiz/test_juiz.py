"""Extração de valores, R1 em código e orquestração do juiz com modelo substituto (FDD-0009, seção 12)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from autoseguro.juiz import Juiz, VeredictoJuiz, prompts
from autoseguro.juiz.extracao import extrair_valores
from autoseguro.juiz.r1 import verificar

PLANOS = [
    {"plano_nome": "Essencial", "premio_mensal": "119.90", "franquia": "4500.00", "primeiro_pagamento_pro_rata": "65.70"},
    {"plano_nome": "Premium", "premio_mensal": "4500.00", "franquia": "900.00", "primeiro_pagamento_pro_rata": None},
]


class ModeloFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = 0

    def estruturar(self, sistema, conteudo, schema):
        self.chamadas += 1
        resposta = self.respostas.pop(0) if self.respostas else RuntimeError("sem resposta")
        if isinstance(resposta, Exception):
            raise resposta
        return resposta, 120


# ----- extração ---------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("custa R$ 119,90 por mês", ["119.90"]),
    ("o plano Premium é R$ 4.500,00", ["4500.00"]),
    ("valor 119.90 por mês", ["119.90"]),
    ("sem valor no texto", []),
])
def test_extracao_de_valores(texto, esperado):
    assert [str(v) for v, _ in extrair_valores(texto)] == esperado


@pytest.mark.parametrize("texto", ["tenho 2 anos", "carência de 30 dias", "idade 35", "ano 2022"])
def test_inteiro_sem_rs_e_ignorado(texto):
    assert extrair_valores(texto) == []


# ----- R1 em código -----------------------------------------------------------

def test_valor_da_cotacao_aprovado():
    assert verificar("O Essencial custa R$ 119,90 por mês.", PLANOS).aprovado


def test_valor_fora_da_cotacao_reprovado():
    resultado = verificar("O Essencial custa R$ 150,00 por mês.", PLANOS)
    assert not resultado.aprovado


def test_valor_no_plano_errado_reprovado():
    # 900,00 é a franquia do Premium. Na frase sobre o Essencial, o valor não é permitido.
    assert not verificar("O Essencial custa R$ 900,00 por mês.", PLANOS).aprovado


def test_valor_de_outro_plano_permitido_em_frase_sem_plano():
    # Sem plano citado na frase, o valor vale se existir em qualquer plano da cotação.
    assert verificar("A franquia de R$ 900,00 é uma das opções.", PLANOS).aprovado


def test_valor_sem_cotacao_reprovado():
    assert not verificar("Custa R$ 119,90.", None).aprovado


def test_rascunho_sem_valor_aprovado_em_r1():
    assert verificar("Qual é a sua idade?", None).aprovado


# ----- juiz com modelo substituto ---------------------------------------------

def test_rascunho_com_valor_fora_da_cotacao_nao_chama_o_modelo():
    modelo = ModeloFalso([])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("Custa R$ 999,00.", PLANOS, "cotada", None)
    assert decisao.regra == "R1" and not decisao.aprovado
    assert modelo.chamadas == 0


def test_consumo_do_modelo_do_juiz_vai_para_a_decisao():
    modelo = ModeloFalso([VeredictoJuiz(aprovado=True)])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("O Essencial custa R$ 119,90.", PLANOS, "cotada", None)
    assert decisao.tokens == 120


def test_modelo_aprova():
    modelo = ModeloFalso([VeredictoJuiz(aprovado=True)])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("O Essencial custa R$ 119,90.", PLANOS, "cotada", None)
    assert decisao.aprovado and decisao.regra is None and modelo.chamadas == 1


def test_modelo_reprova_em_r2():
    modelo = ModeloFalso([VeredictoJuiz(aprovado=False, regra="R2", motivo="Recusa sem motivo da cotação.")])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("Não é possível cotar.", None, "em_andamento", None)
    assert not decisao.aprovado and decisao.regra == "R2"
    assert decisao.motivo == "Recusa sem motivo da cotação."


def test_falha_do_modelo_tres_vezes_reprova_com_motivo_de_falha():
    esperas = []
    modelo = ModeloFalso([ValueError("fora do formato"), ValueError("de novo"), ValueError("outra vez")])
    decisao = Juiz(modelo, sleep=esperas.append).avaliar("Qual é a sua idade?", None, "em_andamento", None)
    assert not decisao.aprovado
    assert decisao.motivo == "falha do juiz"
    assert modelo.chamadas == 3
    assert esperas == [0.5, 1.0]


def test_saida_invalida_seguida_de_aprovacao_recupera():
    modelo = ModeloFalso([ValueError("formato"), VeredictoJuiz(aprovado=True)])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("Mensagem sem valor.", None, "em_andamento", None)
    assert decisao.aprovado and modelo.chamadas == 2


def test_motivo_com_valor_e_omitido():
    modelo = ModeloFalso([VeredictoJuiz(aprovado=False, regra="R2", motivo="Errado, veja R$ 999,00")])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("Não é possível cotar.", None, "em_andamento", None)
    assert decisao.motivo == "motivo omitido"


def test_motivo_com_dado_pessoal_e_omitido():
    modelo = ModeloFalso([VeredictoJuiz(aprovado=False, regra="R4", motivo="Mostra CPF 123.456.789-09")])
    decisao = Juiz(modelo, sleep=lambda s: None).avaliar("Não é possível cotar.", None, "em_andamento", None)
    assert decisao.motivo == "motivo omitido"


def test_gatilho_do_juiz():
    assert prompts.acionado("O plano custa R$ 119,90.")
    assert prompts.acionado("Não é possível cotar para essa idade.")
    assert not prompts.acionado("Qual é a sua idade?")


def test_valor_com_uma_casa_decimal_convertido_para_duas():
    assert extrair_valores("R$ 119,9")[0][0] == Decimal("119.90")
