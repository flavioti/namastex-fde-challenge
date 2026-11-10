"""Montagem da página Streamlit: barra lateral, abas, chat e painel (FDD-0007, seção 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import streamlit as st

import autoseguro

from autoseguro.banco.repositorios import conversas as repo_conversas
from autoseguro.interface import consultas, leads
from autoseguro.interface.servicos import Servicos, montar_servicos
from autoseguro.interface.turno import MENSAGEM_NEUTRA, processar_turno

STATUS_BLOQUEADOS = ("encaminhada", "encerrada")
CHAVE_AVISO = "aviso"


def _versao_do_codigo() -> float:
    """Data de modificação mais recente do pacote. Muda quando qualquer módulo muda."""
    raiz = Path(autoseguro.__file__).parent
    return max(arquivo.stat().st_mtime for arquivo in raiz.rglob("*.py"))


@st.cache_resource
def _servicos(versao: float) -> Servicos:
    """Recria o agente quando o código muda. O parâmetro faz parte da chave da cache."""
    return montar_servicos()


def _estado_do_agente(responder: Any, conversa_id) -> Optional[dict]:
    if not hasattr(responder, "ler_estado"):
        return None
    try:
        leitura = responder.ler_estado(conversa_id)
    except Exception:
        # Queda do banco no meio da leitura. A página segue, e o painel mostra o aviso.
        st.session_state[CHAVE_AVISO] = ("aviso", "Não foi possível ler os dados coletados. Tente de novo.")
        return None
    return {"dados": leitura.dados}


def _painel(pool, responder, conversa_id) -> dict:
    estado = _estado_do_agente(responder, conversa_id)
    return consultas.painel(pool, conversa_id, estado)


def _mostrar_painel(dados: dict) -> None:
    st.subheader("Painel")
    st.write(f"**Status:** {dados['status']}")
    if dados["dados"]:
        st.write("**Dados coletados**")
        st.json(dados["dados"])
    if dados["cotacao"]:
        st.write(f"**Cotação:** {dados['cotacao']['resultado']}")
        for plano in dados["cotacao"]["planos"]:
            st.write(f"- {plano['nome']}: R$ {plano['premio']} por mês")
    if dados["motivo_encaminhamento"]:
        st.write(f"**Encaminhamento:** {dados['motivo_encaminhamento']}")


def _conversa(pool, responder, conversa_id) -> None:
    chat, painel_col = st.columns([3, 2])
    with chat:
        for mensagem in consultas.mensagens_da_conversa(pool, conversa_id):
            papel = "user" if mensagem["papel"] == "lead" else "assistant"
            with st.chat_message(papel):
                st.write(mensagem["texto"])
                st.caption(mensagem["horario"])

        dados = _painel(pool, responder, conversa_id)
        bloqueada = dados["status"] in STATUS_BLOQUEADOS
        if bloqueada:
            st.info(f"Conversa {dados['status']}. Não é possível enviar novas mensagens.")

        aviso = st.session_state.pop(CHAVE_AVISO, None)
        if aviso:
            st.warning(aviso) if aviso[0] == "aviso" else st.error(aviso[1])

        texto = st.chat_input("Mensagem do lead", disabled=bloqueada)
        if texto:
            resultado = processar_turno(pool, responder, conversa_id, texto)
            if resultado.ocupada:
                st.session_state[CHAVE_AVISO] = ("aviso", "turno em andamento")
            elif resultado.erro:
                st.session_state[CHAVE_AVISO] = ("erro", MENSAGEM_NEUTRA)
            st.rerun()

    with painel_col:
        _mostrar_painel(dados)


def executar() -> None:
    st.set_page_config(page_title="AutoSeguro · simulação", layout="wide")
    try:
        servicos = _servicos(_versao_do_codigo())
    except Exception as erro:
        st.error(f"Não foi possível iniciar a simulação: {erro}")
        st.stop()

    pool = servicos.pool
    if "conversa_id" not in st.session_state:
        st.session_state["conversa_id"] = None

    with st.sidebar:
        st.header("Conversas")
        if st.button("Nova conversa", width="stretch"):
            lead = leads.gerar_lead(leads.carregar_listas())
            with pool.connection() as conexao:
                st.session_state["conversa_id"] = repo_conversas.criar_conversa(
                    conexao, lead.nome, lead.telefone
                )
        for item in consultas.listar_conversas(pool):
            if st.button(item["rotulo"], key=f"conversa-{item['id']}", width="stretch"):
                st.session_state["conversa_id"] = item["id"]

    aba_conversa, aba_encaminhados = st.tabs(["Conversa", "Encaminhados"])
    with aba_conversa:
        if st.session_state["conversa_id"] is None:
            st.info("Crie uma conversa ou escolha uma na barra lateral.")
        else:
            _conversa(pool, servicos.responder, st.session_state["conversa_id"])
    with aba_encaminhados:
        st.dataframe(consultas.encaminhados(pool), width="stretch", hide_index=True)
