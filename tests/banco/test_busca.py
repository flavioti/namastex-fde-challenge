"""Busca híbrida: termo exato pelo full-text, sinônimo pelo vetor, filtro e regras inativas (FDD-0004 seção 12).

Os vetores são construídos à mão, para que o teste não dependa do modelo de embeddings.
"""

from __future__ import annotations

import uuid

from autoseguro.banco import busca
from autoseguro.banco.repositorios import regras, trechos


def _vetor(indice: int) -> list[float]:
    vetor = [0.0] * 384
    vetor[indice] = 1.0
    return vetor


def _trecho(conexao, texto: str, tipo: str, eixo: int, ativa: bool = True) -> uuid.UUID:
    regra = uuid.uuid4()
    regras.upsert_regra(conexao, regra, tipo, {}, f"h-{regra}", ativa=ativa)
    trechos.upsert_trecho(conexao, regra, texto, _vetor(eixo), "e5", f"t-{regra}")
    return regra


def test_termo_exato_e_encontrado_pelo_texto(conexao):
    pro_rata = _trecho(conexao, "Pro-rata da vigência: o primeiro pagamento é proporcional aos dias", "pro_rata", 1)
    _trecho(conexao, "Carência de roubo e furto de trinta dias", "carencia", 2)
    resultado = busca.buscar_trechos(conexao, "pro-rata", _vetor(100), k=2)
    assert resultado[0]["texto"].startswith("Pro-rata")
    assert resultado[0]["id"] == trechos.id_do_trecho(pro_rata)


def test_sinonimo_e_encontrado_pelo_vetor(conexao):
    _trecho(conexao, "Pro-rata da vigência: o primeiro pagamento é proporcional", "pro_rata", 1)
    carencia = _trecho(conexao, "Carência de roubo e furto de trinta dias", "carencia", 2)
    # A consulta "tempo de espera" não tem termos em comum com o texto, mas o vetor aponta para a carência.
    resultado = busca.buscar_trechos(conexao, "tempo de espera", _vetor(2), k=1)
    assert resultado[0]["id"] == trechos.id_do_trecho(carencia)


def test_filtro_por_tipo_nao_traz_outros_tipos(conexao):
    _trecho(conexao, "Pro-rata da vigência", "pro_rata", 1)
    carencia = _trecho(conexao, "Carência de roubo e furto", "carencia", 2)
    resultado = busca.buscar_trechos(conexao, "carência", _vetor(2), k=5, tipo="carencia")
    assert resultado and all(item["tipo"] == "carencia" for item in resultado)
    assert resultado[0]["id"] == trechos.id_do_trecho(carencia)


def test_regra_inativa_sai_da_busca(conexao):
    _trecho(conexao, "Carência de roubo e furto", "carencia", 2, ativa=False)
    resultado = busca.buscar_trechos(conexao, "carência roubo", _vetor(2), k=5)
    assert all("roubo" not in item["texto"] for item in resultado)


def test_fusao_rrf_soma_posicoes(conexao):
    # Trecho A ganha no texto e no vetor. Trecho B só aparece no vetor, em segundo lugar.
    a = _trecho(conexao, "franquia franquia do plano", "pro_rata", 5)
    b = _trecho(conexao, "cobertura do veículo", "carencia", 6)
    resultado = busca.buscar_trechos(conexao, "franquia", _vetor(5), k=2)
    assert resultado[0]["id"] == trechos.id_do_trecho(a)
    assert resultado[0]["pontuacao"] > resultado[1]["pontuacao"]
    assert {item["id"] for item in resultado} == {trechos.id_do_trecho(a), trechos.id_do_trecho(b)}
