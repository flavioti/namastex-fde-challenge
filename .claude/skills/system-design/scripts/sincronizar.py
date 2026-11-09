#!/usr/bin/env python3
"""Regenera os HTMLs do system design quando o JSON for mais recente que eles.

Compara a data de modificação de system-design/autoseguro-system-design.json com a dos dois
HTMLs gerados (geral e aprovado). Se o JSON for mais novo, ou se algum HTML não
existir, roda o gerar.py (sem capturas).

Uso, a partir da raiz do repositório:
    python3 .claude/skills/system-design/scripts/sincronizar.py
        # regenera se preciso e diz o que fez
    python3 .claude/skills/system-design/scripts/sincronizar.py --hook PostToolUse
        # modo hook: lê o evento na entrada padrão; só imprime (JSON com
        # additionalContext) quando regenerou ou quando a geração falhou.

Só usa a biblioteca padrão do Python.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
RAIZ = SKILL.parents[2]
SUBDIR = RAIZ / "system-design" / "subsistemas"
DADOS = [RAIZ / "system-design" / "autoseguro-system-design.json"] + sorted(SUBDIR.glob("*.json"))
SAIDAS = [RAIZ / "system-design" / "autoseguro-system-design-geral.html",
          RAIZ / "system-design" / "autoseguro-system-design-aprovado.html"]
for _p in sorted(SUBDIR.glob("*.json")):
    SAIDAS += [SUBDIR / f"{_p.stem}-geral.html", SUBDIR / f"{_p.stem}-aprovado.html"]
GERAR = SKILL / "scripts" / "gerar.py"


def precisa_gerar():
    existentes = [d for d in DADOS if d.exists()]
    if not existentes:
        return False
    mais_recente = max(d.stat().st_mtime for d in existentes)
    return any(not s.exists() or s.stat().st_mtime < mais_recente for s in SAIDAS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hook", metavar="EVENTO", help="modo hook (PostToolUse ou UserPromptSubmit)")
    a = ap.parse_args()
    if a.hook:
        sys.stdin.read()  # o evento não é usado: a comparação olha as datas dos arquivos

    if not precisa_gerar():
        if not a.hook:
            print("os HTMLs já estão em dia com o JSON")
        return

    r = subprocess.run([sys.executable, str(GERAR)], cwd=RAIZ, capture_output=True, text=True, timeout=120)
    saida = (r.stdout + r.stderr).strip()
    erros = [l for l in saida.splitlines() if l.startswith("ERRO")]
    if r.returncode == 0:
        msg = ("O JSON do system design mudou, e os HTMLs (geral e aprovado) foram regenerados "
               "automaticamente. Confira as capturas com gerar.py --capturas se a mudança for visual.")
    else:
        msg = ("O JSON do system design mudou, mas a regeneração dos HTMLs falhou: "
               + "; ".join(erros or [saida[-500:]]) + ". Corrija o JSON.")

    if a.hook:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": a.hook, "additionalContext": msg}},
                         ensure_ascii=False))
    else:
        print(msg)
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
