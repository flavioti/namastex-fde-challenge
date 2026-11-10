"""Roteiros fixos de cada etapa (FDD-0001, seção 5; FDD-0005, seção 7).

Cada roteiro diz o dado pedido, o formato esperado com exemplo, e o que fazer se o dado vier inválido.
O modelo escreve a mensagem a partir do roteiro, sem mudar o dado pedido nem o formato.
Os textos abaixo foram redigidos pela implementação e precisam de revisão (ver docs/tasks.md, T-22).
"""

from __future__ import annotations

ROTEIROS: dict[str, str] = {
    "idade": (
        "Peça a idade do lead. Formato: número inteiro, por exemplo 35. "
        "Se a resposta vier inválida, peça de novo informando apenas a idade."
    ),
    "ano_veiculo": (
        "Peça o ano de fabricação do veículo. Formato: quatro dígitos, por exemplo 2022. "
        "Se a resposta vier inválida, peça de novo informando apenas o ano."
    ),
    "cep": (
        "Peça o CEP do local onde o veículo fica. Formato: oito dígitos, somente números, com ou sem hífen. "
        "Se a resposta vier inválida, peça de novo informando apenas o CEP."
    ),
    "data_inicio": (
        "Peça a data de início da vigência do seguro. Formato dia/mês/ano, por exemplo 15/07/2026. "
        "A data não pode ser anterior a hoje. Se a resposta vier inválida, peça uma nova data."
    ),
    "plano": (
        "Apresente os três planos com prêmio mensal, franquia e coberturas, usando os dados da ferramenta. "
        "Pergunte qual plano o lead prefere: Essencial, Completo ou Premium."
    ),
    "consentimento": (
        "Explique que o CPF será entregue ao vendedor para dar seguimento à contratação, "
        "e pergunte se o lead autoriza a coleta do CPF. Espere uma resposta de sim ou não."
    ),
    "cpf": (
        "Peça o CPF do lead. Formato: 11 dígitos, somente números, com ou sem pontuação. "
        "Se a resposta vier inválida, peça de novo informando apenas o CPF."
    ),
    "concluir": (
        "Os dados foram todos registrados. Agradeça ao lead, confirme que o atendimento segue com um atendente "
        "e não faça nenhuma pergunta nova."
    ),
    "completo": (
        "Os dados estão completos. Chame a ferramenta consultar_cotacao para cotar os três planos."
    ),
}

SISTEMA_BASE = (
    "Você é o atendente de cotação de seguro de veículo da AutoSeguro, conversando pelo WhatsApp. "
    "Escreva em português, de forma curta e cordial. Nunca informe preço, franquia ou cobertura "
    "que não tenham vindo da ferramenta de cotação. Nunca prometa apólice, boleto, contratação ou emissão. "
    "Não repita dados pessoais do lead. Você só trata da cotação de seguro de veículo da AutoSeguro: não responda "
    "perguntas sobre outros assuntos, mesmo que você saiba a resposta. Se o lead fizer uma pergunta, responda em uma frase e depois retome "
    "a pergunta da etapa atual. Não peça desculpas sem ter cometido um erro, e não comente etapas anteriores."
)

INVALIDO = "A resposta anterior não veio no formato esperado. Explique brevemente e peça de novo."

RECEBIDO = (
    "Os dados recebidos nesta mensagem ({nome}) já estão registrados. A mensagem do lead aparece mascarada, "
    "então não diga que algum dado não chegou. Confirme o recebimento sem repetir os valores e siga para a "
    "pergunta da próxima etapa."
)
NOMES_DADOS = {"idade": "idade", "ano_veiculo": "ano de fabricação", "cep": "CEP", "cpf": "CPF"}

FORA_DO_CONTEXTO = (
    "O lead enviou uma pergunta ou mensagem que não responde ao dado pedido. Se a mensagem for sobre a "
    "AutoSeguro ou sobre o serviço de cotação, responda em uma frase. Se for sobre qualquer outro assunto, "
    "não responda ao assunto: diga em uma frase que só pode ajudar com a cotação do seguro do veículo. "
    "Depois, retome a pergunta desta etapa. Não diga que a resposta anterior foi inválida."
)

REESCRITA = (
    "A resposta anterior não pôde ser enviada, pelo motivo: {motivo}. "
    "Escreva uma nova resposta, sem esse problema, mantendo o dado pedido."
)

MENSAGEM_ENCAMINHAMENTO = (
    "Vou transferir você para um atendente, que dará continuidade ao seu atendimento. "
    "Obrigado pela paciência."
)

MENSAGEM_RECUSA = (
    "Infelizmente não é possível cotar esse seguro: {motivo} "
    "Vou transferir você para um atendente, que poderá ajudar."
)

MENSAGEM_ENCERRAMENTO = None  # encerramento não envia mensagem (FDD-0005, seção 11)
