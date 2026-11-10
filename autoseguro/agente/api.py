"""Interface pública do agente: turno e leitura de estado (FDD-0005, seção 3).

Nenhuma das duas funções expõe CPF nem CEP originais. O CEP aparece só como marcador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID, uuid4

from langgraph.checkpoint.postgres import PostgresSaver
from langsmith.run_helpers import tracing_context
from psycopg_pool import ConnectionPool

from autoseguro.agente.estado import DadosColeta, StatusConversa
from autoseguro.agente.grafo import construir
from autoseguro.agente.llm import MODELO_AGENTE
from autoseguro.agente.nos import Dependencias
from autoseguro.banco.repositorios import avaliacoes
from autoseguro.observabilidade import config as obs_config
from autoseguro.logs import obter_logger
from autoseguro.observabilidade.cliente import criar_cliente


_log = obter_logger("autoseguro.agente")


@dataclass(frozen=True)
class RespostaTurno:
    texto: Optional[str]  # já mascarado
    status: StatusConversa
    encaminhada: bool


@dataclass(frozen=True)
class EstadoLeitura:
    status: StatusConversa
    motivo_encaminhamento: Optional[str]
    dados: dict[str, Any]
    cotacao_tipo: Optional[str]
    planos: list[dict] = field(default_factory=list)


def _valor(estado: Any, chave: str, padrao: Any = None) -> Any:
    if isinstance(estado, dict):
        return estado.get(chave, padrao)
    return getattr(estado, chave, padrao)


class Agente:
    def __init__(self, deps: Dependencias, pool_checkpoint: ConnectionPool, tipo_execucao: str = "demonstracao"):
        if tipo_execucao not in obs_config.TAGS_VALIDAS:
            raise ValueError(f"tipo de execução inválido: {tipo_execucao!r}")
        self._saver = PostgresSaver(pool_checkpoint)
        self._saver.setup()
        self._tipo_execucao = tipo_execucao
        self._cliente_trace = criar_cliente() if obs_config.tracing_ativo() else None
        if deps.cliente_trace is None:
            deps.cliente_trace = self._cliente_trace
        self._pool_registro = deps.pool
        self._grafo = construir(deps, self._saver)

    @staticmethod
    def _config(conversa_id: UUID) -> dict:
        return {"configurable": {"thread_id": str(conversa_id)}}

    def _gravar_referencia_trace(self, conversa_id: UUID, trace_id: str) -> None:
        """Grava o trace raiz da conversa na primeira execução. Falha não interrompe o turno (FDD-0006, seção 7)."""
        try:
            with self._pool_registro.connection() as conexao:
                avaliacoes.registrar_referencia_trace(conexao, conversa_id, trace_id)
        except Exception:
            _log.error("falha ao gravar referência do trace", extra={"evento": "referencia_trace_falhou",
                                                                     "conversa_id": str(conversa_id)})

    def turno(self, conversa_id: UUID, texto: str) -> RespostaTurno:
        """Processa uma mensagem do lead e devolve a resposta do agente, já mascarada."""
        run_id = uuid4()
        if obs_config.tracing_ativo():
            self._gravar_referencia_trace(conversa_id, str(run_id))
        entrada = {
            "conversa_id": conversa_id,
            "texto_original": texto,
            "proxima": None,
            "trocas": [],
            "campo_invalido": None,
            "motivo_juiz": None,
            "rascunho": None,
            "resposta_turno": None,
            "motivo_encaminhamento": None,
            "trace_id": str(run_id),
            "recebido_agora": None,
        }
        metadados = {
            obs_config.CHAVES["conversa_id"]: str(conversa_id),
            obs_config.CHAVES["modelo"]: MODELO_AGENTE,
            obs_config.CHAVES["tipo_execucao"]: self._tipo_execucao,
        }
        with tracing_context(
            project_name=obs_config.PROJETO,
            tags=[self._tipo_execucao],
            metadata=metadados,
            client=self._cliente_trace,
            enabled=obs_config.tracing_ativo(),
        ):
            resultado = self._grafo.invoke(entrada, {**self._config(conversa_id), "run_id": run_id})
        status = _valor(resultado, "status", "em_andamento")
        return RespostaTurno(
            texto=_valor(resultado, "resposta_turno"),
            status=status,
            encaminhada=status == "encaminhada",
        )

    def ler_estado(self, conversa_id: UUID) -> EstadoLeitura:
        """Lê o estado do checkpoint, sem executar o grafo. CPF e CEP não aparecem."""
        snapshot = self._grafo.get_state(self._config(conversa_id))
        valores = snapshot.values or {}
        dados: DadosColeta = _valor(valores, "dados") or DadosColeta()
        if isinstance(dados, dict):
            dados = DadosColeta(**dados)
        cotacao = _valor(valores, "cotacao")
        return EstadoLeitura(
            status=_valor(valores, "status", "em_andamento"),
            motivo_encaminhamento=_valor(valores, "motivo_encaminhamento"),
            dados={
                "idade": dados.idade,
                "ano_veiculo": dados.ano_veiculo,
                "cep": "[CEP]" if dados.cep else None,
                "data_inicio": dados.data_inicio.isoformat() if dados.data_inicio else None,
                "plano_escolhido": dados.plano_escolhido,
                "consentimento_cpf": dados.consentimento_cpf,
                "cpf_informado": dados.cpf is not None,
            },
            cotacao_tipo=cotacao.get("tipo") if cotacao else None,
            planos=[
                {"plano_nome": p["plano_nome"], "premio_mensal": str(p["premio_mensal"])}
                for p in (cotacao or {}).get("planos", [])
            ],
        )
