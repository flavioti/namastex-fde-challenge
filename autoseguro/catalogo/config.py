"""Constantes da carga do catálogo (FDD-0008, seções 2 e 3; ADR-0003; RFC-0012)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]

# Fonte oficial das regras, lida pela carga (FDD-0008, seção 4).
ARQUIVO_PLANS = RAIZ_PROJETO / "quote-service" / "data" / "plans.json"

# Modelo de embeddings (ADR-0003). Trocar o modelo recalcula todo o índice (ADR-0014).
MODELO_ID = "intfloat/multilingual-e5-small"
DIMENSAO_ESPERADA = 384
PREFIXO_DOCUMENTO = "passage: "

# Cache do modelo dentro do volume persistente database/ (RFC-0004, seção 3.6).
# AUTOSEGURO_MODELOS sobrescreve o caminho quando database/ não é gravável pelo usuário (ver docs/tasks.md, T-08).
PASTA_MODELOS = Path(os.environ.get("AUTOSEGURO_MODELOS", RAIZ_PROJETO / "database" / "modelos"))

# Versão dos modelos de frase. Mudar uma frase exige recalcular os trechos desse tipo (FDD-0008, seção 6).
VERSAO_TEXTOS = "2"

# Namespace fixo do projeto para UUID v5 das regras (FDD-0008, seção 5; ADR-0009).
NAMESPACE_REGRAS = uuid.uuid5(uuid.NAMESPACE_URL, "autoseguro.catalogo.regras")
