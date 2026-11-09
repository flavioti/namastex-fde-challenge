"""Respondedor de teste, usado enquanto o agente não está configurado (FDD-0007, seção 6; RFC-0001).

Tem a mesma assinatura de turno do agente. Não usa modelo, não cota, não encaminha e não muda o status.
Grava as mensagens mascaradas no registro, para que o chat tenha o histórico.
"""

from __future__ import annotations

import uuid

from psycopg_pool import ConnectionPool

from autoseguro.banco.repositorios import mensagens
from autoseguro.mascaramento import mascarar_entrada, mascarar_saida

FRASE_FIXA = (
    "Olá! Este é o atendimento da AutoSeguro, uma empresa de seguros de veículos. "
    "O agente de cotação ainda não está disponível nesta simulação."
)


class RespondedorTeste:
    def __init__(self, pool: ConnectionPool):
        self._pool = pool

    def turno(self, conversa_id: uuid.UUID, texto: str) -> str:
        lead = mascarar_entrada(texto, conversa_id).texto
        resposta = mascarar_saida(FRASE_FIXA, conversa_id).texto
        with self._pool.connection() as conexao:
            mensagens.registrar_mensagem(conexao, conversa_id, "lead", lead)
            mensagens.registrar_mensagem(conexao, conversa_id, "agente", resposta)
        return resposta
