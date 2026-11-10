"""Nós do grafo do agente (FDD-0005, seções 5 a 11).

Cada nó recebe o estado e devolve apenas as chaves que muda. Transições são decididas pelo campo `proxima`.
As dependências (modelo, juiz, cotação e pool do registro) entram por fechamento em `criar_nos`.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from psycopg_pool import ConnectionPool

from autoseguro.agente import coleta_valores as cv
from autoseguro.agente import roteiros
from autoseguro.agente.estado import EstadoConversa, Mensagem, STATUS_TERMINAIS
from autoseguro.agente.ferramentas import consultar_cotacao, retorno_para_modelo
from autoseguro.agente.llm import tentar, tokens_da_resposta
from autoseguro.banco.repositorios import conversas as repo_conversas
from autoseguro.banco.repositorios import cotacoes as repo_cotacoes
from autoseguro.banco.repositorios import encaminhamentos as repo_encaminhamentos
from autoseguro.banco.repositorios import mensagens as repo_mensagens
from autoseguro.cotacao import DadosCotacao
from autoseguro.juiz import prompts as prompts_juiz
from autoseguro.observabilidade.feedback import registrar_feedbacks
from autoseguro.logs import obter_logger
from autoseguro.mascaramento import detectar, mascarar_entrada, mascarar_saida

_log = obter_logger("autoseguro.agente")

TETO_TOKENS = 50_000  # ADR-0013
LIMITE_RESUMO_TOKENS = 20_000  # ADR-0013
MENSAGENS_LITERAIS = 10

MOTIVO_TETO = "Limite da conversa atingido"
MOTIVO_DADO_INVALIDO = "Dado inválido após tentativas"
MOTIVO_PEDIDO_LEAD = "Pedido do lead"
MOTIVO_CPF_NEGADO = "CPF não autorizado"
MOTIVO_RECUSADA = "Cotação recusada"
MOTIVO_INDISPONIVEL = "Cotação indisponível"
MOTIVO_FALHA_MODELO = "Falha do modelo"
MOTIVO_FALHA_JUIZ = "Falha do juiz"
MOTIVO_REPROVADA = "Resposta reprovada pelo juiz"

# Frases de pedido de humano e de desistência. Lista fixa, a ser revisada (docs/tasks.md, T-17).
_PEDIDO_HUMANO = ("atendente", "humano", "pessoa de verdade", "vendedor", "falar com alguém")
_DESISTENCIA = ("não quero mais", "nao quero mais", "desisto", "deixa pra lá", "deixa pra la", "cancela")


@dataclass
class Dependencias:
    modelo_agente: Any
    juiz: Any
    cotacao: Any
    pool: ConnectionPool
    sleep: Callable[[float], None] = time.sleep
    cliente_trace: Any = None  # cliente do LangSmith, quando o tracing está ativo


def _passo(dados, cotacao: Optional[dict]) -> Optional[str]:
    """Próximo passo da conversa: um dado pedido, a ferramenta, a escolha do plano, o consentimento ou o CPF."""
    if dados.idade is None:
        return "idade"
    if dados.ano_veiculo is None:
        return "ano_veiculo"
    if dados.cep is None:
        return "cep"
    if dados.data_inicio is None:
        return "data_inicio"
    if cotacao is None:
        return "completo"
    if cotacao.get("tipo") != "sucesso":
        return None
    if dados.plano_escolhido is None:
        return "plano"
    if dados.consentimento_cpf is None:
        return "consentimento"
    if dados.consentimento_cpf and dados.cpf is None:
        return "cpf"
    return None


def _texto_da_resposta(resposta: AIMessage) -> str:
    conteudo = resposta.content
    if isinstance(conteudo, str):
        return conteudo.strip()
    partes = [b.get("text", "") for b in conteudo if isinstance(b, dict) and b.get("type") == "text"]
    return "".join(partes).strip()


def _historico(mensagens: list[Mensagem], trocas: list[BaseMessage]) -> list[BaseMessage]:
    historico: list[BaseMessage] = [
        HumanMessage(content=m.texto) if m.papel == "lead" else AIMessage(content=m.texto) for m in mensagens
    ]
    return historico + list(trocas)


def _sistema(passo: Optional[str], campo_invalido: Optional[str], motivo_juiz: Optional[str],
             resumo: Optional[str]) -> str:
    partes = [roteiros.SISTEMA_BASE]
    if passo and passo in roteiros.ROTEIROS:
        partes.append("Nesta etapa: " + roteiros.ROTEIROS[passo])
    elif passo is None:
        partes.append("Responda ao lead de forma curta, sem pedir dados que já foram informados.")
    if campo_invalido:
        partes.append(roteiros.INVALIDO)
    if motivo_juiz:
        partes.append(roteiros.REESCRITA.format(motivo=motivo_juiz))
    if resumo:
        partes.append("Resumo da conversa anterior: " + resumo)
    return "\n\n".join(partes)


def _estimar_tokens(mensagens: list[Mensagem], resumo: Optional[str]) -> int:
    return (sum(len(m.texto) for m in mensagens) + len(resumo or "")) // 4


def criar_nos(deps: Dependencias) -> dict[str, Callable[[EstadoConversa], dict]]:
    def registro(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with deps.pool.connection() as conexao:
            return fn(conexao, *args, **kwargs)

    def entrada(estado: EstadoConversa) -> dict:
        if estado.status in STATUS_TERMINAIS:
            return {"proxima": "fim", "texto_original": None}
        texto = estado.texto_original or ""
        dados = estado.dados.model_copy()
        passo = _passo(dados, estado.cotacao)
        capturou = False
        recebido = None
        for achado in detectar(texto):
            if achado.tipo == "cep" and passo == "cep" and dados.cep is None:
                dados.cep = cv.extrair_cep(achado.valor)
                capturou = dados.cep is not None or capturou
                recebido = "cep" if dados.cep else recebido
            if achado.tipo == "cpf" and passo == "cpf" and dados.cpf is None:
                dados.cpf = cv.extrair_cpf(achado.valor)
                capturou = dados.cpf is not None or capturou
                recebido = "cpf" if dados.cpf else recebido

        mascarado = mascarar_entrada(texto, estado.conversa_id).texto
        registro(repo_mensagens.registrar_mensagem, estado.conversa_id, "lead", mascarado)
        mensagens = estado.mensagens + [Mensagem(papel="lead", texto=mascarado)]

        resumo = estado.resumo
        if estado.tokens_consumidos >= TETO_TOKENS:
            return {"mensagens": mensagens, "motivo_encaminhamento": MOTIVO_TETO, "proxima": "encaminhamento",
                    "texto_original": None}
        if _estimar_tokens(mensagens, resumo) > LIMITE_RESUMO_TOKENS and len(mensagens) > MENSAGENS_LITERAIS:
            try:
                resumo, tokens = _resumir(deps, mensagens[:-MENSAGENS_LITERAIS], resumo)
            except Exception:
                # Sem resumo, a conversa segue com todas as mensagens. O teto de tokens ainda se aplica.
                _log.error("resumo falhou; mensagens mantidas", extra={"evento": "resumo_falhou"})
            else:
                mensagens = mensagens[-MENSAGENS_LITERAIS:]
                return {"mensagens": mensagens, "resumo": resumo, "dados": dados,
                        "tokens_consumidos": estado.tokens_consumidos + tokens,
                        "texto_original": None if capturou else texto, "proxima": "coleta",
                        "recebido_agora": recebido}

        return {"mensagens": mensagens, "dados": dados,
                "texto_original": None if capturou else texto, "proxima": "coleta",
                "recebido_agora": recebido}

    def coleta(estado: EstadoConversa) -> dict:
        dados = estado.dados.model_copy()
        tentativas = dict(estado.tentativas)
        texto = estado.texto_original
        cotacao = estado.cotacao
        fora_do_contexto = False
        base: dict[str, Any] = {"texto_original": None, "campo_invalido": None, "recebido_agora": None}

        if texto is not None:
            minusculo = texto.lower()
            if any(frase in minusculo for frase in _DESISTENCIA):
                return {**base, "proxima": "encerramento"}
            if any(frase in minusculo for frase in _PEDIDO_HUMANO):
                return {**base, "proxima": "encaminhamento", "motivo_encaminhamento": MOTIVO_PEDIDO_LEAD}
            passo = _passo(dados, cotacao)
            if passo in ("idade", "ano_veiculo", "cep", "data_inicio", "cpf"):
                valor = _extrair(passo, texto)
                if valor is not None:
                    setattr(dados, passo, valor)
                    tentativas[passo] = 0
                elif cv.eh_outro_contexto(texto):
                    fora_do_contexto = True  # pergunta ou saudação não conta como tentativa
                else:
                    tentativas[passo] = tentativas.get(passo, 0) + 1
                    if tentativas[passo] >= 3:
                        return {**base, "dados": dados, "tentativas": tentativas, "proxima": "encaminhamento",
                                "motivo_encaminhamento": MOTIVO_DADO_INVALIDO}
                    base["campo_invalido"] = passo
            elif passo == "plano":
                escolhido = cv.extrair_plano(texto)
                if escolhido:
                    dados.plano_escolhido = escolhido
            elif passo == "consentimento":
                autorizado = cv.extrair_consentimento(texto)
                if autorizado is False:
                    dados.consentimento_cpf = False
                    return {**base, "dados": dados, "proxima": "encaminhamento",
                            "motivo_encaminhamento": MOTIVO_CPF_NEGADO}
                if autorizado is True:
                    dados.consentimento_cpf = True

        passo = _passo(dados, cotacao)
        # A ferramenta fica disponível enquanto a cotação não foi feita, e sempre que a troca da ferramenta
        # estiver no histórico, pois a API exige a definição da ferramenta nesse caso.
        ferramentas = [consultar_cotacao] if (passo == "completo" or estado.trocas) else []
        sistema = _sistema(passo, base["campo_invalido"], estado.motivo_juiz, estado.resumo)
        if estado.recebido_agora:
            sistema += "\n\n" + roteiros.RECEBIDO.format(nome=roteiros.NOMES_DADOS[estado.recebido_agora])
        if fora_do_contexto:
            sistema += "\n\n" + roteiros.FORA_DO_CONTEXTO
        historico = _historico(estado.mensagens, estado.trocas)

        try:
            resposta = tentar(lambda: deps.modelo_agente.conversar(sistema, historico, ferramentas), deps.sleep)
        except Exception:
            _log.error("modelo do agente falhou após três tentativas", extra={"evento": "falha_modelo"})
            return {**base, "dados": dados, "tentativas": tentativas, "proxima": "encaminhamento",
                    "motivo_encaminhamento": MOTIVO_FALHA_MODELO}

        tokens = tokens_da_resposta(resposta, sistema + "".join(m.content for m in historico if isinstance(m.content, str)),
                                    _texto_da_resposta(resposta))
        atualizacao = {**base, "dados": dados, "tentativas": tentativas, "motivo_juiz": None,
                       "tokens_consumidos": estado.tokens_consumidos + tokens}

        if resposta.tool_calls and cotacao is None:
            return {**atualizacao, "trocas": [resposta], "rascunho": None, "proxima": "cotacao"}

        texto_resposta = _texto_da_resposta(resposta)
        if not texto_resposta:
            return {**atualizacao, "motivo_encaminhamento": MOTIVO_FALHA_MODELO, "proxima": "encaminhamento",
                    "rascunho": None}
        proxima = "juiz" if prompts_juiz.acionado(texto_resposta) else "resposta"
        return {**atualizacao, "rascunho": texto_resposta, "proxima": proxima}

    def cotacao(estado: EstadoConversa) -> dict:
        dados = estado.dados
        pedido = DadosCotacao(idade=dados.idade, veiculo_ano=dados.ano_veiculo, cep=dados.cep,
                              data_inicio=dados.data_inicio)
        resultado = deps.cotacao.cotar(pedido, estado.conversa_id).model_dump(mode="json")
        registro(repo_cotacoes.registrar_cotacao, estado.conversa_id, resultado["tipo"],
                 planos=resultado.get("planos"), motivo=resultado.get("motivo") or resultado.get("detalhe"))

        id_ferramenta = estado.trocas[-1].tool_calls[0]["id"] if estado.trocas else "cotacao"
        retorno = ToolMessage(content=retorno_para_modelo(resultado), tool_call_id=id_ferramenta)
        if resultado["tipo"] == "sucesso":
            registro(repo_conversas.atualizar_status, estado.conversa_id, "cotada")
            return {"cotacao": resultado, "trocas": [*estado.trocas, retorno], "status": "cotada",
                    "proxima": "coleta"}
        motivo = MOTIVO_RECUSADA if resultado["tipo"] == "recusada" else MOTIVO_INDISPONIVEL
        return {"cotacao": resultado, "trocas": [], "motivo_encaminhamento": motivo, "proxima": "encaminhamento"}

    def juiz(estado: EstadoConversa) -> dict:
        cot = estado.cotacao
        planos = cot.get("planos") if cot and cot.get("tipo") == "sucesso" else None
        motivo_cotacao = cot.get("motivo") if cot else None
        decisao = deps.juiz.avaliar(estado.rascunho or "", planos, estado.status, motivo_cotacao)
        tokens = {"tokens_consumidos": estado.tokens_consumidos + decisao.tokens}
        if deps.cliente_trace is not None and estado.trace_id:
            registrar_feedbacks(deps.cliente_trace, uuid.UUID(estado.trace_id), decisao)
        if decisao.aprovado:
            return {"proxima": "resposta", "motivo_juiz": None, **tokens}
        if decisao.motivo == "falha do juiz":
            return {"proxima": "encaminhamento", "motivo_encaminhamento": MOTIVO_FALHA_JUIZ, "rascunho": None,
                    **tokens}
        if estado.reescritas >= 1:
            return {"proxima": "encaminhamento", "motivo_encaminhamento": MOTIVO_REPROVADA, "rascunho": None,
                    **tokens}
        return {"proxima": "coleta", "reescritas": estado.reescritas + 1, "rascunho": None,
                "motivo_juiz": decisao.motivo or "resposta fora das regras", **tokens}

    def resposta(estado: EstadoConversa) -> dict:
        texto = mascarar_saida(estado.rascunho or "", estado.conversa_id).texto
        registro(repo_mensagens.registrar_mensagem, estado.conversa_id, "agente", texto)
        return {"mensagens": [*estado.mensagens, Mensagem(papel="agente", texto=texto)],
                "resposta_turno": texto, "rascunho": None, "reescritas": 0, "trocas": [],
                "motivo_juiz": None, "texto_original": None, "proxima": "fim"}

    def encaminhamento(estado: EstadoConversa) -> dict:
        motivo = estado.motivo_encaminhamento or "Encaminhamento"
        if motivo == MOTIVO_RECUSADA and estado.cotacao:
            texto = roteiros.MENSAGEM_RECUSA.format(motivo=estado.cotacao.get("motivo", ""))
        else:
            texto = roteiros.MENSAGEM_ENCAMINHAMENTO
        mascarado = mascarar_saida(texto, estado.conversa_id).texto
        resumo_encaminhamento = f"Motivo: {motivo}. Cotação: {(estado.cotacao or {}).get('tipo', 'não realizada')}."
        registro(repo_encaminhamentos.registrar_encaminhamento, estado.conversa_id, motivo, resumo_encaminhamento,
                 cpf=estado.dados.cpf)
        registro(repo_conversas.atualizar_status, estado.conversa_id, "encaminhada")
        registro(repo_mensagens.registrar_mensagem, estado.conversa_id, "agente", mascarado)
        return {"status": "encaminhada", "mensagens": [*estado.mensagens, Mensagem(papel="agente", texto=mascarado)],
                "resposta_turno": mascarado, "rascunho": None, "trocas": [], "texto_original": None, "proxima": "fim"}

    def encerramento(estado: EstadoConversa) -> dict:
        registro(repo_conversas.atualizar_status, estado.conversa_id, "encerrada")
        return {"status": "encerrada", "trocas": [], "texto_original": None, "rascunho": None, "proxima": "fim",
                "resposta_turno": None}

    return {"entrada": entrada, "coleta": coleta, "cotacao": cotacao, "juiz": juiz, "resposta": resposta,
            "encaminhamento": encaminhamento, "encerramento": encerramento}


def _extrair(passo: str, texto: str) -> Any:
    if passo == "idade":
        return cv.extrair_idade(texto)
    if passo == "ano_veiculo":
        return cv.extrair_ano_veiculo(texto)
    if passo == "cep":
        return cv.extrair_cep(texto)
    if passo == "data_inicio":
        return cv.extrair_data_inicio(texto)
    if passo == "cpf":
        return cv.extrair_cpf(texto)
    return None


def _resumir(deps: Dependencias, antigas: list[Mensagem], resumo_anterior: Optional[str]) -> tuple[str, int]:
    """Resumo acumulado das mensagens antigas, escrito pelo modelo do agente (FDD-0005, seção 6)."""
    trecho = "\n".join(f"{m.papel}: {m.texto}" for m in antigas)
    if resumo_anterior:
        trecho = f"Resumo anterior: {resumo_anterior}\n{trecho}"
    sistema = "Resuma a conversa em até 300 palavras, em português, sem dados pessoais."
    resposta = tentar(lambda: deps.modelo_agente.conversar(sistema, [HumanMessage(content=trecho)], []), deps.sleep)
    tokens = tokens_da_resposta(resposta, trecho, _texto_da_resposta(resposta))
    return _texto_da_resposta(resposta), tokens


__all__ = ["Dependencias", "criar_nos", "MOTIVO_TETO"]
