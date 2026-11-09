"""Detecção e substituição de dados pessoais (FDD-0003 seções 5 a 7).

Cada padrão é aplicado ao texto original. Um trecho já coberto por um padrão anterior não é casado de novo,
o que mantém a precedência da ordem fixa e impede que um marcador seja mascarado.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field

from autoseguro.logs import obter_logger
from autoseguro.mascaramento.padroes import MARCADOR_SAIDA, PADROES

_log = obter_logger("autoseguro.mascaramento")


@dataclass(frozen=True)
class Achado:
    tipo: str
    valor: str
    inicio: int
    fim: int


@dataclass(frozen=True)
class ResultadoMascara:
    texto: str
    achados: list[Achado] = field(default_factory=list)

    @property
    def contagem(self) -> dict[str, int]:
        return dict(Counter(achado.tipo for achado in self.achados))


def detectar(texto: str) -> list[Achado]:
    """Lista os dados pessoais do texto original, sem alterá-lo, em ordem de posição."""
    if not texto:
        return []
    cobertos: list[tuple[int, int]] = []
    achados: list[Achado] = []
    for padrao in PADROES:
        for casamento in padrao.regex.finditer(texto):
            inicio, fim = casamento.span()
            if any(inicio < c_fim and fim > c_inicio for c_inicio, c_fim in cobertos):
                continue
            cobertos.append((inicio, fim))
            achados.append(Achado(padrao.tipo, casamento.group(0), inicio, fim))
    return sorted(achados, key=lambda achado: achado.inicio)


def _substituir(texto: str, achados: list[Achado], marcador_de: dict[str, str] | str) -> str:
    partes: list[str] = []
    posicao = 0
    for achado in achados:
        partes.append(texto[posicao:achado.inicio])
        marcador = marcador_de if isinstance(marcador_de, str) else marcador_de[achado.tipo]
        partes.append(marcador)
        posicao = achado.fim
    partes.append(texto[posicao:])
    return "".join(partes)


def _registrar(ponto: str, conversa_id: uuid.UUID | None, contagem: dict[str, int]) -> None:
    _log.info(
        "mascaramento aplicado",
        extra={"evento": "mascaramento", "ponto": ponto, "conversa_id": str(conversa_id) if conversa_id else None,
               "contagem": contagem},
    )


def mascarar_entrada(texto: str, conversa_id: uuid.UUID | None = None) -> ResultadoMascara:
    """Substitui cada dado pessoal pelo marcador do seu tipo, como [CPF]. Usada antes do modelo."""
    achados = detectar(texto)
    marcadores = {padrao.tipo: padrao.marcador for padrao in PADROES}
    resultado = ResultadoMascara(_substituir(texto, achados, marcadores) if achados else texto, achados)
    _registrar("entrada", conversa_id, resultado.contagem)
    return resultado


def mascarar_saida(texto: str, conversa_id: uuid.UUID | None = None) -> ResultadoMascara:
    """Substitui cada dado pessoal por [dado omitido]. Usada na resposta do agente antes do envio."""
    achados = detectar(texto)
    resultado = ResultadoMascara(_substituir(texto, achados, MARCADOR_SAIDA) if achados else texto, achados)
    _registrar("saida", conversa_id, resultado.contagem)
    return resultado
