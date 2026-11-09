"""Configuração do LangSmith e chaves de metadado (FDD-0006, seções 3 e 5; ADR-0017)."""

from __future__ import annotations

import os

PROJETO = "autoseguro-mvp"

TAG_TESTE = "teste"
TAG_DEMONSTRACAO = "demonstracao"
TAG_AVALIACAO = "avaliacao"
TAGS_VALIDAS = (TAG_TESTE, TAG_DEMONSTRACAO, TAG_AVALIACAO)

# Dicionário único de chaves de metadado. Nenhuma etapa cria chave fora dele (ADR-0017).
CHAVES = {
    "conversa_id": "conversa_id",
    "versao_prompt": "versao_prompt",
    "modelo": "modelo",
    "etapa": "etapa",
    "tipo_execucao": "tipo_execucao",
}


def tracing_ativo() -> bool:
    """Tracing só é enviado quando LANGSMITH_TRACING vale true. Testes e a configuração padrão não enviam."""
    return os.environ.get("LANGSMITH_TRACING", "false").strip().lower() == "true"
