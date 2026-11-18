"""Regras determinísticas: cadastro + extração -> campos da nota.

Aqui ficam as decisões fiscais. O LLM nunca escolhe código, alíquota ou município de incidência.
"""
from __future__ import annotations

import re
from decimal import Decimal

from comum import contido, dec, digitos, norm

TEXTO_IRRF = (
    "Com Base na IN RFB nº 765/2007, c/c os artigos 181 a 184 do RIR/2018, pessoa jurídica optante "
    "pelo Simples Nacional está dispensada da retenção de IRRF (DARF - 8045)."
)

# LC 116/2003, art. 3º: serviços em que o ISS é devido no local da prestação, não no estabelecimento.
# Lista PARCIAL: só o que apareceu nos exemplos. Completar com o art. 3º antes do piloto.
ITENS_ISS_NO_LOCAL = {"12"}          # item 12 inteiro...
ITENS_ISS_NO_LOCAL_EXCETO = {"12.13"}  # ...menos o subitem 12.13


def brl(v: Decimal) -> str:
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def identificar_cliente(extracao: dict, remetente: str | None, assunto: str | None, cadastro: dict):
    """Cliente pelo remetente autorizado; se o remetente for da equipe, pelo assunto ou pelo nome citado."""
    rem = (remetente or "").lower()
    for c in cadastro["clientes"]:
        if rem and rem in [r.lower() for r in c.get("remetentes_autorizados", [])]:
            return c, "remetente autorizado"
    pistas = norm(f"{assunto or ''} {extracao.get('cliente_mencionado') or ''}")
    for c in cadastro["clientes"]:
        if any(norm(k) in pistas for k in c.get("palavras_chave", [])):
            origem = "equipe repassou; cliente pelo assunto" if rem in cadastro.get("internos", []) \
                else "nome citado (remetente fora da lista)"
            return c, origem
    return None, "não identificado"


def municipio_incidencia(cod_nacional: str, local: dict | None, cliente: dict):
    item, subitem = cod_nacional[:2], cod_nacional[:5]
    if item in ITENS_ISS_NO_LOCAL and subitem not in ITENS_ISS_NO_LOCAL_EXCETO and local and local.get("municipio"):
        return {"municipio": local["municipio"], "uf": local.get("uf")}, "local do serviço (LC 116, art. 3º)"
    return {"municipio": cliente["municipio"], "uf": cliente["uf"]}, "estabelecimento do prestador"


def preencher_lacunas(texto: str, cliente: dict) -> tuple[str, bool]:
    padrao = cliente.get("descricao_padrao")
    if not padrao or "[" not in texto:
        return texto, False
    return re.sub(r"\s*\[[^\]]+\]", " " + padrao, texto, count=1), True


def compor_nfse(pedido: dict, cliente: dict) -> dict:
    cod = cliente["codigos_servico"][0]
    incid, motivo = municipio_incidencia(cod["nacional"], pedido.get("local_prestacao"), cliente)
    valor = dec(pedido.get("valor"))
    aliq = Decimal(cliente["aliquota_lei_12741_pct"])
    lei_valor = (valor * aliq / 100).quantize(Decimal("0.01")) if valor is not None else None

    d = pedido.get("descricao") or {}
    base = d.get("texto") or ""
    preenchida = False
    if d.get("tipo") == "modelo_com_lacunas":
        base, preenchida = preencher_lacunas(base, cliente)

    partes = [base] if base else []
    ref = pedido.get("periodo_ou_referencia")
    datas_ref = re.findall(r"\d{2}/\d{2}(?:/\d{2,4})?", ref or "")
    ja_tem = (datas_ref and all(d in base for d in datas_ref)) or contido(ref, base, 0.95)
    if ref and not ja_tem:
        partes.append(f"Referente a: {ref}.")
    if valor is not None and brl(valor) not in base:
        partes.append(f"Valor: R$ {brl(valor)}.")
    banco = pedido.get("dados_bancarios") or (cliente.get("dados_bancarios") if pedido.get("exige_dados_bancarios_no_corpo") else None)
    if banco:
        txt = f"Dados bancários para depósito: Banco {banco['banco']} Agência {banco['agencia']} Conta {banco['conta']}"
        if banco.get("pix"):
            txt += f" PIX {banco['pix']}"
        partes.append(txt + ".")
    if lei_valor is not None:
        anexo = cliente.get("anexo_simples", "III")
        partes.append(
            f"Valor aproximado dos tributos (Lei 12.741/12 e Decreto 8.264/14): R$ {brl(lei_valor)} "
            f"({str(aliq).replace('.', ',')}% - Anexo {anexo} do Simples Nacional)."
        )
    if cliente.get("texto_dispensa_irrf"):
        partes.append(TEXTO_IRRF)

    return {
        "tipo": "NFS-e",
        "prestador_doc": cliente["cnpj"],
        "tomador_doc": pedido["tomador"].get("cnpj_cpf"),
        "valor_servico": valor,
        "cod_trib_nacional": cod["nacional"],
        "cod_trib_municipal_cadastro": cod.get("municipal"),
        "municipio_incidencia": incid,
        "motivo_incidencia": motivo,
        "descricao_base": base,
        "descricao_preenchida_pelo_cadastro": preenchida,
        "descricao": " ".join(partes),
        "banco": banco,
        "lei_12741_valor": lei_valor,
        "texto_dispensa_irrf": bool(cliente.get("texto_dispensa_irrf")),
        "iss_retido": False,
        "competencia": "data de emissão (prática do escritório, a confirmar)",
    }


def casar_produto(descricao: str, catalogo: list[dict]):
    """Escolhe o item do catálogo mais parecido (sobreposição de palavras e números)."""
    alvo = set(norm(descricao).split())
    melhor, nota = None, 0.0
    for item in catalogo:
        toks = set(norm(item["descricao"]).split())
        s = len(alvo & toks) / max(1, len(alvo))
        if s > nota:
            melhor, nota = item, s
    return melhor, round(nota, 2)


def compor_nfe(pedido: dict, cliente: dict) -> dict:
    itens = []
    for it in pedido.get("itens_produto") or []:
        prod, conf = casar_produto(it["descricao"], cliente.get("catalogo", []))
        itens.append({
            "pedido": it["descricao"],
            "codigo": prod["codigo"] if prod else None,
            "ncm": prod["ncm"] if prod else None,
            "cfop": prod["cfop"] if prod else None,
            "confianca_catalogo": conf,
            "quantidade": it.get("quantidade"),
            "valor_unitario": dec(it.get("valor_unitario")),
        })
    total = sum((i["valor_unitario"] or 0) * Decimal(str(i["quantidade"] or 0)) for i in itens) if itens else dec(pedido.get("valor"))
    return {
        "tipo": "NF-e",
        "prestador_doc": cliente["cnpj"],
        "tomador_doc": pedido["tomador"].get("cnpj_cpf"),
        "cep_tomador": digitos(pedido["tomador"].get("cep")),
        "itens": itens,
        "valor_servico": dec(total),
    }


def compor(pedido: dict, cliente: dict) -> dict:
    if pedido.get("tipo_documento") == "NF-e" or cliente.get("documento") == "NF-e":
        return compor_nfe(pedido, cliente)
    return compor_nfse(pedido, cliente)
