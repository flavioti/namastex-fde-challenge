"""Log de execução por conversa, gravado enquanto a conversa acontece.

Cada conversa ganha um arquivo novo em AUTOSEGURO_EXECUCOES (padrão: execucoes/). A cada turno, o arquivo
recebe uma seção com a mensagem do lead e a resposta do agente, já mascaradas, o status, o encaminhamento e os
logs JSON que o turno produziu. Os registros de mascaramento ficam de fora, por serem repetitivos.
"""

from __future__ import annotations

import contextvars
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID
from zoneinfo import ZoneInfo

from autoseguro.logs import FormatoJson, configurar_logging
from autoseguro.mascaramento import mascarar_entrada, mascarar_saida

RAIZ = Path(__file__).resolve().parents[2]
PASTA_PADRAO = RAIZ / "execucoes"
FUSO = ZoneInfo("America/Sao_Paulo")
EVENTOS_OMITIDOS = {"mascaramento"}

_coletor: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar("coletor_de_logs", default=None)


class _ColetorDeLogs(logging.Handler):
    """Copia para o turno atual os registros JSON do pacote autoseguro."""

    def emit(self, registro: logging.LogRecord) -> None:
        destino = _coletor.get()
        if destino is None or not registro.name.startswith("autoseguro"):
            return
        if getattr(registro, "evento", None) in EVENTOS_OMITIDOS:
            return
        destino.append(FormatoJson().format(registro))


def _instalar_coletor() -> None:
    raiz = logging.getLogger()
    if not any(isinstance(h, _ColetorDeLogs) for h in raiz.handlers):
        raiz.addHandler(_ColetorDeLogs(level=logging.INFO))


class RegistroExecucao:
    def __init__(self, pasta: Path | None = None) -> None:
        self._pasta = pasta or Path(os.environ.get("AUTOSEGURO_EXECUCOES", PASTA_PADRAO))
        self._arquivos: dict[UUID, Path] = {}
        self._turnos: dict[UUID, int] = {}
        configurar_logging()  # nível INFO e saída JSON no terminal
        _instalar_coletor()

    @contextmanager
    def turno(self, conversa_id: UUID, texto_lead: str) -> Iterator[dict[str, Any]]:
        """Coleta os logs do turno. Quem chama preenche o dicionário yielded com resposta, status e motivo."""
        registros: list[str] = []
        token = _coletor.set(registros)
        resultado: dict[str, Any] = {}
        inicio = datetime.now(timezone.utc)
        try:
            yield resultado
        finally:
            _coletor.reset(token)
            self._gravar(conversa_id, inicio, texto_lead, resultado, registros)

    def _gravar(self, conversa_id: UUID, inicio: datetime, texto_lead: str, resultado: dict[str, Any],
                registros: list[str]) -> None:
        self._pasta.mkdir(parents=True, exist_ok=True)
        if conversa_id not in self._arquivos:
            nome = f"{inicio.astimezone(FUSO):%Y%m%d-%H%M%S}-{str(conversa_id)[:8]}.md"
            self._arquivos[conversa_id] = self._pasta / nome
            self._turnos[conversa_id] = 0
            cabecalho = (f"# Execução da conversa `{conversa_id}`\n\n"
                         f"Início: {inicio.astimezone(FUSO):%d/%m/%Y %H:%M:%S} (Brasília). "
                         "Dados pessoais aparecem mascarados.\n")
            self._arquivos[conversa_id].write_text(cabecalho, encoding="utf-8")

        self._turnos[conversa_id] += 1
        numero = self._turnos[conversa_id]
        lead = mascarar_entrada(texto_lead, conversa_id).texto
        agente = mascarar_saida(resultado.get("resposta") or "", conversa_id).texto if resultado.get("resposta") else "(sem resposta)"
        linhas = [
            "",
            f"## Turno {numero} · {datetime.now(FUSO):%H:%M:%S}",
            "",
            f"**Lead:** {lead}",
            "",
            f"**Agente:** {agente}",
            "",
            f"**Status:** {resultado.get('status', 'não informado')}",
        ]
        if resultado.get("motivo"):
            linhas.append(f"**Encaminhamento:** {resultado['motivo']}")
        linhas += ["", "<details><summary>Logs do turno</summary>", "", "```json"]
        linhas += registros or ["(nenhum registro)"]
        linhas += ["```", "", "</details>", ""]
        with self._arquivos[conversa_id].open("a", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(linhas))
