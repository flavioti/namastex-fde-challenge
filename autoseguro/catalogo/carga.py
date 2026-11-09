"""Carga do catálogo: sincroniza planos, regras e trechos com plans.json (FDD-0008, seção 8).

Toda a carga roda em uma única transação. Qualquer falha reverte tudo.
Só os trechos com impressão digital diferente são embedados de novo (ADR-0014 vale automaticamente:
o identificador do modelo faz parte da impressão digital do trecho).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from psycopg import Connection

from autoseguro.banco.repositorios import regras as repo_regras
from autoseguro.banco.repositorios import trechos as repo_trechos
from autoseguro.catalogo import fonte
from autoseguro.catalogo.config import ARQUIVO_PLANS, DIMENSAO_ESPERADA, MODELO_ID
from autoseguro.catalogo.embeddings import Embedder, prefixar_documentos
from autoseguro.catalogo.regras import Regra, extrair
from autoseguro.catalogo.textos import impressao_do_trecho, texto_da_regra
from autoseguro.logs import obter_logger

_log = obter_logger("autoseguro.catalogo")


@dataclass
class Relatorio:
    planos_gravados: int = 0
    regras_criadas: int = 0
    regras_atualizadas: int = 0
    regras_inalteradas: int = 0
    regras_desativadas: int = 0
    trechos_reembedados: int = 0
    trechos_inalterados: int = 0

    def texto(self) -> str:
        return (
            f"planos gravados: {self.planos_gravados}\n"
            f"regras criadas: {self.regras_criadas}, atualizadas: {self.regras_atualizadas}, "
            f"inalteradas: {self.regras_inalteradas}, desativadas: {self.regras_desativadas}\n"
            f"trechos reembedados: {self.trechos_reembedados}, inalterados: {self.trechos_inalterados}"
        )


def _normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(x * x for x in vetor))
    if norma == 0:
        raise ValueError("vetor nulo não pode ser normalizado")
    return [x / norma for x in vetor]


def _gravar_regra(conexao: Connection, regra: Regra, relatorio: Relatorio) -> None:
    """Cria ou atualiza a regra, e a reativa se ela voltou ao plans.json."""
    atual = repo_regras.obter_regra(conexao, regra.id)
    if atual is None:
        repo_regras.upsert_regra(conexao, regra.id, regra.tipo, regra.dados, regra.impressao_digital)
        relatorio.regras_criadas += 1
    elif atual["impressao_digital"] == regra.impressao_digital and atual["ativa"]:
        relatorio.regras_inalteradas += 1
    else:
        repo_regras.upsert_regra(conexao, regra.id, regra.tipo, regra.dados, regra.impressao_digital, ativa=True)
        relatorio.regras_atualizadas += 1


def sincronizar(
    conexao: Connection,
    embedder: Embedder,
    caminho: Path = ARQUIVO_PLANS,
    modelo_id: str = MODELO_ID,
) -> Relatorio:
    """Executa a carga completa. Lança FonteInvalida, ErroModelo ou erro de banco; nada é gravado nesses casos."""
    catalogo = fonte.carregar(caminho)  # valida antes de qualquer gravação
    relatorio = Relatorio()
    regras_do_arquivo = extrair(catalogo)

    with conexao.transaction():
        for plano in catalogo.planos:
            repo_regras.upsert_plano(
                conexao, plano.id, plano.nome, plano.base_mensal, plano.franquia, plano.coberturas
            )
            relatorio.planos_gravados += 1

        for regra in regras_do_arquivo:
            _gravar_regra(conexao, regra, relatorio)
        relatorio.regras_desativadas = repo_regras.desativar_regras_ausentes(
            conexao, [r.id for r in regras_do_arquivo]
        )

        # Um trecho só é embedado de novo se o seu texto, o modelo ou a versão das frases mudaram.
        pendentes: list[tuple[Regra, str, str]] = []
        for regra in regras_do_arquivo:
            texto = texto_da_regra(regra)
            impressao = impressao_do_trecho(texto, modelo_id)
            if repo_trechos.obter_impressao_trecho(conexao, regra.id) == impressao:
                relatorio.trechos_inalterados += 1
            else:
                pendentes.append((regra, texto, impressao))

        if pendentes:
            vetores = embedder.gerar(prefixar_documentos([texto for _, texto, _ in pendentes]))
            if len(vetores) != len(pendentes):
                raise RuntimeError("o embedder devolveu um número de vetores diferente do esperado")
            for (regra, texto, impressao), vetor in zip(pendentes, vetores):
                if len(vetor) != DIMENSAO_ESPERADA:
                    raise RuntimeError(
                        f"dimensão {len(vetor)} do vetor da regra {regra.chave}, esperado {DIMENSAO_ESPERADA}"
                    )
                repo_trechos.upsert_trecho(
                    conexao, regra.id, texto, _normalizar(vetor), modelo_id, impressao
                )
                relatorio.trechos_reembedados += 1

    _log.info(
        "carga do catálogo concluída",
        extra={
            "evento": "carga_catalogo",
            "detalhe": {
                "planos": relatorio.planos_gravados,
                "regras_criadas": relatorio.regras_criadas,
                "regras_atualizadas": relatorio.regras_atualizadas,
                "regras_inalteradas": relatorio.regras_inalteradas,
                "regras_desativadas": relatorio.regras_desativadas,
                "trechos_reembedados": relatorio.trechos_reembedados,
                "trechos_inalterados": relatorio.trechos_inalterados,
            },
        },
    )
    return relatorio
