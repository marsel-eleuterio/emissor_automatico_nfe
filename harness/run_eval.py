"""Roda um extrator nos casos, compara com rótulos e gabarito e grava o relatório.

Exemplos:
  python -I harness/run_eval.py --extrator oraculo   # testa só as regras de composição
  python -I harness/run_eval.py --extrator regex     # linha de base sem LLM
  ANTHROPIC_API_KEY=... python -I harness/run_eval.py --extrator claude --modelo claude-haiku-5-5
  python -I harness/run_eval.py --extrator ollama --modelo qwen3.5:9b
  python -I harness/run_eval.py --extrator claude-code --modelo haiku      # pelo seu plano Pro/Max
  NFSE_DADOS=data_anon NFSE_DADOS_ANONIMIZADOS=1 GEMINI_API_KEY=... \\
    python -I harness/run_eval.py --extrator openai --provedor gemini --modelo gemini-3.8-flash
  python -I harness/run_eval.py --extrator replay --replay reports/saidas_claude_....json
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from avaliar import checar_caso_extracao, checar_ponta_a_ponta, regra_competencia  # noqa: E402
from comum import DADOS, RAIZ, RELATORIOS, gravar_json, ler_json  # noqa: E402
from extratores import cabecalho, criar  # noqa: E402


def _fmt(x, n=90):
    s = "—" if x is None else str(x)
    return s if len(s) <= n else s[: n - 1] + "…"


def tabela(contagem: dict) -> list[str]:
    linhas = ["| Campo | Acertos | Total |", "| --- | --- | --- |"]
    for campo, (ok, tot) in contagem.items():
        linhas.append(f"| {campo} | {ok} | {tot} |")
    return linhas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extrator", default="regex",
                    choices=["oraculo", "regex", "claude", "claude-code", "ollama", "openai", "replay"])
    ap.add_argument("--modelo")
    ap.add_argument("--provedor", help="com --extrator openai: gemini, groq, github ou ollama")
    ap.add_argument("--replay")
    ap.add_argument("--casos", help="lista separada por vírgula, ex.: A,C")
    args = ap.parse_args()

    casos = ler_json(DADOS / "casos.json")
    rotulos = ler_json(DADOS / "rotulos_extracao.json")
    cadastro = ler_json(DADOS / "cadastro_rascunho.json")
    gabarito = ler_json(DADOS / "gabarito_notas.json")
    ext = criar(args.extrator, rotulos, cadastro, args.modelo, args.replay, args.provedor)
    if args.casos:
        casos = [c for c in casos if c["caso"] in args.casos.split(",")]

    ts = time.strftime("%Y%m%d-%H%M%S")
    saidas, metas, linhas_csv = {}, {}, []
    cont_ext, cont_e2e = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    erros = []

    for caso in casos:
        cid = caso["caso"]
        texto = (DADOS / caso["input"]).read_text(encoding="utf-8")
        meta = {**cabecalho(texto), "recebido_em": caso["recebido_em"]}
        try:
            saida = ext.extrair(cid, texto, meta)
        except Exception as exc:  # um caso com erro não derruba a rodada
            erros.append(f"- **{cid}**: falha do extrator: {exc}")
            saida = {"pedidos": []}
        saidas[cid], metas[cid] = saida, meta

        for campo, ok, esp, obt in checar_caso_extracao(saida, rotulos[cid]):
            cont_ext[campo][0] += ok
            cont_ext[campo][1] += 1
            linhas_csv.append([ext.nome, cid, "extracao", campo, ok, esp, obt])
            if not ok:
                erros.append(f"- **{cid}** · extração · `{campo}`: esperado {_fmt(esp)}; veio {_fmt(obt)}")

        notas = [gabarito[n["id"]] for n in caso["notas"]]
        linhas, _ = checar_ponta_a_ponta(saida, meta, cadastro, notas)
        for campo, ok, esp, obt in linhas:
            cont_e2e[campo][0] += ok
            cont_e2e[campo][1] += 1
            linhas_csv.append([ext.nome, cid, "nota", campo, ok, esp, obt])
            if not ok:
                erros.append(f"- **{cid}** · nota · `{campo}`: esperado {_fmt(esp)}; veio {_fmt(obt)}")

    soma = lambda c: (sum(v[0] for v in c.values()), sum(v[1] for v in c.values()))  # noqa: E731
    se, te = soma(cont_ext)
    sn, tn = soma(cont_e2e)
    comp = regra_competencia(gabarito)

    md = [
        f"# Avaliação · extrator `{ext.nome}` · {ts}",
        "",
        f"Casos: {', '.join(saidas)}. Extração comparada com `{DADOS.name}/rotulos_extracao.json`; "
        f"nota composta (extração + cadastro + regras) comparada com `{DADOS.name}/gabarito_notas.json`.",
        "",
        "| Etapa | Acertos | Total | % |",
        "| --- | --- | --- | --- |",
        f"| Extração (campos) | {se} | {te} | {100 * se / max(te, 1):.0f}% |",
        f"| Nota composta (campos) | {sn} | {tn} | {100 * sn / max(tn, 1):.0f}% |",
        "",
        "## Extração por campo",
        *tabela(cont_ext),
        "",
        "## Nota composta por campo",
        *tabela(cont_e2e),
        "",
        "## Divergências",
        *(erros or ["Nenhuma."]),
        "",
        "## Regra de competência (independe do extrator)",
        f"Competência igual à data de emissão em {sum(c[1] for c in comp)} de {len(comp)} NFS-e.",
    ]
    if any("latencia_s" in m for m in metas.values()):
        md += ["", "## Custo e tempo", "| Caso | Latência (s) | Tokens entrada | Tokens saída |", "| --- | --- | --- | --- |"]
        for cid, m in metas.items():
            tk = m.get("tokens", {})
            md.append(f"| {cid} | {m.get('latencia_s', '—')} | {tk.get('entrada', '—')} | {tk.get('saida', '—')} |")

    # Lote fora de data/ (ex.: anonimizado) entra no nome, para o comparativo não misturar lotes.
    lote = "" if DADOS == RAIZ / "data" else f"@{DADOS.name}"
    nome = re.sub(r"[^a-z0-9.-]+", "_", (ext.nome + lote).lower()).strip("_")
    RELATORIOS.mkdir(exist_ok=True)
    (RELATORIOS / f"avaliacao_{nome}_{ts}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with open(RELATORIOS / f"avaliacao_{nome}_{ts}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["extrator", "caso", "etapa", "campo", "ok", "esperado", "obtido"])
        w.writerows(linhas_csv)
    gravar_json(RELATORIOS / f"saidas_{nome}_{ts}.json", {"extrator": ext.nome, "saidas": saidas, "meta": metas})
    print(f"Extração: {se}/{te} · Nota composta: {sn}/{tn} · relatório em reports/avaliacao_{nome}_{ts}.md")


if __name__ == "__main__":
    main()
