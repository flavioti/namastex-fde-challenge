"""Busca híbrida de trechos: full-text em português e vetor, fundidos por RRF (FDD-0004 seção 10; ADR-0005).

A busca considera apenas regras ativas. O texto da consulta e o vetor da consulta vêm de fora:
o prefixo "query: " é responsabilidade de quem gera o vetor (FDD-0008, seção 9).
"""

from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row

CONSTANTE_RRF = 60
CANDIDATOS = 20


def _filtro_tipo(tipo: str | None) -> tuple[str, tuple]:
    if tipo is None:
        return "", ()
    return " AND r.tipo = %s", (tipo,)


def buscar_trechos(
    conexao: Connection,
    texto: str,
    vetor: list[float],
    k: int = 5,
    tipo: str | None = None,
    constante: int = CONSTANTE_RRF,
    candidatos: int = CANDIDATOS,
) -> list[dict]:
    """Devolve até k trechos, ordenados pela pontuação fundida por RRF."""
    filtro, params_filtro = _filtro_tipo(tipo)
    vetor_sql = "[" + ",".join(repr(float(x)) for x in vetor) + "]"

    with conexao.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT t.id, t.texto, r.tipo, ts_rank(t.texto_busca, consulta) AS pontuacao "
            "FROM regras.trechos t "
            "JOIN regras.regras r ON r.id = t.regra_id, "
            "plainto_tsquery('portuguese', %s) AS consulta "
            "WHERE r.ativa AND t.texto_busca @@ consulta" + filtro + " "
            "ORDER BY pontuacao DESC LIMIT %s",
            (texto, *params_filtro, candidatos),
        )
        por_texto = cur.fetchall()

        cur.execute(
            "SELECT t.id, t.texto, r.tipo "
            "FROM regras.trechos t JOIN regras.regras r ON r.id = t.regra_id "
            "WHERE r.ativa" + filtro + " "
            "ORDER BY t.embedding <=> %s::vector LIMIT %s",
            (*params_filtro, vetor_sql, candidatos),
        )
        por_vetor = cur.fetchall()

    pontuacao: dict = {}
    dados: dict = {}
    for ranking in (por_texto, por_vetor):
        for posicao, linha in enumerate(ranking, start=1):
            pontuacao[linha["id"]] = pontuacao.get(linha["id"], 0.0) + 1.0 / (constante + posicao)
            dados.setdefault(linha["id"], {"id": linha["id"], "texto": linha["texto"], "tipo": linha["tipo"]})

    ordenados = sorted(pontuacao.items(), key=lambda par: par[1], reverse=True)[:k]
    return [{**dados[trecho_id], "pontuacao": valor} for trecho_id, valor in ordenados]
