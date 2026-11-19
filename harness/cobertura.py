"""De onde vem cada campo da nota: do email, do cadastro, de uma regra ou de consulta.

Checa objetivamente se o valor que está na nota aparece no texto do pedido.
Uso: python -I harness/cobertura.py  (grava reports/cobertura_campos.md)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import DADOS, RELATORIOS, contido, digitos, ler_json, norm  # noqa: E402
from compor import brl  # noqa: E402
from comum import dec  # noqa: E402

EMAIL, CAD, REGRA, CONS, NA = "email", "cadastro", "regra", "consulta", "—"


def presente_digitos(valor, texto) -> bool:
    d = digitos(valor)
    return bool(d) and d in digitos(texto).replace(" ", "")


def avaliar_nota(g: dict, texto: str, rotulo_pedido: dict | None) -> dict:
    t = texto
    out = {}
    tom = g["tomador"]
    out["Tomador: CNPJ/CPF"] = EMAIL if presente_digitos(tom["doc"], t) else CONS
    out["Tomador: nome"] = EMAIL if contido(tom["nome"], t, 0.85) else CONS
    out["Tomador: CEP"] = EMAIL if presente_digitos(tom.get("cep"), t) else CONS
    bairro = (tom.get("bairro") or tom.get("endereco", "").split(",")[-1]).replace("(ZONA...", "").strip()
    out["Tomador: bairro"] = EMAIL if bairro and contido(bairro, t, 0.85) else CONS
    out["Valor"] = EMAIL if brl(dec(g["valor_servico"])) in t or digitos(brl(dec(g["valor_servico"]))) in digitos(t) else NA
    prest = g.get("prestador") or g.get("emitente")
    out["Prestador (quem emite)"] = EMAIL if presente_digitos(prest["doc"], t) else "remetente ou assunto"
    if g["tipo"] == "NFS-e":
        desc_rot = ((rotulo_pedido or {}).get("descricao") or {})
        if desc_rot.get("tipo") == "pronta":
            out["Descrição do serviço"] = EMAIL if contido(desc_rot["texto"], g["descricao"]) else "parcial"
        else:
            out["Descrição do serviço"] = "email + cadastro"
        out["Código de serviço"] = EMAIL if g["servico"]["cod_trib_nacional"] in t else (
            "cadastro (pista no email)" if contido(g["servico"]["descricao_codigo"].rstrip("."), t, 0.75) else CAD)
        mi = g["iss"]["municipio_incidencia"]["municipio"]
        out["Município de incidência do ISS"] = (
            REGRA if norm(mi) == norm(prest["municipio"]) else (EMAIL + " + regra" if contido(mi, t) else REGRA))
        conta = g["banco_na_descricao"]["conta"]
        out["Conta bancária no corpo"] = EMAIL if conta and presente_digitos(conta, t) else (CAD if conta else NA)
        out["Valor aprox. de tributos (Lei 12.741)"] = CAD + " (alíquota do mês)"
        out["Texto de dispensa de IRRF"] = (CAD if g["texto_dispensa_irrf"] else NA)
        comp = g["competencia"]
        dd = f"{comp[8:10]}/{comp[5:7]}/{comp[0:4]}"
        out["Competência"] = EMAIL if dd in t else REGRA
    else:
        out["Produto (código, NCM, CFOP)"] = "cadastro (catálogo)"
        out["Quantidade e preço"] = EMAIL
    return out


def main() -> None:
    casos = ler_json(DADOS / "casos.json")
    gab = ler_json(DADOS / "gabarito_notas.json")
    rot = ler_json(DADOS / "rotulos_extracao.json")
    colunas, matriz = [], {}
    for caso in casos:
        texto = (DADOS / caso["input"]).read_text(encoding="utf-8")
        for i, n in enumerate(caso["notas"]):
            pedidos = rot[caso["caso"]]["pedidos"]
            r = avaliar_nota(gab[n["id"]], texto, pedidos[i] if i < len(pedidos) else None)
            colunas.append(n["id"])
            for campo, origem in r.items():
                matriz.setdefault(campo, {})[n["id"]] = origem
    linhas = ["# De onde vem cada campo da nota", "",
              "Checagem automática: o valor que está na nota aparece no texto do pedido?", "",
              "| Campo | " + " | ".join(colunas) + " |", "| --- |" + " --- |" * len(colunas)]
    for campo, por_nota in matriz.items():
        linhas.append(f"| {campo} | " + " | ".join(por_nota.get(c, NA) for c in colunas) + " |")
    RELATORIOS.mkdir(exist_ok=True)
    nome_arq = "cobertura_campos.md" if DADOS.name == "data" else f"cobertura_campos_{DADOS.name}.md"
    (RELATORIOS / nome_arq).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))


if __name__ == "__main__":
    main()
