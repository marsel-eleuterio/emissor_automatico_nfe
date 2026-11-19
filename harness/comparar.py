"""Junta os CSVs de várias rodadas numa tabela modelo × campo.

Uso: python -I harness/comparar.py   (grava reports/comparativo.md)
Se o mesmo extrator rodou mais de uma vez, vale a rodada mais recente.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import RELATORIOS  # noqa: E402

CRITICOS = {"tomador_doc", "valor", "local_prestacao", "descricao_texto", "municipio_incidencia", "descricao_nucleo"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", help="filtra relatórios de um lote específico, ex.: data_lote2")
    args = ap.parse_args()

    ultimas: dict[str, Path] = {}
    for p in sorted(RELATORIOS.glob("avaliacao_*.csv")):
        if args.lote:
            if f"_{args.lote}_" not in p.name:
                continue
        else:
            if "_data_lote2_" in p.name:
                continue
        with open(p, encoding="utf-8") as f:
            primeira = next(csv.DictReader(f), None)
        if primeira:
            ultimas[primeira["extrator"]] = p  # sorted por data: fica a mais recente

    acertos = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for ext, p in ultimas.items():
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                chave = f"{r['etapa']}: {r['campo']}"
                acertos[chave][ext][0] += r["ok"] == "True"
                acertos[chave][ext][1] += 1

    exts = list(ultimas)
    linhas = ["# Comparativo de extratores", "",
              "Rodada mais recente de cada extrator. Campos críticos marcados com *.", "",
              "| Campo | " + " | ".join(f"`{e}`" for e in exts) + " |",
              "| --- |" + " --- |" * len(exts)]
    for chave in sorted(acertos):
        marca = " *" if chave.split(": ")[1] in CRITICOS else ""
        celulas = []
        for e in exts:
            ok, tot = acertos[chave].get(e, [0, 0])
            celulas.append(f"{ok}/{tot}" if tot else "—")
        linhas.append(f"| {chave}{marca} | " + " | ".join(celulas) + " |")
    totais = []
    for e in exts:
        ok = sum(v[e][0] for v in acertos.values() if e in v)
        tot = sum(v[e][1] for v in acertos.values() if e in v)
        totais.append(f"**{ok}/{tot}**")
    linhas.append("| **Total** | " + " | ".join(totais) + " |")
    nome_out = f"comparativo_{args.lote}.md" if args.lote else "comparativo.md"
    (RELATORIOS / nome_out).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
