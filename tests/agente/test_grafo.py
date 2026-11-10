"""Caminhos completos do grafo, com modelos substitutos, cotação simulada e banco real (FDD-0005, seção 14)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from langchain_core.messages import AIMessage, ToolMessage

from autoseguro.agente import Agente, Dependencias, criar_pool_agente
from autoseguro.agente.roteiros import ROTEIROS
from autoseguro.banco.conexao import abrir_pool
from autoseguro.banco.repositorios import avaliacoes
from autoseguro.banco.repositorios import conversas
from autoseguro.cotacao import CotacaoClient
from autoseguro.juiz import Juiz, VeredictoJuiz

BASE = "http://quote.test"
AGORA = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
TEXTO_PLANOS = "Temos três planos. O Essencial custa R$ 119,90 por mês, com franquia de R$ 1.500,00."


# ----- dublês -----------------------------------------------------------------

class ModeloAgenteFalso:
    """Responde conforme o roteiro da etapa. Registra tudo que recebe, para checar vazamentos."""

    def __init__(self, primeira_resposta_planos: str = TEXTO_PLANOS, usage: dict | None = None,
                 falhar: bool = False):
        self.recebido: list[str] = []
        self.primeira_resposta_planos = primeira_resposta_planos
        self.usage = usage
        self.falhar = falhar
        self.apresentacoes = 0  # respostas que apresentam os planos, depois da ferramenta

    def conversar(self, sistema, mensagens, ferramentas=()):
        texto_entrada = sistema + " " + " ".join(str(getattr(m, "content", "")) for m in mensagens)
        self.recebido.append(texto_entrada)
        if self.falhar:
            raise RuntimeError("API indisponível")
        uso = {"usage_metadata": self.usage} if self.usage else {}
        if any(isinstance(m, ToolMessage) for m in mensagens):
            self.apresentacoes += 1
            texto = self.primeira_resposta_planos if self.apresentacoes == 1 else TEXTO_PLANOS
            return AIMessage(content=texto, **uso)
        if ferramentas and ROTEIROS["completo"] in sistema:
            return AIMessage(content="", tool_calls=[{"name": "consultar_cotacao", "args": {}, "id": "call-1"}],
                             **uso)
        for chave, roteiro in ROTEIROS.items():
            if roteiro in sistema:
                return AIMessage(content=f"[pergunta:{chave}]", **uso)
        return AIMessage(content="Entendi, obrigado.", **uso)


class JuizFalso:
    """Saída do modelo do juiz, roteirizada. Devolve aprovado quando a lista acaba."""

    def __init__(self, saidas=None, tokens=0):
        self.saidas = list(saidas or [])
        self.chamadas = 0
        self.tokens = tokens

    def estruturar(self, sistema, conteudo, schema):
        self.chamadas += 1
        if self.saidas:
            saida = self.saidas.pop(0)
            if isinstance(saida, Exception):
                raise saida
            return saida, self.tokens
        return VeredictoJuiz(aprovado=True), self.tokens


def _plano(plano_id: str, nome: str) -> dict:
    return {
        "plano_id": plano_id, "plano_nome": nome, "premio_mensal": 119.9, "franquia": 1500.0,
        "coberturas": ["colisão", "roubo"], "carencia": {"dias": 30},
        "primeiro_pagamento_pro_rata": {"valor_primeiro_pagamento": 65.7},
    }


def _transporte(modo: str = "ok"):
    def handler(request: httpx.Request) -> httpx.Response:
        if modo == "ok":
            plano = json.loads(request.content)["plano_id"]
            return httpx.Response(200, json=_plano(plano, plano.capitalize()))
        if modo == "recusada":
            return httpx.Response(422, json={"error": "cotacao_recusada", "motivo": "Veículo com mais de 20 anos."})
        return httpx.Response(503, json={"error": "upstream_unavailable"})
    return httpx.MockTransport(handler)


@pytest.fixture
def ambiente(url_banco):
    """Pool do registro, pool do checkpoint e a conversa criada no registro."""
    pool_registro = abrir_pool(url_banco)
    pool_checkpoint = criar_pool_agente(url_banco)
    with pool_registro.connection() as conexao:
        conversa_id = conversas.criar_conversa(conexao, "Lead Teste", "11999990000", agora=AGORA)
    yield {"registro": pool_registro, "checkpoint": pool_checkpoint, "conversa": conversa_id}
    pool_checkpoint.close()
    pool_registro.close()


def _agente(ambiente, modelo, juiz_modelo=None, transporte="ok", cliente_trace=None):
    cotacao = CotacaoClient(BASE, transporte=_transporte(transporte), sleep=lambda s: None)
    deps = Dependencias(
        modelo_agente=modelo,
        juiz=Juiz(juiz_modelo or JuizFalso(), sleep=lambda s: None),
        cotacao=cotacao,
        pool=ambiente["registro"],
        sleep=lambda s: None,
        cliente_trace=cliente_trace,
    )
    return Agente(deps, ambiente["checkpoint"]), cotacao


class ClienteTraceFalso:
    def __init__(self):
        self.feedbacks = []

    def create_feedback(self, run_id, key, score, comment):
        self.feedbacks.append({"run_id": run_id, "key": key, "score": score})


def _conversar(agente, conversa_id, mensagens):
    return [agente.turno(conversa_id, texto) for texto in mensagens]


def _contar(pool, sql, parametros=()):
    with pool.connection() as c:
        return c.execute(sql, parametros).fetchone()[0]


def _status(pool, conversa_id):
    with pool.connection() as c:
        return c.execute("SELECT status FROM registro.conversas WHERE id = %s", (conversa_id,)).fetchone()[0]


def _encaminhamento(pool, conversa_id):
    with pool.connection() as c:
        return c.execute(
            "SELECT motivo, cpf FROM registro.encaminhamentos WHERE conversa_id = %s", (conversa_id,)
        ).fetchone()


# ----- caminhos ---------------------------------------------------------------

def test_caminho_feliz_cota_escolhe_plano_e_coleta_cpf(ambiente):
    modelo = ModeloAgenteFalso()
    agente, _ = _agente(ambiente, modelo)
    conversa = ambiente["conversa"]

    respostas = _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])
    assert respostas[-1].texto == TEXTO_PLANOS
    assert respostas[-1].status == "cotada"

    escolha = agente.turno(conversa, "quero o premium")
    assert escolha.texto == "[pergunta:consentimento]"
    consentimento = agente.turno(conversa, "sim")
    assert consentimento.texto == "[pergunta:cpf]"
    final = agente.turno(conversa, "987.654.321-00")
    assert final.status == "cotada" and not final.encaminhada

    pool = ambiente["registro"]
    assert _contar(pool, "SELECT count(*) FROM registro.cotacoes WHERE conversa_id = %s", (conversa,)) == 1
    assert _contar(pool, "SELECT count(*) FROM registro.encaminhamentos WHERE conversa_id = %s", (conversa,)) == 0
    estado = agente.ler_estado(conversa)
    assert estado.dados["cep"] == "[CEP]"
    assert estado.dados["cpf_informado"] is True
    assert "987.654.321-00" not in json.dumps(estado.dados)


def test_modelo_nunca_recebe_cep_nem_cpf(ambiente):
    modelo = ModeloAgenteFalso()
    agente, _ = _agente(ambiente, modelo)
    conversa = ambiente["conversa"]
    _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026", "premium", "sim", "987.654.321-00"])
    todo_o_texto = " ".join(modelo.recebido)
    for valor in ["01310-100", "987.654.321-00", "98765432100"]:
        assert valor not in todo_o_texto


def test_cotacao_recusada_por_regra_encaminha_com_motivo(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso(), transporte="recusada")
    conversa = ambiente["conversa"]
    resposta = _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])[-1]
    assert resposta.encaminhada and resposta.status == "encaminhada"
    assert "mais de 20 anos" in resposta.texto
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Cotação recusada"


def test_falha_persistente_da_cotacao_encaminha(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso(), transporte="falha")
    conversa = ambiente["conversa"]
    resposta = _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])[-1]
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Cotação indisponível"
    assert "R$" not in (resposta.texto or "")


def test_pedido_de_humano_encaminha(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    resposta = agente.turno(conversa, "quero falar com um atendente")
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Pedido do lead"


def test_tres_respostas_invalidas_encaminham(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    primeira, segunda, terceira = _conversar(agente, conversa, ["trinta", "abc", "xx"])
    assert primeira.status == "em_andamento" and segunda.status == "em_andamento"
    assert terceira.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Dado inválido após tentativas"


def test_desistencia_encerra_sem_mensagem(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    resposta = agente.turno(conversa, "não quero mais")
    assert resposta.status == "encerrada"
    assert resposta.texto is None
    assert _status(ambiente["registro"], conversa) == "encerrada"


def test_recusa_do_cpf_encaminha_mantendo_cotacao(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026", "essencial", "não autorizo"])
    pool = ambiente["registro"]
    assert _encaminhamento(pool, conversa)[0] == "CPF não autorizado"
    assert _contar(pool, "SELECT count(*) FROM registro.cotacoes WHERE conversa_id = %s", (conversa,)) == 1


def test_juiz_reprova_uma_vez_e_aprova_a_reescrita(ambiente):
    modelo = ModeloAgenteFalso(primeira_resposta_planos="O Essencial custa R$ 999,00.")
    juiz = JuizFalso([])
    agente, _ = _agente(ambiente, modelo, juiz_modelo=juiz)
    conversa = ambiente["conversa"]
    resposta = _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])[-1]
    assert resposta.texto == TEXTO_PLANOS
    assert resposta.status == "cotada"
    assert _contar(ambiente["registro"], "SELECT count(*) FROM registro.encaminhamentos WHERE conversa_id = %s",
                   (conversa,)) == 0


def test_juiz_reprova_a_reescrita_e_encaminha(ambiente):
    modelo = ModeloAgenteFalso(primeira_resposta_planos="O Essencial custa R$ 999,00.")
    # A reescrita também cita valor fora da cotação: a R1 reprova de novo, sem chamar o modelo do juiz.
    original = modelo.conversar

    def conversar_sempre_errado(sistema, mensagens, ferramentas=()):
        resposta = original(sistema, mensagens, ferramentas)
        if isinstance(resposta.content, str) and "R$ 119,90" in resposta.content:
            return AIMessage(content="O Essencial custa R$ 999,00.")
        return resposta

    modelo.conversar = conversar_sempre_errado
    agente, _ = _agente(ambiente, modelo, juiz_modelo=JuizFalso([]))
    conversa = ambiente["conversa"]
    resposta = _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])[-1]
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Resposta reprovada pelo juiz"


def test_falha_do_juiz_encaminha(ambiente):
    falhas = [ValueError("formato"), ValueError("formato"), ValueError("formato")]
    agente, _ = _agente(ambiente, ModeloAgenteFalso(), juiz_modelo=JuizFalso(falhas))
    conversa = ambiente["conversa"]
    resposta = _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])[-1]
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Falha do juiz"


def test_falha_do_modelo_encaminha(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso(falhar=True))
    conversa = ambiente["conversa"]
    resposta = agente.turno(conversa, "35")
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Falha do modelo"


def test_teto_de_tokens_encaminha(ambiente):
    modelo = ModeloAgenteFalso(usage={"input_tokens": 60_000, "output_tokens": 0, "total_tokens": 60_000})
    agente, _ = _agente(ambiente, modelo)
    conversa = ambiente["conversa"]
    agente.turno(conversa, "35")  # consome o teto
    resposta = agente.turno(conversa, "2022")
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Limite da conversa atingido"


def test_turno_depois_de_encaminhada_nao_responde(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    agente.turno(conversa, "quero falar com um atendente")
    depois = agente.turno(conversa, "35")
    assert depois.texto is None
    assert depois.status == "encaminhada"


def test_consumo_do_juiz_conta_no_teto(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso(), juiz_modelo=JuizFalso(tokens=60_000))
    conversa = ambiente["conversa"]
    _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])  # o juiz aprova e gasta o teto
    resposta = agente.turno(conversa, "premium")
    assert resposta.encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Limite da conversa atingido"


def test_feedbacks_do_juiz_vao_para_o_run_do_turno(ambiente):
    cliente = ClienteTraceFalso()
    agente, _ = _agente(ambiente, ModeloAgenteFalso(), cliente_trace=cliente)
    conversa = ambiente["conversa"]
    _conversar(agente, conversa, ["35", "2022", "01310-100", "15/12/2026"])
    chaves = {f["key"] for f in cliente.feedbacks}
    assert chaves == {"juiz_regra_1", "juiz_regra_2", "juiz_regra_3", "juiz_regra_4", "juiz_decisao"}
    run_ids = {str(f["run_id"]) for f in cliente.feedbacks}
    assert len(run_ids) == 1  # todos no mesmo run do turno em que o juiz avaliou


def test_referencia_do_trace_e_gravada_uma_vez(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    primeiro = uuid.uuid4()
    agente._gravar_referencia_trace(conversa, str(primeiro))
    agente._gravar_referencia_trace(conversa, str(uuid.uuid4()))
    with ambiente["registro"].connection() as c:
        assert avaliacoes.obter_referencia_trace(c, conversa) == str(primeiro)


def test_modelo_e_avisado_de_que_o_cep_foi_recebido(ambiente):
    modelo = ModeloAgenteFalso()
    agente, _ = _agente(ambiente, modelo)
    conversa = ambiente["conversa"]
    _conversar(agente, conversa, ["35", "2022", "01310-100"])
    assert any("Os dados recebidos nesta mensagem (CEP)" in texto for texto in modelo.recebido)
    assert not any("CEP ainda não" in texto for texto in modelo.recebido)


def test_pergunta_nao_conta_como_tentativa(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    respostas = _conversar(agente, conversa, ["Oi, boa noite", "Para que serve?", "Qual o preço?", "42"])
    assert all(not r.encaminhada for r in respostas)
    assert agente.ler_estado(conversa).dados["idade"] == 42


def test_tres_respostas_invalidas_ainda_encaminham_apos_perguntas(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    _conversar(agente, conversa, ["Para que serve?", "trinta", "abc", "xx"])
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Dado inválido após tentativas"


def test_cinco_perguntas_seguidas_encaminham(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    respostas = _conversar(agente, conversa, ["Para que serve?", "Qual o preço?", "Como funciona?",
                                             "O que é isso?", "Quanto custa?"])
    assert respostas[-1].encaminhada
    assert _encaminhamento(ambiente["registro"], conversa)[0] == "Perguntas fora do contexto"


def test_resposta_valida_zera_o_contador_de_perguntas(ambiente):
    agente, _ = _agente(ambiente, ModeloAgenteFalso())
    conversa = ambiente["conversa"]
    antes = _conversar(agente, conversa, ["Para que serve?", "Qual o preço?", "Como funciona?", "O que é isso?",
                                         "35", "Para que serve?", "Qual o preço?", "Como funciona?",
                                         "O que é isso?"])
    assert not antes[-1].encaminhada  # quatro perguntas depois da resposta válida, abaixo do limite
    assert agente.turno(conversa, "O que é isso?").encaminhada  # a quinta encaminha


def test_dados_juntos_numa_mensagem_sao_guardados(ambiente):
    modelo = ModeloAgenteFalso()
    agente, _ = _agente(ambiente, modelo)
    conversa = ambiente["conversa"]
    resposta = agente.turno(conversa, "Minha idade é 42 e meu cep é 01310-100")
    estado = agente.ler_estado(conversa)
    assert estado.dados["idade"] == 42
    assert estado.dados["cep"] == "[CEP]"
    assert resposta.texto == "[pergunta:ano_veiculo]"
