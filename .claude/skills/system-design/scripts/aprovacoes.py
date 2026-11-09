#!/usr/bin/env python3
"""Detecta documentos de design que o system design ou a rastreabilidade ainda não refletiram.

Acompanha os PRDs, RFCs, ADRs e FDDs de docs/ (pelo frontmatter `tipo` e `status`).
O JSON do diagrama guarda em meta.documentos_status o status de cada um
({"rfc-0001-exemplo": "aprovado", ...}), como a skill system-design
o considerou da última vez. Este script avisa quando:
    - um documento é novo (não está em meta.documentos_status);
    - o status de um documento mudou (ex.: rascunho -> aprovado, proposto -> aceito);
    - um documento registrado deixou de existir;
    - um documento acompanhado não é citado em docs/rastreabilidade.md.

Uso, a partir da raiz do repositório:
    python3 .claude/skills/system-design/scripts/aprovacoes.py
        # lista as pendências; código de saída 1 se houver alguma
    python3 .claude/skills/system-design/scripts/aprovacoes.py --hook PostToolUse
        # modo hook: lê o evento na entrada padrão e, se houver pendência, devolve
        # JSON com additionalContext pedindo ao Claude que rode a skill system-design.
        # Sem pendência, não imprime nada.

Só usa a biblioteca padrão do Python.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
RAIZ = SKILL.parents[2]
DADOS = RAIZ / "system-design" / "autoseguro-system-design.json"
RASTREABILIDADE = RAIZ / "docs" / "rastreabilidade.md"
TIPOS = {"prd", "rfc", "adr", "fdd"}


def frontmatter(texto):
    if not texto.startswith("---"):
        return {}
    fim = texto.find("\n---", 3)
    if fim < 0:
        return {}
    campos = {}
    for linha in texto[3:fim].splitlines():
        m = re.match(r"^(tipo|status):\s*[\"']?([\w-]+)", linha)
        if m:
            campos[m.group(1)] = m.group(2).lower()
    return campos


def documentos():
    """Status atual de cada PRD, RFC, ADR e FDD: {nome da nota: status}."""
    docs = {}
    for p in (RAIZ / "docs").rglob("*.md"):
        try:
            fm = frontmatter(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if fm.get("tipo") in TIPOS:
            docs[p.stem] = fm.get("status", "")
    return docs


def registrados():
    """Status de cada documento como o diagrama o considerou: meta.documentos_status."""
    try:
        meta = json.loads(DADOS.read_text(encoding="utf-8")).get("meta", {})
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(meta.get("documentos_status", {}))


def pendencias():
    atuais, vistos = documentos(), registrados()
    novos = sorted((n, atuais[n]) for n in atuais if n not in vistos)
    mudados = sorted((n, vistos[n], atuais[n]) for n in atuais if n in vistos and vistos[n] != atuais[n])
    removidos = sorted(n for n in vistos if n not in atuais)
    return novos, mudados, removidos


def fora_da_rastreabilidade():
    """Documentos acompanhados que não são citados no documento de rastreabilidade."""
    try:
        texto = RASTREABILIDADE.read_text(encoding="utf-8")
    except OSError:
        return []
    return sorted(n for n in documentos() if f"[[{n}" not in texto)


def mensagem(novos, mudados, removidos, sem_rastro):
    partes = []
    if novos:
        partes.append("novos: " + ", ".join(f"[[{n}]] ({s})" for n, s in novos))
    if mudados:
        partes.append("status alterado: " + ", ".join(f"[[{n}]] ({a} -> {b})" for n, a, b in mudados))
    if removidos:
        partes.append("removidos ou renomeados: " + ", ".join(f"[[{n}]]" for n in removidos))
    texto = ""
    if partes:
        texto = ("Documentos de design mudaram — " + "; ".join(partes) + ". "
                 "Rode a skill system-design agora para atualizar o diagrama (as versões geral e aprovado) "
                 "e atualize meta.documentos_status no JSON.")
    if sem_rastro:
        texto += ((" " if texto else "")
                  + "Documentos que não aparecem em docs/rastreabilidade.md: "
                  + ", ".join(f"[[{n}]]" for n in sem_rastro)
                  + ". Acrescente-os ao ciclo de vida e registre a origem das decisões deles.")
    return texto


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hook", metavar="EVENTO", help="modo hook (PostToolUse, UserPromptSubmit ou SessionStart)")
    a = ap.parse_args()

    novos, mudados, removidos = pendencias()
    sem_rastro = fora_da_rastreabilidade()
    ha_pendencia = bool(novos or mudados or removidos or sem_rastro)
    if a.hook:
        sys.stdin.read()  # o evento não é usado: a verificação olha todo o repositório
        if ha_pendencia:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": a.hook,
                                                     "additionalContext": mensagem(novos, mudados, removidos, sem_rastro)}},
                             ensure_ascii=False))
        return
    if not ha_pendencia:
        print("nenhuma pendência: o diagrama e a rastreabilidade refletem todos os PRDs, RFCs, ADRs e FDDs")
        return
    print(mensagem(novos, mudados, removidos, sem_rastro))
    sys.exit(1)


if __name__ == "__main__":
    main()
