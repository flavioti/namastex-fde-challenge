"""Acesso aos modelos da Anthropic (ADR-0007; RFC-0005; FDD-0005, seção 2).

Cada chamada tem até três tentativas, com esperas de 0,5 s e 1 s, sem jitter. O cliente do LangChain
não repete chamadas (max_retries=0), para que a política fique em um único lugar.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Sequence, TypeVar

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

MODELO_AGENTE = "claude-haiku-5-5"
MODELO_JUIZ = "claude-opus-5-5"
TENTATIVAS = 3
ESPERAS = (0.5, 1.0)

T = TypeVar("T")


def tentar(chamada: Callable[[], T], sleep: Callable[[float], None] = time.sleep) -> T:
    """Repete a chamada até TENTATIVAS vezes. Relança o último erro se todas falharem."""
    ultimo: Exception | None = None
    for numero in range(1, TENTATIVAS + 1):
        try:
            return chamada()
        except Exception as erro:  # erros de rede, de API e de formato são todos tentativas perdidas
            ultimo = erro
            if numero < TENTATIVAS:
                sleep(ESPERAS[numero - 1])
    assert ultimo is not None
    raise ultimo


class ModeloAnthropic:
    """Adaptador sobre ChatAnthropic, com temperatura 0 (RFC-0005)."""

    def __init__(self, modelo_id: str):
        from langchain_anthropic import ChatAnthropic

        self.modelo_id = modelo_id
        self._llm = ChatAnthropic(model=modelo_id, temperature=0, max_retries=0)

    def conversar(
        self,
        sistema: str,
        mensagens: Sequence[BaseMessage],
        ferramentas: Sequence[Any] = (),
    ) -> AIMessage:
        llm: Any = self._llm.bind_tools(list(ferramentas)) if ferramentas else self._llm
        return llm.invoke([SystemMessage(content=sistema), *mensagens])

    def estruturar(self, sistema: str, conteudo: str, schema: type[T]) -> T:
        llm: Any = self._llm.with_structured_output(schema)
        return llm.invoke([SystemMessage(content=sistema), HumanMessage(content=conteudo)])


def tokens_da_resposta(resposta: AIMessage, texto_entrada: str = "", texto_saida: str = "") -> int:
    """Soma de entrada e saída. Sem contagem do provedor, estima por caracteres (4 por token)."""
    uso = getattr(resposta, "usage_metadata", None) or {}
    if uso.get("input_tokens") is not None or uso.get("output_tokens") is not None:
        return int(uso.get("input_tokens") or 0) + int(uso.get("output_tokens") or 0)
    return (len(texto_entrada) + len(texto_saida)) // 4
