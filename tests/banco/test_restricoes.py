"""Restrições do esquema: status, papel, ordem única, um encaminhamento por conversa e coluna gerada
(FDD-0004, seções 5 a 7 e 12)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import psycopg
import pytest

AGORA = datetime.now(timezone.utc)


def _nova_conversa(conexao) -> uuid.UUID:
    conversa_id = uuid.uuid4()
    conexao.execute(
        "INSERT INTO registro.conversas (id, nome_lead, telefone_lead, status, criada_em, atualizada_em) "
        "VALUES (%s, 'Lead Teste', '11999990000', 'em_andamento', %s, %s)",
        (conversa_id, AGORA, AGORA),
    )
    return conversa_id


def test_status_invalido_e_recusado(conexao):
    with pytest.raises(psycopg.errors.CheckViolation):
        conexao.execute(
            "INSERT INTO registro.conversas (id, nome_lead, telefone_lead, status, criada_em, atualizada_em) "
            "VALUES (%s, 'x', 'y', 'qualquer', %s, %s)",
            (uuid.uuid4(), AGORA, AGORA),
        )
    conexao.rollback()


def test_papel_invalido_em_mensagem_e_recusado(conexao):
    conversa_id = _nova_conversa(conexao)
    with pytest.raises(psycopg.errors.CheckViolation):
        conexao.execute(
            "INSERT INTO registro.mensagens (id, conversa_id, ordem, papel, conteudo_mascarado, criada_em, status) "
            "VALUES (%s, %s, 1, 'sistema', 'oi', %s, 'recebida')",
            (uuid.uuid4(), conversa_id, AGORA),
        )
    conexao.rollback()


def test_ordem_de_mensagem_unica_na_conversa(conexao):
    conversa_id = _nova_conversa(conexao)
    conexao.execute(
        "INSERT INTO registro.mensagens (id, conversa_id, ordem, papel, conteudo_mascarado, criada_em, status) "
        "VALUES (%s, %s, 1, 'lead', 'oi', %s, 'recebida')",
        (uuid.uuid4(), conversa_id, AGORA),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        conexao.execute(
            "INSERT INTO registro.mensagens (id, conversa_id, ordem, papel, conteudo_mascarado, criada_em, status) "
            "VALUES (%s, %s, 1, 'agente', 'olá', %s, 'recebida')",
            (uuid.uuid4(), conversa_id, AGORA),
        )
    conexao.rollback()


def test_um_encaminhamento_por_conversa(conexao):
    conversa_id = _nova_conversa(conexao)
    conexao.execute(
        "INSERT INTO registro.encaminhamentos (id, conversa_id, motivo, resumo, criado_em) "
        "VALUES (%s, %s, 'pedido_humano', 'resumo', %s)",
        (uuid.uuid4(), conversa_id, AGORA),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        conexao.execute(
            "INSERT INTO registro.encaminhamentos (id, conversa_id, motivo, resumo, criado_em) "
            "VALUES (%s, %s, 'pedido_humano', 'outro', %s)",
            (uuid.uuid4(), conversa_id, AGORA),
        )
    conexao.rollback()


def test_mensagem_sem_conversa_e_recusada(conexao):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conexao.execute(
            "INSERT INTO registro.mensagens (id, conversa_id, ordem, papel, conteudo_mascarado, criada_em, status) "
            "VALUES (%s, %s, 1, 'lead', 'oi', %s, 'recebida')",
            (uuid.uuid4(), uuid.uuid4(), AGORA),
        )
    conexao.rollback()


def test_texto_busca_e_gerado_pelo_postgres(conexao):
    regra_id = uuid.uuid4()
    conexao.execute(
        "INSERT INTO regras.regras (id, tipo, dados, impressao_digital) "
        "VALUES (%s, 'pro_rata', '{}', 'hash-regra')",
        (regra_id,),
    )
    vetor = "[" + ",".join(["0.1"] * 384) + "]"
    conexao.execute(
        "INSERT INTO regras.trechos (id, regra_id, texto, embedding, modelo_id, dimensao, impressao_digital, gerado_em) "
        "VALUES (%s, %s, 'Pro-rata da vigência', %s::vector, 'e5-small', 384, 'hash-trecho', %s)",
        (uuid.uuid4(), regra_id, vetor, AGORA),
    )
    linha = conexao.execute("SELECT texto_busca::text FROM regras.trechos").fetchone()
    assert linha[0]
    with pytest.raises(psycopg.errors.GeneratedAlways):
        conexao.execute("UPDATE regras.trechos SET texto_busca = to_tsvector('x')")
    conexao.rollback()


def test_dimensao_diferente_de_384_e_recusada(conexao):
    regra_id = uuid.uuid4()
    conexao.execute(
        "INSERT INTO regras.regras (id, tipo, dados, impressao_digital) "
        "VALUES (%s, 'carencia', '{}', 'hash-regra-2')",
        (regra_id,),
    )
    # O tipo vector(384) recusa vetores de outra dimensão antes da restrição CHECK.
    with pytest.raises(psycopg.errors.DataException):
        conexao.execute(
            "INSERT INTO regras.trechos (id, regra_id, texto, embedding, modelo_id, dimensao, impressao_digital, gerado_em) "
            "VALUES (%s, %s, 'x', %s::vector, 'm', 3, 'h', %s)",
            (uuid.uuid4(), regra_id, "[0.1,0.2,0.3]", AGORA),
        )
    conexao.rollback()
