"""Compara extração com os rótulos e a nota composta com o gabarito."""
from __future__ import annotations

from comum import banco_codigo, conta_igual, contido, dec, doc_igual, norm, similaridade
from compor import compor, identificar_cliente


def _local(p):
    loc = p.get("local_prestacao") or {}
    return (norm(loc.get("municipio")), (loc.get("uf") or "").upper()) if loc.get("municipio") else None


def _banco(p):
    return p.get("dados_bancarios") or {}


def checar_pedido(e: dict, r: dict) -> list[tuple[str, bool, object, object]]:
    """(campo, ok, esperado, obtido) para um pedido extraído contra o rótulo."""
    out = []
    out.append(("tipo_documento", e.get("tipo_documento") == r.get("tipo_documento"), r.get("tipo_documento"), e.get("tipo_documento")))
    te, tr = (e.get("tomador") or {}).get("cnpj_cpf"), r["tomador"].get("cnpj_cpf")
    out.append(("tomador_doc", doc_igual(te, tr) if tr else not te, tr, te))
    out.append(("valor", dec(e.get("valor")) == dec(r.get("valor")), r.get("valor"), e.get("valor")))
    de, dr = e.get("descricao") or {}, r.get("descricao") or {}
    out.append(("descricao_tipo", de.get("tipo") == dr.get("tipo"), dr.get("tipo"), de.get("tipo")))
    if dr.get("texto"):
        ok = similaridade(de.get("texto"), dr.get("texto")) >= 0.9
    else:
        ok = not de.get("texto")
    out.append(("descricao_texto", ok, dr.get("texto"), de.get("texto")))
    out.append(("local_prestacao", _local(e) == _local(r), _local(r), _local(e)))
    be, br = _banco(e), _banco(r)
    if br:
        ok_c = conta_igual(be.get("conta"), br.get("conta"))
        ok_b = banco_codigo(be.get("banco")) == banco_codigo(br.get("banco"))
    else:
        ok_c = ok_b = not be
    out.append(("banco_conta", ok_c, br.get("conta"), be.get("conta")))
    out.append(("banco_codigo", ok_b, br.get("banco"), be.get("banco")))
    out.append(("vencimento", (e.get("vencimento") or None) == (r.get("vencimento") or None), r.get("vencimento"), e.get("vencimento")))
    if r.get("itens_produto"):
        ie, ir = e.get("itens_produto") or [], r["itens_produto"]
        ok = len(ie) == len(ir) and all(
            dec(a.get("valor_unitario")) == dec(b.get("valor_unitario")) and float(a.get("quantidade") or 0) == float(b.get("quantidade") or 0)
            for a, b in zip(ie, ir)
        )
        out.append(("itens_produto", ok, ir, ie))
    return out


def checar_caso_extracao(ext: dict, rot: dict) -> list[tuple]:
    linhas = [("n_pedidos", len(ext.get("pedidos", [])) == len(rot["pedidos"]), len(rot["pedidos"]), len(ext.get("pedidos", [])))]
    pe = (ext.get("prazo_envio") or "")[:10] or None
    pr = (rot.get("prazo_envio") or "")[:10] or None
    linhas.append(("prazo_envio", pe == pr, pr, pe))
    for i, r in enumerate(rot["pedidos"]):
        if i < len(ext.get("pedidos", [])):
            linhas += [(f"{c}", ok, esp, obt) for c, ok, esp, obt in checar_pedido(ext["pedidos"][i], r)]
        else:
            linhas += [(c, False, esp, None) for c, _, esp, _ in checar_pedido(r, r)]
    return linhas


def checar_ponta_a_ponta(ext: dict, meta: dict, cadastro: dict, notas_gab: list[dict]) -> tuple[list[tuple], list[dict]]:
    cliente, origem = identificar_cliente(ext, meta.get("remetente"), meta.get("assunto"), cadastro)
    linhas, compostas = [], []
    for i, g in enumerate(notas_gab):
        doc_prest = (g.get("prestador") or g.get("emitente"))["doc"]
        linhas.append(("cliente_identificado", bool(cliente) and doc_igual(cliente["cnpj"], doc_prest),
                       doc_prest, cliente["cnpj"] if cliente else origem))
        pedidos = ext.get("pedidos", [])
        if not cliente or i >= len(pedidos):
            linhas.append(("nota_composta", False, g["numero"], None))
            continue
        c = compor(pedidos[i], cliente)
        compostas.append(c)
        linhas.append(("tomador_doc", doc_igual(c["tomador_doc"], g["tomador"]["doc"]), g["tomador"]["doc"], c["tomador_doc"]))
        linhas.append(("valor", c["valor_servico"] == dec(g["valor_servico"]), g["valor_servico"], c["valor_servico"]))
        if g["tipo"] == "NFS-e":
            linhas.append(("cod_trib_nacional", c.get("cod_trib_nacional") == g["servico"]["cod_trib_nacional"],
                           g["servico"]["cod_trib_nacional"], c.get("cod_trib_nacional")))
            mi_g, mi_c = g["iss"]["municipio_incidencia"], c.get("municipio_incidencia") or {}
            linhas.append(("municipio_incidencia", norm(mi_g["municipio"]) == norm(mi_c.get("municipio")),
                           mi_g["municipio"], mi_c.get("municipio")))
            lv = g["lei_12741"]["valor"]
            linhas.append(("lei_12741_valor", c.get("lei_12741_valor") == dec(lv), lv, c.get("lei_12741_valor")))
            linhas.append(("texto_irrf", c.get("texto_dispensa_irrf") == g["texto_dispensa_irrf"], g["texto_dispensa_irrf"], c.get("texto_dispensa_irrf")))
            cg = g["banco_na_descricao"]["conta"]
            linhas.append(("banco_no_corpo", conta_igual((c.get("banco") or {}).get("conta"), cg) if cg else not c.get("banco"),
                           cg, (c.get("banco") or {}).get("conta")))
            linhas.append(("descricao_nucleo", contido(c.get("descricao_base"), g["descricao"]), g["descricao"][:120] + "…", c.get("descricao_base")))
        else:
            it_g = g["itens"][0]
            it_c = (c.get("itens") or [{}])[0]
            linhas.append(("produto_catalogo", it_c.get("codigo") == it_g["codigo"], it_g["codigo"], it_c.get("codigo")))
    return linhas, compostas


def regra_competencia(gabarito: dict) -> list[tuple[str, bool, str, str]]:
    out = []
    for nid, g in gabarito.items():
        if g["tipo"] == "NFS-e":
            out.append((nid, g["competencia"] == g["emissao"][:10], g["competencia"], g["emissao"]))
    return out
