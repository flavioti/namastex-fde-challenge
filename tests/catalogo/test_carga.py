"""Carga do catálogo com embedder substituto, sem carregar o modelo real (FDD-0008, seções 12 e 13)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autoseguro.catalogo import fonte
from autoseguro.catalogo.carga import sincronizar
from autoseguro.catalogo.config import ARQUIVO_PLANS, DIMENSAO_ESPERADA


class EmbedderFalso:
    """Devolve vetores determinísticos de 384 posições e registra as chamadas."""

    def __init__(self, dimensao: int = DIMENSAO_ESPERADA, falhar: bool = False):
        self.chamadas: list[list[str]] = []
        self.dimensao = dimensao
        self.falhar = falhar

    def gerar(self, textos: list[str]) -> list[list[float]]:
        self.chamadas.append(list(textos))
        if self.falhar:
            raise RuntimeError("falha simulada do modelo")
        vetores = []
        for texto in textos:
            vetor = [0.0] * self.dimensao
            vetor[len(texto) % self.dimensao] = 1.0
            vetores.append(vetor)
        return vetores

    @property
    def textos_embedados(self) -> int:
        return sum(len(c) for c in self.chamadas)


def _plans_modificado(tmp_path: Path, alterar) -> Path:
    dados = json.loads(ARQUIVO_PLANS.read_text(encoding="utf-8"))
    alterar(dados)
    caminho = tmp_path / "plans.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return caminho


def _contar(conexao, sql: str) -> int:
    return conexao.execute(sql).fetchone()[0]


def test_carga_inicial_cria_planos_regras_e_trechos(conexao):
    embedder = EmbedderFalso()
    relatorio = sincronizar(conexao, embedder, ARQUIVO_PLANS)
    assert relatorio.planos_gravados == 3
    assert relatorio.regras_criadas == 12
    assert relatorio.trechos_reembedados == 12
    assert _contar(conexao, "SELECT count(*) FROM regras.trechos") == 12
    assert _contar(conexao, "SELECT count(*) FROM regras.planos") == 3


def test_textos_de_passagem_recebem_prefixo_de_documento(conexao):
    embedder = EmbedderFalso()
    sincronizar(conexao, embedder, ARQUIVO_PLANS)
    assert len(embedder.chamadas) == 1, "o embedder é chamado uma vez, em lote"
    assert all(texto.startswith("passage: ") for texto in embedder.chamadas[0])


def test_reexecucao_sem_mudanca_nao_chama_o_embedder(conexao):
    sincronizar(conexao, EmbedderFalso(), ARQUIVO_PLANS)
    embedder = EmbedderFalso()
    relatorio = sincronizar(conexao, embedder, ARQUIVO_PLANS)
    assert embedder.chamadas == []
    assert relatorio.trechos_reembedados == 0
    assert relatorio.regras_inalteradas == 12
    assert relatorio.trechos_inalterados == 12


def test_alterar_um_valor_recalcula_so_o_trecho_desse_valor(conexao, tmp_path):
    sincronizar(conexao, EmbedderFalso(), ARQUIVO_PLANS)

    def alterar(dados):
        dados["regras"]["faixa_etaria"][0]["multiplicador"] = 1.7

    embedder = EmbedderFalso()
    relatorio = sincronizar(conexao, embedder, _plans_modificado(tmp_path, alterar))
    assert relatorio.trechos_reembedados == 1
    assert embedder.textos_embedados == 1
    assert relatorio.regras_atualizadas == 1


def test_regra_removida_do_arquivo_fica_inativa_sem_ser_apagada(conexao, tmp_path):
    sincronizar(conexao, EmbedderFalso(), ARQUIVO_PLANS)

    def alterar(dados):
        dados["regras"]["faixa_etaria"] = dados["regras"]["faixa_etaria"][1:]

    relatorio = sincronizar(conexao, EmbedderFalso(), _plans_modificado(tmp_path, alterar))
    assert relatorio.regras_desativadas == 1
    assert _contar(conexao, "SELECT count(*) FROM regras.regras WHERE NOT ativa") == 1
    assert _contar(conexao, "SELECT count(*) FROM regras.regras") == 12
    assert _contar(conexao, "SELECT count(*) FROM regras.trechos") == 12


def test_identificadores_de_regra_sao_estaveis_entre_cargas(conexao):
    sincronizar(conexao, EmbedderFalso(), ARQUIVO_PLANS)
    primeiros = set(conexao.execute("SELECT id FROM regras.regras").fetchall())
    sincronizar(conexao, EmbedderFalso(), ARQUIVO_PLANS)
    segundos = set(conexao.execute("SELECT id FROM regras.regras").fetchall())
    assert primeiros == segundos


def test_falha_do_embedder_nao_grava_nada(conexao):
    with pytest.raises(RuntimeError):
        sincronizar(conexao, EmbedderFalso(falhar=True), ARQUIVO_PLANS)
    assert _contar(conexao, "SELECT count(*) FROM regras.regras") == 0
    assert _contar(conexao, "SELECT count(*) FROM regras.trechos") == 0
    assert _contar(conexao, "SELECT count(*) FROM regras.planos") == 0


def test_dimensao_errada_reverte_a_carga(conexao):
    with pytest.raises(RuntimeError):
        sincronizar(conexao, EmbedderFalso(dimensao=3), ARQUIVO_PLANS)
    assert _contar(conexao, "SELECT count(*) FROM regras.trechos") == 0
    assert _contar(conexao, "SELECT count(*) FROM regras.regras") == 0


def test_plans_invalido_nao_grava_nada(conexao, tmp_path):
    def alterar(dados):
        del dados["planos"][0]["base_mensal"]

    with pytest.raises(fonte.FonteInvalida):
        sincronizar(conexao, EmbedderFalso(), _plans_modificado(tmp_path, alterar))
    assert _contar(conexao, "SELECT count(*) FROM regras.planos") == 0


def test_catalogo_completo_tem_doze_regras_nos_tipos_esperados():
    catalogo = fonte.carregar(ARQUIVO_PLANS)
    from autoseguro.catalogo.regras import extrair

    regras = extrair(catalogo)
    assert len(regras) == 12
    assert sorted({r.tipo for r in regras}) == ["carencia", "faixa_etaria", "idade_veiculo", "pro_rata", "regiao_cep"]
    assert len({r.id for r in regras}) == 12
