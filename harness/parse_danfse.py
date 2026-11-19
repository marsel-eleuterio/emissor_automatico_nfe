"""Leitura do DANFSe v2.0 (padrão nacional, NT 008/2026) a partir do PDF.

Usa o texto do `pdftotext -layout`. Serve para montar o gabarito quando só
houver o PDF da nota; quando houver o XML, prefira o XML (é o documento com
valor jurídico e não depende de layout).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

RE_DOC = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}")
RE_MONEY = re.compile(r"R\$\s*([\d.]+,\d{2})")
RE_DATA = r"\d{2}/\d{2}/\d{4}"
RE_DATAHORA = r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}"


def _bin_pdftotext() -> str:
    achado = shutil.which("pdftotext")
    if achado:
        return achado
    for cand in (
        Path(r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"),
        Path(r"C:\Program Files\Git\usr\bin\pdftotext.exe"),
    ):
        if cand.exists():
            return str(cand)
    return "pdftotext"


def pdf_text(path: Path) -> str:
    out = subprocess.run(
        [_bin_pdftotext(), "-layout", "-enc", "UTF-8", str(path), "-"],
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


def _prox_nao_vazia(lines: list[str], start: int) -> int:
    for i in range(start, len(lines)):
        if lines[i].strip():
            return i
    raise ValueError(f"sem linha não vazia após {start}")


def parse_danfse(texto: str) -> dict:
    L = texto.replace("\r\n", "\n").split("\n")

    chave = re.search(r"\d{50}", L[_prox_nao_vazia(L, _find(L, "CHAVE DE ACESSO DA NFS-e") + 1)]).group(0)
    m = re.search(rf"(\d+)\s+({RE_DATA})\s+({RE_DATAHORA})", L[_prox_nao_vazia(L, _find(L, "NÚMERO DA NFS-e") + 1)])
    numero, competencia, emissao = m.group(1), iso_data(m.group(2)), iso_datahora(m.group(3))
    m = re.search(rf"(\d+)\s+(\d+)\s+({RE_DATAHORA})", L[_prox_nao_vazia(L, _find(L, "NÚMERO DA DPS") + 1)])
    numero_dps, serie_dps = m.group(1), m.group(2)
    mun_emissor = re.search(r"Município:\s*(.+?)\s*$", L[0]).group(1)

    prestador = _parte(L, _find(L, "PRESTADOR / FORNECEDOR"))
    i_sn = _find(L, "Simples Nacional na Data de Competência")
    c_reg = L[i_sn].find("Regime de Apuração")
    ln_sn = L[_prox_nao_vazia(L, i_sn + 1)]
    prestador["simples_nacional"] = (ln_sn[:c_reg] if c_reg > 0 else ln_sn).strip() or None
    tomador = _parte(L, _find(L, "TOMADOR / ADQUIRENTE"))

    i_serv = _find(L, "SERVIÇO PRESTADO")
    i_desc = _find(L, "Descrição do Serviço", i_serv)
    cod, nbs, local, desc_cod_linhas = None, None, None, []
    for ln in L[i_serv + 1:i_desc]:
        ts = tokens(ln)
        if not ts:
            continue
        usou = False
        for tk in ts:
            mc = re.match(r"^(\d{2}\.\d{2}\.\d{2})\s*/\s*(\S+)$", tk)
            if mc and cod is None:
                cod = mc
                usou = True
            elif " / " in tk and local is None and re.search(r"/\s*[A-Z]{2}\b", tk):
                local = [p.strip() for p in tk.split(" / ")]
                usou = True
            elif usou and nbs is None and tk in {"-", ""} or (usou and nbs is None and re.match(r"^[\d.]+$", tk)):
                nbs = None if tk in {"-", ""} else tk
        if not usou:
            desc_cod_linhas.append(ln)
    if cod is None or local is None:
        raise ValueError("não encontrei código ou local em SERVIÇO PRESTADO")
    desc_codigo = join_wrapped(desc_cod_linhas)

    i_iss = _find(L, "TRIBUTAÇÃO MUNICIPAL (ISSQN)", i_desc)
    descricao = join_wrapped(L[i_desc + 1:i_iss])
    t_iss = tokens(L[_prox_nao_vazia(L, i_iss + 1)])
    incid = [p.strip() for p in t_iss[-1].split(" / ")]
    t_bc = tokens(L[_prox_nao_vazia(L, _find(L, "BC ISSQN", i_iss) + 1)])
    t_fed = tokens(L[_prox_nao_vazia(L, _find(L, "TRIBUTAÇÃO FEDERAL", i_iss) + 1)])
    t_pis = tokens(L[_prox_nao_vazia(L, _find(L, "PIS - Débito Apuração Própria", i_iss) + 1)])
    valor_servico = brl(L[_prox_nao_vazia(L, _find(L, "VALOR TOTAL DA NFS-e") + 1)])
    t_liq = tokens(L[_prox_nao_vazia(L, _find(L, "Total das Retenções") + 1)])
    lei_info, banco_info = _extrair_lei_e_banco(descricao)

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
            "nbs": nbs,
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
        "lei_12741": lei_info,
        "texto_dispensa_irrf": "dispensada da retenção de IRRF" in descricao,
        "banco_na_descricao": banco_info,
    }


def _extrair_lei_e_banco(descricao: str) -> tuple[dict, dict]:
    lei = re.search(
        r"Valor aproximado dos Tributos:?\s*-?\s*R\$\s*([\d.]+,\d{2})\s*-?\s*\(\s*(\d+,\d{2})%",
        descricao, re.I,
    )
    banco = (
        re.search(r"Banco:?\s*0?(\d{3})\b", descricao, re.I)
        or re.search(r"(?:banco:?\s*|\()0?(\d{3})\)", descricao, re.I)
    )
    agencia = re.search(r"Ag(?:[êe]ncia|\.?):?\s*(\d{4})\b", descricao, re.I)
    conta = re.search(r"(?:Conta(?:\s+corrente)?|C/C|Cc\.|Corrente):?\s*([\d]+-?[\dXx]?)", descricao, re.I)
    if not conta:
        m_alt = re.search(r"\b(\d{4})\s*-\s*(\d{5,}-[\dXx])\b", descricao)
        if m_alt:
            if not agencia:
                agencia = m_alt  # group(1)
            conta_val = m_alt.group(2)
        else:
            conta_val = None
    else:
        conta_val = conta.group(1)
    return (
        {
            "valor": str(brl(lei.group(1))) if lei else None,
            "aliquota_pct": lei.group(2).replace(",", ".") if lei else None,
        },
        {
            "banco": banco.group(1) if banco else None,
            "agencia": agencia.group(1) if agencia else None,
            "conta": conta_val,
        },
    )


# Correlação código municipal de São Paulo -> código de tributação nacional (LC 116)
COD_SP_PARA_NACIONAL = {
    "01430": "07.01.01",  # Decoração / arquitetura
    "01899": "17.03.01",  # Planejamento, coordenação, organização técnica/adm
    "02496": "17.06.01",  # Propaganda e publicidade
    "02498": "17.25.01",  # Inserção de textos, desenhos e outros materiais de publicidade
    "07161": "17.10.01",  # Planejamento, organização e administração de feiras/exposições
}


def parse_nfse_sp(texto: str) -> dict:
    """Leitura da NFS-e municipal da Prefeitura de São Paulo (Nota Fiscal Paulistana)."""
    L = texto.replace("\r\n", "\n").split("\n")
    full = "\n".join(L)
    num = re.search(r"SECRETARIA MUNICIPAL DA FAZENDA\s+(\d+)", full).group(1).lstrip("0") or "0"
    dh = re.search(rf"({RE_DATAHORA})", full).group(1)
    emissao = iso_datahora(dh)
    m_rps = re.search(rf"RPS N[º°]\s*(\d+),\s*emitido em\s*({RE_DATA})", full)
    competencia = iso_data(m_rps.group(2)) if m_rps else emissao[:10]
    m_chave = re.search(r"Identificador Nacional:\s*(\d{50})", full)
    chave = m_chave.group(1) if m_chave else None

    i_prest = _find(L, "PRESTADOR DE SERVIÇOS")
    i_tom = _find(L, "TOMADOR DE SERVIÇOS", i_prest)
    i_inter = _find(L, "INTERMEDIÁRIO DE SERVIÇOS", i_tom)
    i_disc = _find(L, "DISCRIMINAÇÃO DE SERVIÇOS", i_inter)
    i_val = _find(L, "VALOR TOTAL DO SERVIÇO", i_disc)
    i_cod = _find(L, "Código do Serviço", i_val)

    bloco_p = "\n".join(L[i_prest:i_tom])
    bloco_t = "\n".join(L[i_tom:i_inter])

    def _campo(bloco: str, rot: str) -> str | None:
        m = re.search(rf"{rot}:\s*(.+?)(?:\s{{2,}}|\n|$)", bloco)
        val = m.group(1).strip() if m else ""
        return None if val in {"", "-", "----", "-----"} else val

    def _mun_uf(bloco: str) -> tuple[str | None, str | None]:
        m = re.search(r"Município:\s*(.+?)\s+UF:\s*([A-Z]{2})", bloco)
        return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)

    def _cep_sp(bloco: str) -> str | None:
        m = re.search(r"CEP:\s*([\d.-]+)", bloco)
        return _cep(m.group(1)) if m else None

    p_mun, p_uf = _mun_uf(bloco_p)
    t_mun, t_uf = _mun_uf(bloco_t)
    prestador = {
        "doc": (RE_DOC.search(bloco_p).group(0) if RE_DOC.search(bloco_p) else None),
        "nome": _campo(bloco_p, r"Nome/Razão Social"),
        "inscricao_municipal": _campo(bloco_p, r"Inscrição Municipal"),
        "telefone": None,
        "municipio": p_mun,
        "uf": p_uf,
        "cep": _cep_sp(bloco_p),
        "endereco": _campo(bloco_p, r"Endereço"),
        "email": None,
        "simples_nacional": "Optante pelo Simples Nacional" if "Simples Nacional" in full else None,
    }
    tomador = {
        "doc": (RE_DOC.search(bloco_t).group(0) if RE_DOC.search(bloco_t) else None),
        "nome": _campo(bloco_t, r"Nome/Razão Social"),
        "inscricao_municipal": _campo(bloco_t, r"Inscrição Municipal"),
        "telefone": None,
        "municipio": t_mun,
        "uf": t_uf,
        "cep": _cep_sp(bloco_t),
        "endereco": _campo(bloco_t, r"Endereço"),
        "email": _campo(bloco_t, r"E-mail"),
    }

    descricao = join_wrapped(L[i_disc + 1:i_val])
    valor_servico = brl(L[i_val])
    cod_ln = L[_prox_nao_vazia(L, i_cod + 1)].strip()
    m_cod = re.match(r"(\d{5})\s*-\s*(.+)", cod_ln)
    cod_mun = m_cod.group(1) if m_cod else None
    desc_cod = m_cod.group(2).strip() if m_cod else cod_ln
    cod_nac = COD_SP_PARA_NACIONAL.get(cod_mun, cod_mun)

    lei_info, banco_info = _extrair_lei_e_banco(descricao)
    return {
        "tipo": "NFS-e",
        "layout": "SP_municipal",
        "municipio_emissor": "São Paulo - SP",
        "chave": chave,
        "numero": num,
        "numero_dps": m_rps.group(1) if m_rps else None,
        "serie_dps": None,
        "competencia": competencia,
        "emissao": emissao,
        "prestador": prestador,
        "tomador": tomador,
        "servico": {
            "cod_trib_nacional": cod_nac,
            "cod_trib_municipal": cod_mun,
            "descricao_codigo": desc_cod,
            "nbs": None,
            "local_prestacao": {"municipio": "São Paulo", "uf": "SP"},
        },
        "descricao": descricao,
        "iss": {
            "tipo_tributacao": "Operação Tributável",
            "municipio_incidencia": {"municipio": "São Paulo", "uf": "SP"},
            "retido": False,
        },
        "retencoes_federais": {
            "irrf": None,
            "contribuicao_previdenciaria": None,
            "contribuicoes_sociais": "0 - PIS/COFINS/CSLL Não Retidos",
        },
        "valor_servico": str(valor_servico),
        "total_retencoes": None,
        "valor_liquido": str(valor_servico),
        "lei_12741": lei_info,
        "texto_dispensa_irrf": "dispensada da retenção de IRRF" in descricao,
        "banco_na_descricao": banco_info,
    }


def parse_pdf_nfse(texto: str) -> dict:
    if "CHAVE DE ACESSO DA NFS-e" in texto:
        return parse_danfse(texto)
    if "PREFEITURA DO MUNICÍPIO DE SÃO PAULO" in texto:
        return parse_nfse_sp(texto)
    raise ValueError("Layout de NFS-e não reconhecido automaticamente")


if __name__ == "__main__":
    import json
    import sys

    for p in sys.argv[1:]:
        print(json.dumps(parse_danfse(pdf_text(Path(p))), ensure_ascii=False, indent=2))
