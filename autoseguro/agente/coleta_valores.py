"""Extração determinística de cada campo da mensagem do lead, sem o modelo (FDD-0005, seção 7; FDD-0001, seção 3).

Texto livre não é interpretado: uma resposta que não contém o dado no formato esperado conta como inválida.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")
IDADE_MINIMA, IDADE_MAXIMA = 1, 120
ANO_MINIMO = 1950

_IDADE = re.compile(r"\s*(\d{1,3})\s*(?:anos?)?\s*\.?\s*")
_ANO = re.compile(r"\s*(\d{4})\s*\.?\s*")
_CEP = re.compile(r"\s*(\d{5})-?(\d{3})\s*\.?\s*")
_DATA = re.compile(r"\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*\.?\s*")
_CPF = re.compile(r"\s*(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\s*\.?\s*")
_NEGATIVA = re.compile(r"\b(não|nao|recuso|negativo|nunca)\b", re.IGNORECASE)
_AFIRMATIVA = re.compile(r"\b(sim|autorizo|concordo|pode|ok|claro|autorizado)\b", re.IGNORECASE)
PLANOS = ("essencial", "completo", "premium")


def extrair_idade(texto: str) -> int | None:
    casamento = _IDADE.fullmatch(texto)
    if not casamento:
        return None
    idade = int(casamento.group(1))
    return idade if IDADE_MINIMA <= idade <= IDADE_MAXIMA else None


def extrair_ano_veiculo(texto: str, hoje: date | None = None) -> int | None:
    casamento = _ANO.fullmatch(texto)
    if not casamento:
        return None
    ano = int(casamento.group(1))
    ano_atual = (hoje or datetime.now(FUSO_BRASILIA).date()).year
    return ano if ANO_MINIMO <= ano <= ano_atual else None


def extrair_cep(texto: str) -> str | None:
    casamento = _CEP.fullmatch(texto)
    if not casamento:
        return None
    return f"{casamento.group(1)}-{casamento.group(2)}"


def extrair_data_inicio(texto: str, hoje: date | None = None) -> date | None:
    """Dia/mês/ano, sem data anterior a hoje (no fuso de Brasília)."""
    casamento = _DATA.fullmatch(texto)
    if not casamento:
        return None
    dia, mes, ano = (int(g) for g in casamento.groups())
    try:
        data = date(ano, mes, dia)
    except ValueError:
        return None
    referencia = hoje or datetime.now(FUSO_BRASILIA).date()
    return data if data >= referencia else None


def extrair_cpf(texto: str) -> str | None:
    casamento = _CPF.fullmatch(texto)
    if not casamento:
        return None
    return "".join(casamento.groups())


_INICIO_DE_PERGUNTA = re.compile(
    r"^\s*(para que|pra que|o que|oq|como|quem|qual|quais|quando|onde|por que|porque|quanto|quanto custa)\b",
    re.IGNORECASE,
)
_SAUDACAO = re.compile(
    r"^\s*(oi|olá|ola|bom dia|boa tarde|boa noite|tudo bem|e aí|e ai|obrigad[oa])\b",
    re.IGNORECASE,
)


def eh_outro_contexto(texto: str) -> bool:
    """Pergunta, saudação ou agradecimento. Não é resposta ao dado pedido, e não conta como tentativa."""
    if "?" in texto:
        return True
    return bool(_INICIO_DE_PERGUNTA.search(texto) or _SAUDACAO.search(texto))


_ROTULO_IDADE = re.compile(r"\bidade\b\D{0,15}?(\d{1,3})\b|\b(\d{1,3})\s*anos\b", re.IGNORECASE)
_ROTULO_ANO = re.compile(r"\b(?:ano|fabrica[cç][aã]o)\b\D{0,20}?(\d{4})\b", re.IGNORECASE)
_CEP_QUALQUER = re.compile(r"\b\d{5}-?\d{3}\b")
_CPF_QUALQUER = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def extrair_campos_rotulados(texto: str, hoje: date | None = None) -> dict[str, object]:
    """Dados válidos numa mensagem que tem rótulo ou formato claro: idade com 'idade' ou 'anos', ano com
    'ano' ou 'fabricação', CEP e CPF pelo formato. Dados sem rótulo, como 'tenho uns 35', não são extraídos."""
    campos: dict[str, object] = {}
    casamento = _ROTULO_IDADE.search(texto)
    if casamento:
        idade = extrair_idade(casamento.group(1) or casamento.group(2))
        if idade is not None:
            campos["idade"] = idade
    casamento = _ROTULO_ANO.search(texto)
    if casamento:
        ano = extrair_ano_veiculo(casamento.group(1), hoje)
        if ano is not None:
            campos["ano_veiculo"] = ano
    casamento = _CEP_QUALQUER.search(texto)
    if casamento and extrair_cep(casamento.group(0)):
        campos["cep"] = extrair_cep(casamento.group(0))
    casamento = _CPF_QUALQUER.search(texto)
    if casamento and extrair_cpf(casamento.group(0)):
        campos["cpf"] = extrair_cpf(casamento.group(0))
    return campos


def extrair_plano(texto: str) -> str | None:
    encontrados = [p for p in PLANOS if re.search(rf"\b{p}\b", texto, re.IGNORECASE)]
    return encontrados[0] if len(encontrados) == 1 else None


def extrair_consentimento(texto: str) -> bool | None:
    """Recusa tem prioridade, porque "não autorizo" contém a palavra "autorizo"."""
    if _NEGATIVA.search(texto):
        return False
    if _AFIRMATIVA.search(texto):
        return True
    return None
