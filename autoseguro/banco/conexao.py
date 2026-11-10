"""Pool de conexões compartilhado pela aplicação (FDD-0004, seção 9)."""

from __future__ import annotations

from psycopg import Connection
from psycopg_pool import ConnectionPool


class BancoIndisponivel(RuntimeError):
    """O banco não respondeu. A mensagem orienta o avaliador (RFC-0012, seção 7)."""


MENSAGEM_BANCO_INDISPONIVEL = (
    "Banco indisponível. Confirme que o serviço 'banco' está no ar com "
    "'docker compose up -d banco' e que DATABASE_URL aponta para ele."
)


def detalhe_erro(erro: Exception) -> str:
    """Primeira linha do erro do servidor, com dica para falha de senha. Não inclui a URL nem a senha."""
    linha = str(erro).splitlines()[0] if str(erro) else type(erro).__name__
    if "password authentication failed" in linha:
        linha += (" | A senha de DATABASE_URL não é a do volume do banco. Ela foi fixada na primeira"
                  " inicialização. Use a mesma senha em POSTGRES_PASSWORD e DATABASE_URL, ou recrie o volume.")
    return linha


def _configurar(conexao: Connection) -> None:
    """Registra o tipo vector nas conexões, quando a extensão já existe."""
    from pgvector.psycopg import register_vector

    # A transação é encerrada aqui. O pool descarta conexões deixadas em transação aberta.
    with conexao.transaction():
        existe = conexao.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        if existe:
            register_vector(conexao)


def abrir_pool(url: str, minimo: int = 1, maximo: int = 5, timeout: float = 10.0) -> ConnectionPool:
    """Abre o pool e confirma que o banco responde. Falha com mensagem clara."""
    pool = ConnectionPool(
        conninfo=url,
        min_size=minimo,
        max_size=maximo,
        configure=_configurar,
        open=False,
    )
    try:
        pool.open(wait=True, timeout=timeout)
    except Exception as erro:  # psycopg_pool.PoolTimeout e erros de conexão
        pool.close()
        raise BancoIndisponivel(f"{MENSAGEM_BANCO_INDISPONIVEL}\nDetalhe: {detalhe_erro(erro)}") from erro
    return pool
