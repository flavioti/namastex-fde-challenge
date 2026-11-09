"""Comando da carga do catálogo. Nada é carregado automaticamente ao subir a aplicação (FDD-0008, seção 1).

Uso: uv run --env-file .env python -m autoseguro.catalogo
"""

from __future__ import annotations

import os
import sys

from autoseguro.banco.conexao import BancoIndisponivel, abrir_pool
from autoseguro.catalogo.embeddings import ErroModelo, EmbedderE5
from autoseguro.catalogo.fonte import FonteInvalida
from autoseguro.catalogo.carga import sincronizar
from autoseguro.logs import configurar_logging


def main() -> int:
    configurar_logging()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL não definida. Preencha o .env a partir do .env.example.", file=sys.stderr)
        return 2
    try:
        pool = abrir_pool(url)
    except BancoIndisponivel as erro:
        print(erro, file=sys.stderr)
        return 1
    try:
        with pool.connection() as conexao:
            relatorio = sincronizar(conexao, EmbedderE5())
    except FonteInvalida as erro:
        print(f"plans.json inválido, nada foi gravado: {erro}", file=sys.stderr)
        return 1
    except ErroModelo as erro:
        print(f"nada foi gravado: {erro}", file=sys.stderr)
        return 1
    finally:
        pool.close()
    print("Carga do catálogo concluída.")
    print(relatorio.texto())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
