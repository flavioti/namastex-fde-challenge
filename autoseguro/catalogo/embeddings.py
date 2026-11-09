"""Embedder do modelo multilingual-e5-small (ADR-0003; FDD-0008, seção 9).

O modelo é carregado uma vez por execução da carga. Na primeira execução é baixado para PASTA_MODELOS.
Os vetores são normalizados, para que a distância cosseno equivalha ao produto interno.
"""

from __future__ import annotations

from typing import Protocol

from autoseguro.catalogo.config import MODELO_ID, PASTA_MODELOS, PREFIXO_DOCUMENTO


class ErroModelo(RuntimeError):
    """O modelo de embeddings não carregou. A mensagem orienta o avaliador (RFC-0004, seção 3.7)."""


class Embedder(Protocol):
    def gerar(self, textos: list[str]) -> list[list[float]]:
        """Recebe textos já prefixados e devolve um vetor normalizado por texto."""


class EmbedderE5:
    def __init__(self, modelo_id: str = MODELO_ID, pasta: str = str(PASTA_MODELOS)):
        self._modelo_id = modelo_id
        self._pasta = pasta
        self._modelo = None

    def _carregar(self):
        if self._modelo is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._modelo = SentenceTransformer(self._modelo_id, cache_folder=self._pasta)
            except Exception as erro:
                raise ErroModelo(
                    "Modelo de embeddings indisponível. Na primeira execução é preciso acesso à internet "
                    "para baixar o modelo. Tente novamente com internet."
                ) from erro
        return self._modelo

    def gerar(self, textos: list[str]) -> list[list[float]]:
        modelo = self._carregar()
        vetores = modelo.encode(textos, normalize_embeddings=True, convert_to_numpy=True)
        return [[float(x) for x in vetor] for vetor in vetores]


def prefixar_documentos(textos: list[str]) -> list[str]:
    return [PREFIXO_DOCUMENTO + texto for texto in textos]
