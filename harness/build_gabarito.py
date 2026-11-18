"""Monta data/gabarito_notas.json a partir dos PDFs das notas (DANFSe) e do gabarito manual.

Uso: python -I harness/build_gabarito.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import DADOS, gravar_json, ler_json  # noqa: E402
from parse_danfse import parse_danfse, pdf_text  # noqa: E402


def main() -> None:
    casos = ler_json(DADOS / "casos.json")
    manual = ler_json(DADOS / "gabarito_manual.json")
    saida = {}
    for caso in casos:
        for nota in caso["notas"]:
            if nota.get("manual"):
                g = dict(manual[nota["id"]])
            else:
                g = parse_danfse(pdf_text((DADOS / nota["pdf"]).resolve()))
            g["caso"] = caso["caso"]
            g["nome_original"] = nota.get("nome_original")
            saida[nota["id"]] = g
    gravar_json(DADOS / "gabarito_notas.json", saida)
    print(f"{len(saida)} notas no gabarito: {', '.join(saida)}")


if __name__ == "__main__":
    main()
