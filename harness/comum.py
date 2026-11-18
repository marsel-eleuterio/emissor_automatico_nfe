"""Caminhos e normalizações usadas pelo harness."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# NFSE_DADOS aponta para outra pasta com a mesma estrutura de data/, ex.: um lote anonimizado.
DADOS = Path(os.environ["NFSE_DADOS"]).resolve() if os.environ.get("NFSE_DADOS") else RAIZ / "data"
RELATORIOS = RAIZ / "reports"


def ler_json(p: Path | str):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def gravar_json(p: Path | str, obj) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def digitos(s) -> str:
    return re.sub(r"\D", "", str(s)) if s is not None else ""


def doc_igual(a, b) -> bool:
    return bool(digitos(a)) and digitos(a).zfill(14 if len(digitos(a)) > 11 else 11) == \
        digitos(b).zfill(14 if len(digitos(b)) > 11 else 11)


def dec(x) -> Decimal | None:
    if x is None or x == "":
        return None
    try:
        if isinstance(x, str) and "," in x:
            x = x.replace(".", "").replace(",", ".")
        return Decimal(str(x)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def norm(s) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços simples."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def similaridade(a, b) -> float:
    return SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio()


def contido(trecho, texto, limiar: float = 0.9) -> bool:
    """O trecho aparece no texto? Tolera pequenas diferenças de grafia."""
    t, x = norm(trecho), norm(texto)
    if not t:
        return False
    if t in x:
        return True
    m = SequenceMatcher(None, t, x, autojunk=False).find_longest_match(0, len(t), 0, len(x))
    if m.size == 0:
        return False
    ini = max(0, m.b - m.a)
    melhor = max(
        SequenceMatcher(None, t, x[ini:ini + len(t) + d], autojunk=False).ratio()
        for d in range(-12, 13, 2)
    )
    return melhor >= limiar


def conta_igual(a, b) -> bool:
    """Compara número de conta só pelos dígitos (ignora traço do dígito verificador)."""
    return bool(digitos(a)) and digitos(a).lstrip("0") == digitos(b).lstrip("0")


def banco_codigo(s) -> str:
    m = re.search(r"\d{3,4}", str(s or ""))
    return m.group(0).lstrip("0") if m else ""
