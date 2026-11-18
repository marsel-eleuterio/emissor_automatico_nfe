"""Leitura do DANFSe v2.0 (padrão nacional, NT 008/2026) a partir do PDF.

Usa o texto do `pdftotext -layout`. Serve para montar o gabarito quando só
houver o PDF da nota; quando houver o XML, prefira o XML (é o documento com
valor jurídico e não depende de layout).
"""
from __future__ import annotations

import re
import subprocess
from decimal import Decimal
from pathlib import Path

RE_DOC = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}")
RE_MONEY = re.compile(r"R\$\s*([\d.]+,\d{2})")
RE_DATA = r"\d{2}/\d{2}/\d{4}"
RE_DATAHORA = r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}"


def pdf_text(path: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return out.stdout


def brl(s: str | None) -> Decimal | None:
    if not s or s.strip() in {"-", ""}:
        return None
    m = RE_MONEY.search(s) or re.search(r"([\d.]+,\d{2})", s)
    if not m:
        return None
    return Decimal(m.group(1).replace(".", "").replace(",", "."))


def iso_data(d: str) -> str:
    dd, mm, aaaa = d.split("/")
    return f"{aaaa}-{mm}-{dd}"


def iso_datahora(dh: str) -> str:
    d, h = dh.split(" ")
    return f"{iso_data(d)}T{h}"


def join_wrapped(parts: list[str]) -> str:
    """Junta linhas quebradas pelo layout; não põe espaço em número cortado (0001-\\n78)."""
    out = ""
    for raw in parts:
        s = raw.strip()
        if not s or s == '"':
            continue
        if not out:
            out = s
        elif re.search(r"\d-$", out):
            out += s
        else:
            out += " " + s
    return out


def tokens(line: str) -> list[str]:
    return [t for t in re.split(r"\s{2,}", line.strip()) if t]


def _find(lines: list[str], needle: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if needle in lines[i]:
            return i
    raise ValueError(f"rótulo não encontrado: {needle!r}")


def _cep(s: str | None) -> str | None:
    if not s:
        return None
    dig = re.sub(r"\D", "", s.split("/")[-1])
    return f"{dig.zfill(8)[:5]}-{dig.zfill(8)[5:]}" if dig else None


PARADAS = (
    "Simples Nacional na Data", "DESTINATÁRIO DA OPERAÇÃO", "INTERMEDIÁRIO",
    "TOMADOR / ADQUIRENTE", "SERVIÇO PRESTADO",
)


def _parte(lines: list[str], i_cab: int) -> dict:
    """Bloco de prestador ou tomador, a partir da linha de cabeçalho."""
    cab, val = lines[i_cab], lines[i_cab + 1]
    c_im, c_tel = cab.index("Indicador Municipal"), cab.index("Telefone")
    doc = RE_DOC.search(val)
    im = val[c_im:c_tel].strip()
    tel = val[c_tel:].strip()

    i_nome = _find(lines, "Nome / Nome Empresarial", i_cab)
    rot = lines[i_nome]
    c_mun, c_ibge = rot.index("Município / Sigla UF"), rot.index("Código IBGE / CEP")
    i_end = _find(lines, "Endereço", i_nome)
    nome, mun, ibge_cep = [], None, None
    for ln in lines[i_nome + 1:i_end]:
        nome.append(ln[:c_mun])
        if mun is None and ln[c_mun:c_ibge].strip():
            mun = ln[c_mun:c_ibge].strip()
        if ibge_cep is None and ln[c_ibge:].strip():
            ibge_cep = ln[c_ibge:].strip()

    c_mail = lines[i_end].index("E-mail")
    end, email = [], None
    for ln in lines[i_end + 1:]:
        if any(p in ln for p in PARADAS):
            break
        esq, dir_ = ln[:c_mail], ln[c_mail:].strip()
        if email is None and dir_:
            email = dir_
        elif email is None and esq.rstrip().endswith(" -"):
            # o "-" do e-mail vazio às vezes cola no fim do endereço
            esq, email = esq.rstrip()[:-2], "-"
        end.append(esq)

    municipio, uf = (mun.split(" / ") + [None])[:2] if mun else (None, None)
    return {
        "doc": doc.group(0) if doc else None,
        "nome": join_wrapped(nome),
        "inscricao_municipal": None if im in {"", "-"} else im,
        "telefone": None if tel in {"", "-"} else tel,
        "municipio": municipio,
        "uf": uf,
        "cep": _cep(ibge_cep),
        "endereco": join_wrapped(end),
        "email": None if email in {None, "-"} else email,
    }


def parse_danfse(texto: str) -> dict:
    L = texto.split("\n")

    chave = re.search(r"\d{50}", L[_find(L, "CHAVE DE ACESSO DA NFS-e") + 1]).group(0)
    m = re.search(rf"(\d+)\s+({RE_DATA})\s+({RE_DATAHORA})", L[_find(L, "NÚMERO DA NFS-e") + 1])
    numero, competencia, emissao = m.group(1), iso_data(m.group(2)), iso_datahora(m.group(3))
    m = re.search(rf"(\d+)\s+(\d+)\s+({RE_DATAHORA})", L[_find(L, "NÚMERO DA DPS") + 1])
    numero_dps, serie_dps = m.group(1), m.group(2)
    mun_emissor = re.search(r"Município:\s*(.+?)\s*$", L[0]).group(1)

    prestador = _parte(L, _find(L, "PRESTADOR / FORNECEDOR"))
    sn = tokens(L[_find(L, "Simples Nacional na Data de Competência") + 1])
    prestador["simples_nacional"] = sn[0] if sn else None
    tomador = _parte(L, _find(L, "TOMADOR / ADQUIRENTE"))

    i_serv = _find(L, "SERVIÇO PRESTADO")
    t = tokens(L[i_serv + 1])
    cod = re.match(r"(\d{2}\.\d{2}\.\d{2})\s*/\s*(\S+)", t[0])
    local = t[-1].split(" / ")
    i_desc = _find(L, "Descrição do Serviço", i_serv)
    desc_codigo = join_wrapped(L[i_serv + 2:i_desc])

    i_iss = _find(L, "TRIBUTAÇÃO MUNICIPAL (ISSQN)", i_desc)
    descricao = join_wrapped(L[i_desc + 1:i_iss])
    t_iss = tokens(L[i_iss + 1])
    incid = t_iss[-1].split(" / ")
    t_bc = tokens(L[_find(L, "BC ISSQN", i_iss) + 1])
    t_fed = tokens(L[_find(L, "TRIBUTAÇÃO FEDERAL", i_iss) + 1])
    t_pis = tokens(L[_find(L, "PIS - Débito Apuração Própria", i_iss) + 1])
    valor_servico = brl(L[_find(L, "VALOR TOTAL DA NFS-e") + 1])
    t_liq = tokens(L[_find(L, "Total das Retenções") + 1])

    lei = re.search(
        r"Valor aproximado dos Tributos:?\s*-?\s*R\$\s*([\d.]+,\d{2})\s*\((\d+,\d{2})%", descricao
    )
    banco = re.search(r"Banco:?\s*0?(\d{3})\b", descricao)
    agencia = re.search(r"Ag[êe]ncia:?\s*(\d{4})", descricao)
    conta = re.search(r"Conta(?: corrente)?:?\s*([\d]+-?[\dXx]?)", descricao)

    return {
        "tipo": "NFS-e",
        "municipio_emissor": mun_emissor,
        "chave": chave,
        "numero": numero,
        "numero_dps": numero_dps,
        "serie_dps": serie_dps,
        "competencia": competencia,
        "emissao": emissao,
        "prestador": prestador,
        "tomador": tomador,
        "servico": {
            "cod_trib_nacional": cod.group(1),
            "cod_trib_municipal": None if cod.group(2) == "-" else cod.group(2),
            "descricao_codigo": desc_codigo,
            "nbs": None if t[1] == "-" else t[1],
            "local_prestacao": {"municipio": local[0], "uf": local[1]},
        },
        "descricao": descricao,
        "iss": {
            "tipo_tributacao": t_iss[0],
            "municipio_incidencia": {"municipio": incid[0], "uf": incid[1]},
            "retido": t_bc[2] == "Retido",
        },
        "retencoes_federais": {
            "irrf": None if t_fed[0] == "-" else t_fed[0],
            "contribuicao_previdenciaria": None if t_fed[1] == "-" else t_fed[1],
            "contribuicoes_sociais": t_pis[-1],
        },
        "valor_servico": str(valor_servico),
        "total_retencoes": None if t_liq[0] == "-" else str(brl(t_liq[0])),
        "valor_liquido": str(brl(t_liq[1])),
        "lei_12741": {
            "valor": str(brl(lei.group(1))) if lei else None,
            "aliquota_pct": lei.group(2).replace(",", ".") if lei else None,
        },
        "texto_dispensa_irrf": "dispensada da retenção de IRRF" in descricao,
        "banco_na_descricao": {
            "banco": banco.group(1) if banco else None,
            "agencia": agencia.group(1) if agencia else None,
            "conta": conta.group(1) if conta else None,
        },
    }


if __name__ == "__main__":
    import json
    import sys

    for p in sys.argv[1:]:
        print(json.dumps(parse_danfse(pdf_text(Path(p))), ensure_ascii=False, indent=2))
