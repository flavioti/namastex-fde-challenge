"""Estado do grafo do agente (FDD-0005, seção 4; ADR-0006)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

StatusConversa = Literal["em_andamento", "cotada", "encaminhada", "encerrada"]
PAPEIS = ("lead", "agente")
STATUS_TERMINAIS = ("encaminhada", "encerrada")


class Mensagem(BaseModel):
    papel: Literal["lead", "agente"]
    texto: str  # sempre o texto mascarado


class DadosColeta(BaseModel):
    idade: Optional[int] = None
    ano_veiculo: Optional[int] = None
    cep: Optional[str] = None  # valor original, nunca enviado ao modelo
    data_inicio: Optional[date] = None
    plano_escolhido: Optional[str] = None
    consentimento_cpf: Optional[bool] = None
    cpf: Optional[str] = None  # valor original, nunca enviado ao modelo


class EstadoConversa(BaseModel):
    conversa_id: UUID
    mensagens: list[Mensagem] = Field(default_factory=list)
    resumo: Optional[str] = None
    dados: DadosColeta = Field(default_factory=DadosColeta)
    tentativas: dict[str, int] = Field(default_factory=dict)
    cotacao: Optional[dict] = None  # ResultadoCotacao serializado, sem CEP nem CPF
    rascunho: Optional[str] = None
    reescritas: int = 0
    status: StatusConversa = "em_andamento"
    motivo_encaminhamento: Optional[str] = None
    tokens_consumidos: int = 0
    # Campos de passagem entre nós, limpos ao fim de cada turno.
    texto_original: Optional[str] = None
    proxima: Optional[str] = None
    trocas: list[Any] = Field(default_factory=list)
    motivo_juiz: Optional[str] = None
    campo_invalido: Optional[str] = None
    resposta_turno: Optional[str] = None
    perguntas_seguidas: int = 0  # perguntas fora do contexto seguidas, sem resposta ao dado
    recebido_agora: Optional[str] = None  # dado capturado da mensagem atual, sem o valor
    trace_id: Optional[str] = None  # run raiz do turno no LangSmith, usado pelos feedbacks do juiz
