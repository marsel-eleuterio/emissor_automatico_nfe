"""Gera um lote anonimizado em data_anon/ a partir de data/.

Lê os pares (original, substituto) de data/mapa_anonimizacao.json (que fica fora do git,
junto com os dados reais) para que nenhum dado pessoal apareça no código-fonte.

Uso:
  python -I harness/anonimizar.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import RAIZ, ler_json  # noqa: E402

ORIGEM = RAIZ / "data"
DESTINO = RAIZ / "data_anon"


def carregar_trocas(origem: Path = ORIGEM) -> list[tuple[str, str]]:
    mapa = origem / "mapa_anonimizacao.json"
    if not mapa.exists():
        raise FileNotFoundError(f"Arquivo de mapeamento não encontrado: {mapa}")
    return [(orig, subst) for orig, subst in ler_json(mapa)]


def anonimizar_texto(texto: str, trocas: list[tuple[str, str]]) -> str:
    for orig, subst in trocas:
        texto = texto.replace(orig, subst)
    return texto


def gerar_lote_anonimizado(origem: Path = ORIGEM, destino: Path = DESTINO) -> Path:
    trocas = carregar_trocas(origem)
    if destino.exists():
        shutil.rmtree(destino)
    for arq in origem.rglob("*"):
        if arq.is_dir() or arq.name == "mapa_anonimizacao.json":
            continue
        rel = arq.relative_to(origem)
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        conteudo = arq.read_text(encoding="utf-8")
        alvo.write_text(anonimizar_texto(conteudo, trocas), encoding="utf-8")
    return destino


if __name__ == "__main__":
    d = gerar_lote_anonimizado()
    print(f"Lote anonimizado gerado em {d.relative_to(RAIZ)}/")
