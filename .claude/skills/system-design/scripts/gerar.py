#!/usr/bin/env python3
"""Gera o system design do AutoSeguro (HTML animado) a partir do JSON de dados.

Do mesmo JSON saem duas versões, que existem em paralelo:
    - geral: tudo o que está no JSON (decidido, proposto e futuro), aprovados e não aprovados;
    - aprovado: só os nós com status "decidido" (ADR aceito) e as conexões e cenas entre eles.

Uso, a partir da raiz do repositório:
    python3 .claude/skills/system-design/scripts/gerar.py                # valida e gera as duas versões
    python3 .claude/skills/system-design/scripts/gerar.py --so-validar   # só valida
    python3 .claude/skills/system-design/scripts/gerar.py --capturas tmp/system-design
        # gera e salva uma captura PNG por cena em <pasta>/geral e <pasta>/aprovado
        # (precisa de Chrome ou Chromium)

Erros interrompem a geração. Avisos não interrompem, mas devem ser lidos e resolvidos
ou justificados.

Só usa a biblioteca padrão do Python.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
RAIZ = SKILL.parents[2]
TEMPLATE = SKILL / "assets" / "template.html"
DADOS_PADRAO = RAIZ / "system-design" / "autoseguro-system-design.json"
SAIDA_GERAL = RAIZ / "system-design" / "autoseguro-system-design-geral.html"
SAIDA_APROVADO = RAIZ / "system-design" / "autoseguro-system-design-aprovado.html"

LARGURA, ALTURA = 1600, 900
TIPOS = {"phone", "dot", "lb", "app", "ext", "db", "worker", "bucket", "source"}
STATUS = {"decidido", "proposto", "futuro"}
CORES_TAG = {"green", "muted", "blue", "cyan", "violet", "text"}
# Faixas reservadas: título, legenda, subtítulo + legenda em pílula + selo
RESERVADAS = {
    "título": (500, 20, 1100, 95),
    "legenda": (40, 110, 270, 250),
    "rodapé": (0, 765, LARGURA, ALTURA),
}


def caixa(n):
    """Retângulo aproximado (x0, y0, x1, y1) ocupado pelo nó, incluindo rótulos externos."""
    x, y, t = n["x"], n["y"], n["type"]
    if t == "phone":
        return (x - 17, y - 27, x + 34 + 9 * len(n.get("label", "")), y + 27)
    if t == "dot":
        return (x - 6, y - 6, x + 6, y + 6)
    if t == "app":
        w, h = 120, 64
    elif t == "db":
        w, h = 110, 102
    elif t == "worker":
        w, h = n.get("w", 130), 56
    elif t == "bucket":
        w, h = 120, 62
    elif t == "source":
        return (x - 75, y - 25, x + 75, y + 50)  # inclui a tag abaixo
    elif t == "lb":
        w, h = n.get("w", 190), n.get("h", 40)
    else:  # ext
        w, h = n.get("w", 96), n.get("h", 64)
    return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def sobrepoe(a, b, folga=6):
    return a[0] < b[2] + folga and b[0] < a[2] + folga and a[1] < b[3] + folga and b[1] < a[3] + folga


def arquivos_md_do_repo():
    nomes = set()
    for p in RAIZ.rglob("*.md"):
        partes = p.relative_to(RAIZ).parts
        if partes[0] in {".claude", "tmp", ".venv", "node_modules"} or "originais" in partes:
            continue
        nomes.add(p.stem)
    return nomes


def validar(d):
    erros, avisos = [], []
    nodes, edges, scenes = d.get("nodes", {}), d.get("edges", {}), d.get("scenes", [])
    meta = d.get("meta", {})

    for campo in ("titulo", "selo", "atualizado"):
        if not meta.get(campo):
            erros.append(f"meta.{campo} ausente")

    for nid, n in nodes.items():
        if n.get("type") not in TIPOS:
            erros.append(f"nó {nid}: tipo '{n.get('type')}' desconhecido (use {sorted(TIPOS)})")
            continue
        if n["type"] != "dot" and not n.get("label"):
            erros.append(f"nó {nid}: sem label")
        if n.get("status") not in STATUS:
            erros.append(f"nó {nid}: status '{n.get('status')}' inválido (use {sorted(STATUS)})")
        if n.get("status") == "futuro" and not n.get("future"):
            avisos.append(f"nó {nid}: status futuro mas sem \"future\": true (não fica tracejado)")
        if n.get("future") and n.get("status") != "futuro":
            avisos.append(f"nó {nid}: tracejado (future) mas status '{n.get('status')}'")
        if n.get("tagColor") and n["tagColor"] not in CORES_TAG:
            erros.append(f"nó {nid}: tagColor '{n['tagColor']}' inválida (use {sorted(CORES_TAG)})")
        x0, y0, x1, y1 = caixa(n)
        if x0 < 0 or y0 < 0 or x1 > LARGURA or y1 > ALTURA:
            erros.append(f"nó {nid}: sai da área de {LARGURA}x{ALTURA}")
        for nome, r in RESERVADAS.items():
            if sobrepoe((x0, y0, x1, y1), r, folga=0):
                avisos.append(f"nó {nid}: invade a faixa reservada do {nome}")
        if n["type"] != "dot" and not n.get("fonte"):
            avisos.append(f"nó {nid}: sem fonte (componente proposto sem documento que o justifique)")
        if n.get("status") == "decidido" and not re.search(r"\[\[adr-\d{4}-", n.get("fonte") or "", re.I):
            avisos.append(f"nó {nid}: status decidido sem citar um ADR em fonte")

    ids = [k for k in nodes if nodes[k].get("type") in TIPOS]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if sobrepoe(caixa(nodes[a]), caixa(nodes[b])):
                avisos.append(f"nós {a} e {b} se sobrepõem (ou ficam a menos de 6 px)")

    def perto_de_algum(p):
        return any(perto(n, p) for n in nodes.values())

    for eid, e in edges.items():
        pts = e.get("pts", [])
        if len(pts) < 2:
            erros.append(f"conexão {eid}: precisa de pelo menos 2 pontos")
            continue
        if e.get("decorative"):
            continue
        for p in (pts[0], pts[-1]):
            if not perto_de_algum(p):
                avisos.append(f"conexão {eid}: ponta {p} longe de qualquer nó (não vai acender nas cenas)")

    usados = set()
    for i, s in enumerate(scenes):
        for campo in ("title", "sub"):
            if not (isinstance(s.get(campo), list) and len(s[campo]) == 2):
                erros.append(f"cena {i}: {campo} deve ser [texto, texto em destaque]")
        if not s.get("cap"):
            erros.append(f"cena {i}: sem cap (legenda em pílula)")
        elif len(s["cap"]) > 40:
            avisos.append(f"cena {i}: cap com {len(s['cap'])} caracteres (acima de 40 fica longa)")
        lista = list(nodes) if s.get("nodes") == "*" else s.get("nodes", [])
        if s.get("nodes") != "*":
            usados.update(lista)
        for nid in lista:
            if nid not in nodes:
                erros.append(f"cena {i}: nó '{nid}' não existe")
        for eid in s.get("packets", []):
            if eid not in edges:
                erros.append(f"cena {i}: conexão '{eid}' não existe")
    for nid in nodes:
        if nid not in usados and nodes[nid].get("type") != "dot":
            avisos.append(f"nó {nid}: só aparece nas cenas de visão geral")

    documentos = arquivos_md_do_repo()
    textos = [n.get("fonte") or "" for n in nodes.values()] + meta.get("documentos_lidos", [])
    for alvo in sorted({m.split("|")[0].split("#")[0] for t in textos for m in re.findall(r"\[\[([^\]]+)\]\]", t)}):
        if alvo not in documentos:
            avisos.append(f"fonte [[{alvo}]] não corresponde a nenhum documento do repositório")

    return erros, avisos


def perto(n, p):
    return abs(n["x"] - p[0]) <= 80 and abs(n["y"] - p[1]) <= 56


def versao_aprovada(d):
    """Filtra o JSON para a versão aprovada: só nós decididos (ADR aceito)."""
    nodes = {k: v for k, v in d["nodes"].items() if v.get("status") == "decidido"}

    def liga(e):
        pts = e["pts"]
        return all(any(perto(n, p) for n in nodes.values()) for p in (pts[0], pts[-1]))

    edges = {k: e for k, e in d["edges"].items() if liga(e)}
    adrs = sorted({m for n in nodes.values() for m in re.findall(r"\[\[adr-(\d{4})-", n.get("fonte") or "", re.I)})
    data = d["meta"]["atualizado"]
    meta = dict(d["meta"], titulo=d["meta"]["titulo"] + " · aprovado")

    if not nodes:
        meta["selo"] = f"aprovado · nenhum ADR aceito · {data}"
        cena = {"title": ["AutoSeguro, ", "aprovado"], "sub": ["nada aprovado ", "ainda"],
                "cap": "veja a versão geral no outro diagrama", "nodes": [], "packets": []}
        return {"meta": meta, "nodes": {}, "edges": {}, "scenes": [cena]}

    def _faixa(nums):
        """ADR-0001, ADR-0001 a 0003 (só se contíguos) ou ADR-0001, 0003 e 0005."""
        if len(nums) == 1:
            return f"ADR-{nums[0]}"
        if [int(n) for n in nums] == list(range(int(nums[0]), int(nums[-1]) + 1)):
            return f"ADR-{nums[0]} a {nums[-1]}"
        return f"ADR-{', '.join(nums[:-1])} e {nums[-1]}"

    faixa = _faixa(adrs)
    meta["selo"] = f"aprovado · {faixa} · {data}"
    cenas = []
    for i, s in enumerate(d["scenes"]):
        geral = s.get("nodes") == "*"
        ns = "*" if geral else [n for n in s.get("nodes", []) if n in nodes]
        ps = [e for e in s.get("packets", []) if e in edges]
        if geral or ns:
            cenas.append(dict(s, nodes=ns, packets=ps))
    if cenas:
        cenas[-1] = dict(cenas[-1], cap="só o que tem ADR aceito")
    return {"meta": meta, "nodes": nodes, "edges": edges, "scenes": cenas}


def gerar(d, saida):
    template = TEMPLATE.read_text(encoding="utf-8")
    bloco = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    if "/*__DADOS__*/" not in template or "__TITULO__" not in template:
        sys.exit("template sem os marcadores /*__DADOS__*/ e __TITULO__")
    out = template.replace("/*__DADOS__*/", bloco).replace("__TITULO__", html.escape(d["meta"]["titulo"]))
    saida.write_text(out, encoding="utf-8")


def capturas(saida, pasta, n_cenas):
    chrome = next((shutil.which(b) for b in ("google-chrome", "chromium", "chromium-browser") if shutil.which(b)), None)
    if not chrome:
        print("aviso: Chrome/Chromium não encontrado; capturas não geradas")
        return
    pasta.mkdir(parents=True, exist_ok=True)
    for i in range(n_cenas):
        png = pasta / f"cena-{i:02d}.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--window-size=1600,952", "--virtual-time-budget=5000",
                        f"--screenshot={png}", f"{saida.as_uri()}?cena={i}&pausado&captura"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
        print(f"captura: {png}")


SUBDIR = RAIZ / "system-design" / "subsistemas"


def carregar_subsistemas():
    """Lê cada subpágina de system-design/subsistemas/<id>.json, em ordem alfabética."""
    if not SUBDIR.exists():
        return {}
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(SUBDIR.glob("*.json"))}


def com_links(dados, variante, detalhes):
    """Cópia do diagrama em que os nós com 'detalhe' apontam para a subpágina da mesma variante."""
    out = dict(dados, nodes={k: dict(v) for k, v in dados["nodes"].items()})
    for k, n in out["nodes"].items():
        det = n.get("detalhe")
        if det:
            assert det in detalhes, f"nó {k}: subpágina '{det}' não existe em system-design/subsistemas/"
            n["link"] = f"subsistemas/{det}-{variante}.html"
    return out


def com_voltar(dados, variante):
    out = dict(dados, meta=dict(dados["meta"]))
    out["meta"]["voltar"] = {"href": f"../autoseguro-system-design-{variante}.html", "rotulo": "visão geral"}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dados", type=Path, default=DADOS_PADRAO)
    ap.add_argument("--saida-geral", type=Path, default=SAIDA_GERAL)
    ap.add_argument("--saida-aprovado", type=Path, default=SAIDA_APROVADO)
    ap.add_argument("--so-validar", action="store_true")
    ap.add_argument("--capturas", type=Path, help="pasta para salvar uma captura PNG por cena de cada página")
    a = ap.parse_args()

    macro = json.loads(a.dados.read_text(encoding="utf-8"))
    subs = carregar_subsistemas()
    paginas = [("macro", macro)] + list(subs.items())

    erros_total, avisos_total = [], []
    for nome, d in paginas:
        erros, avisos = validar(d)
        erros_total += [f"{nome}: {e}" for e in erros]
        avisos_total += [f"{nome}: {w}" for w in avisos]
    for m in avisos_total:
        print(f"aviso: {m}")
    for m in erros_total:
        print(f"ERRO: {m}")
    print(f"{len(paginas)} página(s) · {len(erros_total)} erro(s), {len(avisos_total)} aviso(s)")
    if erros_total:
        sys.exit(1)
    if a.so_validar:
        return

    detalhes = set(subs)
    saidas_macro = {"geral": a.saida_geral, "aprovado": a.saida_aprovado}
    for variante in ("geral", "aprovado"):
        base = macro if variante == "geral" else versao_aprovada(macro)
        dados = com_links(base, variante, detalhes)
        gerar(dados, saidas_macro[variante].resolve())
        print(f"gerado (macro, {variante}): {saidas_macro[variante]} · {len(dados['nodes'])} nós")
        if a.capturas:
            capturas(saidas_macro[variante].resolve(), (a.capturas / "macro" / variante).resolve(), len(dados["scenes"]))

    for sid, sd in subs.items():
        for variante in ("geral", "aprovado"):
            base = sd if variante == "geral" else versao_aprovada(sd)
            dados = com_voltar(base, variante)
            saida = SUBDIR / f"{sid}-{variante}.html"
            gerar(dados, saida.resolve())
            print(f"gerado ({sid}, {variante}): {saida} · {len(dados['nodes'])} nós")
            if a.capturas:
                capturas(saida.resolve(), (a.capturas / sid / variante).resolve(), len(dados["scenes"]))


if __name__ == "__main__":
    main()
