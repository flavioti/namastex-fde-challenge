"""Aplica as migrações SQL em ordem numérica (FDD-0004, seção 8).

Uso: uv run --env-file .env python -m autoseguro.banco.migrar
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

from autoseguro.banco.conexao import MENSAGEM_BANCO_INDISPONIVEL, BancoIndisponivel, detalhe_erro

PASTA_MIGRACOES = Path(__file__).parent / "migracoes"

TABELA_CONTROLE = """
CREATE TABLE IF NOT EXISTS public.migracoes_aplicadas (
    nome text PRIMARY KEY,
    aplicada_em timestamptz NOT NULL DEFAULT now()
)
"""


def listar_migracoes(pasta: Path = PASTA_MIGRACOES) -> list[Path]:
    """Arquivos NNNN_*.sql, ordenados pelo número."""
    return sorted(pasta.glob("[0-9][0-9][0-9][0-9]_*.sql"))


def aplicar_migracoes(url: str, pasta: Path = PASTA_MIGRACOES) -> list[str]:
    """Aplica as migrações pendentes. Cada arquivo roda em transação própria.

    Devolve os nomes aplicados nesta execução. Para no primeiro erro.
    """
    try:
        with psycopg.connect(url) as conexao:
            with conexao.transaction():
                conexao.execute(TABELA_CONTROLE)
            ja_aplicadas = {
                linha[0]
                for linha in conexao.execute("SELECT nome FROM public.migracoes_aplicadas").fetchall()
            }
    except psycopg.OperationalError as erro:
        raise BancoIndisponivel(f"{MENSAGEM_BANCO_INDISPONIVEL}\nDetalhe: {detalhe_erro(erro)}") from erro

    aplicadas: list[str] = []
    for arquivo in listar_migracoes(pasta):
        if arquivo.name in ja_aplicadas:
            continue
        sql = arquivo.read_text(encoding="utf-8")
        with psycopg.connect(url) as conexao:
            with conexao.transaction():
                conexao.execute(sql)
                conexao.execute(
                    "INSERT INTO public.migracoes_aplicadas (nome) VALUES (%s)",
                    (arquivo.name,),
                )
        aplicadas.append(arquivo.name)
    return aplicadas


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL não definida. Preencha o .env a partir do .env.example.", file=sys.stderr)
        return 2
    try:
        aplicadas = aplicar_migracoes(url)
    except BancoIndisponivel as erro:
        print(erro, file=sys.stderr)
        return 1
    if aplicadas:
        print("Migrações aplicadas: " + ", ".join(aplicadas))
    else:
        print("Nenhuma migração pendente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
