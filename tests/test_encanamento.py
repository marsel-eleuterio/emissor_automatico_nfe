"""Testes de encanamento: schema, rótulos e os extratores de LLM com respostas simuladas.

Uso: python -I tests/test_encanamento.py
"""
from __future__ import annotations

import json
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "harness"))

from jsonschema import Draft202012Validator  # noqa: E402

from comum import DADOS, ler_json  # noqa: E402

SCHEMA = ler_json(RAIZ / "schema" / "extracao_v1.json")
ROT = ler_json(DADOS / "rotulos_extracao.json")
CAD = ler_json(DADOS / "cadastro_rascunho.json")


def test_schema_e_rotulos():
    Draft202012Validator.check_schema(SCHEMA)
    v = Draft202012Validator(SCHEMA)
    for caso, rot in ROT.items():
        if caso.startswith("_"):
            continue
        erros = list(v.iter_errors(rot))
        assert not erros, f"rótulo {caso} fora do schema: {erros[0].message}"


def test_regex_no_schema():
    from extratores import RegexBase, cabecalho

    v = Draft202012Validator(SCHEMA)
    ext = RegexBase(CAD)
    for c in ler_json(DADOS / "casos.json"):
        texto = (DADOS / c["input"]).read_text(encoding="utf-8")
        saida = ext.extrair(c["caso"], texto, {**cabecalho(texto), "recebido_em": c["recebido_em"]})
        erros = list(v.iter_errors(saida))
        assert not erros, f"regex {c['caso']} fora do schema: {erros[0].message}"


def test_claude_simulado():
    class Bloco:
        type = "tool_use"
        input = ROT["C"]

    class Resp:
        content = [Bloco()]
        usage = types.SimpleNamespace(input_tokens=1200, output_tokens=800)

    class Mensagens:
        def create(self, **kw):
            assert kw["tool_choice"]["name"] == "registrar_extracao"
            assert kw["tools"][0]["input_schema"]["title"] == "ExtracaoPedidoNota_v1"
            return Resp()

    falso = types.ModuleType("anthropic")
    falso.Anthropic = lambda: types.SimpleNamespace(messages=Mensagens())
    sys.modules["anthropic"] = falso
    from extratores import Claude

    meta = {}
    assert Claude("modelo-teste").extrair("C", "texto", meta) == ROT["C"]
    assert meta["tokens"]["saida"] == 800


def test_ollama_simulado():
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert corpo["format"]["title"] == "ExtracaoPedidoNota_v1"
            assert corpo["options"]["num_ctx"] == 8192
            assert corpo["think"] is False
            resp = json.dumps({"message": {"content": json.dumps(ROT["D"], ensure_ascii=False)},
                               "prompt_eval_count": 3100, "eval_count": 900}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import os

    from extratores import Ollama

    os.environ["NFSE_OLLAMA_PENSAR"] = "0"
    try:
        ext = Ollama("qwen3:14b", f"http://127.0.0.1:{srv.server_port}")
        meta = {}
        assert ext.extrair("D", "texto", meta) == ROT["D"]
        assert ext.nome == "ollama:qwen3:14b:sem-pensar"
        assert meta["tokens"]["saida"] == 900
    finally:
        os.environ.pop("NFSE_OLLAMA_PENSAR", None)
        srv.shutdown()


def _servidor_openai(respostas: list, recebidos: list) -> HTTPServer:
    """API falsa no formato da OpenAI: devolve (status, corpo) na ordem e guarda o que recebeu."""

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            recebidos.append({"corpo": corpo, "auth": self.headers.get("Authorization"), "path": self.path})
            status, resp = respostas.pop(0)
            dados = json.dumps(resp, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(dados)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _completion(conteudo: str, entrada: int, saida: int) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": conteudo}}],
            "usage": {"prompt_tokens": entrada, "completion_tokens": saida}}


def test_openai_cai_para_json_livre():
    from extratores import CompativelOpenAI

    recebidos = []
    srv = _servidor_openai([
        (400, {"error": {"message": "response_format json_schema não suportado"}}),
        (200, _completion("```json\n" + json.dumps(ROT["B"], ensure_ascii=False) + "\n```", 3000, 700)),
    ], recebidos)
    try:
        ext = CompativelOpenAI("modelo-x", url=f"http://127.0.0.1:{srv.server_port}/v1", chave="segredo")
        meta = {}
        assert ext.extrair("B", "texto", meta) == ROT["B"]
        assert recebidos[0]["corpo"]["response_format"]["type"] == "json_schema"
        assert recebidos[1]["corpo"]["response_format"]["type"] == "json_object"
        assert "Schema da resposta" in recebidos[1]["corpo"]["messages"][0]["content"]
        assert recebidos[0]["auth"] == "Bearer segredo" and recebidos[0]["path"] == "/v1/chat/completions"
        assert meta["formato"] == "json_object" and meta["tokens"] == {"entrada": 3000, "saida": 700}
    finally:
        srv.shutdown()


def test_openai_corrige_saida_fora_do_schema():
    from extratores import CompativelOpenAI

    ruim = {k: v for k, v in ROT["A"].items() if k != "pedidos"}
    recebidos = []
    srv = _servidor_openai([
        (200, _completion(json.dumps(ruim, ensure_ascii=False), 2000, 500)),
        (200, _completion(json.dumps(ROT["A"], ensure_ascii=False), 2600, 600)),
    ], recebidos)
    try:
        ext = CompativelOpenAI("modelo-x", url=f"http://127.0.0.1:{srv.server_port}")
        meta = {}
        assert ext.extrair("A", "texto", meta) == ROT["A"]
        assert meta["tentativas"] == 2 and meta["tokens"]["entrada"] == 4600
        assert "não passou no schema" in recebidos[1]["corpo"]["messages"][-1]["content"]
    finally:
        srv.shutdown()


def test_openai_exige_lote_anonimizado():
    import os

    from extratores import CompativelOpenAI

    os.environ.pop("NFSE_DADOS_ANONIMIZADOS", None)
    os.environ.pop("NFSE_NIVEL_PAGO", None)
    try:
        CompativelOpenAI("gemini-3.8-flash", provedor="gemini")
    except SystemExit as e:
        assert "anonimizado" in str(e)
    else:
        raise AssertionError("mandaria dado real para fora do notebook")


def test_openai_nivel_pago_libera_caso_real():
    import os

    from extratores import CompativelOpenAI

    os.environ.pop("NFSE_DADOS_ANONIMIZADOS", None)
    os.environ["NFSE_NIVEL_PAGO"] = "1"
    try:
        ext = CompativelOpenAI("gemini-3.8-flash", provedor="gemini", chave="x")
        assert ext.nome == "oai:gemini:gemini-3.8-flash:pago"
    finally:
        os.environ.pop("NFSE_NIVEL_PAGO", None)


CLAUDE_FALSO = r'''
import json, sys
a = sys.argv[1:]
assert a[0] == "-p" and a[a.index("--tools") + 1] == ""
assert "--no-session-persistence" in a and a[a.index("--model") + 1] == "haiku"
assert json.loads(a[a.index("--json-schema") + 1])["title"] == "ExtracaoPedidoNota_v1"
assert "<email>" in sys.stdin.buffer.read().decode("utf-8")
saida = json.load(open(sys.argv[0] + ".json", encoding="utf-8"))
print(json.dumps({"type": "result", "is_error": False, "result": "", "structured_output": saida,
                  "usage": {"input_tokens": 2500, "output_tokens": 650}, "total_cost_usd": 0.0006}))
'''


def test_claude_code_simulado():
    import tempfile

    from extratores import ClaudeCode

    with tempfile.TemporaryDirectory() as d:
        falso = Path(d) / "claude_falso.py"
        falso.write_text(CLAUDE_FALSO, encoding="utf-8")
        Path(f"{falso}.json").write_text(json.dumps(ROT["E"], ensure_ascii=False), encoding="utf-8")
        ext = ClaudeCode("haiku", comando=[sys.executable, "-I", str(falso)])
        meta = {}
        assert ext.extrair("E", "texto", meta) == ROT["E"]
        assert ext.nome == "claude-code:haiku" and meta["tokens"]["saida"] == 650


def test_anonimizar():
    from anonimizar import carregar_trocas, gerar_lote_anonimizado
    from avaliar import checar_caso_extracao, checar_ponta_a_ponta
    from extratores import cabecalho, criar

    trocas = carregar_trocas()
    destino = gerar_lote_anonimizado()
    for arq in destino.rglob("*"):
        if arq.is_file():
            txt = arq.read_text(encoding="utf-8")
            for orig, _ in trocas:
                assert orig not in txt, f"valor original '{orig}' sobrou em {arq.relative_to(RAIZ)}"

    def placar(pasta: Path, nome_ext: str) -> tuple[int, int, int, int]:
        casos = ler_json(pasta / "casos.json")
        rotulos = ler_json(pasta / "rotulos_extracao.json")
        cadastro = ler_json(pasta / "cadastro_rascunho.json")
        gabarito = ler_json(pasta / "gabarito_notas.json")
        ext = criar(nome_ext, rotulos, cadastro)
        ok_e = tot_e = ok_n = tot_n = 0
        for c in casos:
            cid = c["caso"]
            texto = (pasta / c["input"]).read_text(encoding="utf-8")
            meta = {**cabecalho(texto), "recebido_em": c["recebido_em"]}
            saida = ext.extrair(cid, texto, meta)
            for _, ok, _, _ in checar_caso_extracao(saida, rotulos[cid]):
                ok_e += int(ok)
                tot_e += 1
            notas = [gabarito[n["id"]] for n in c["notas"]]
            linhas, _ = checar_ponta_a_ponta(saida, meta, cadastro, notas)
            for _, ok, _, _ in linhas:
                ok_n += int(ok)
                tot_n += 1
        return ok_e, tot_e, ok_n, tot_n

    assert placar(DADOS, "oraculo") == placar(destino, "oraculo") == (65, 65, 49, 49)
    assert placar(DADOS, "regex") == placar(destino, "regex") == (58, 65, 44, 49)


def test_compor_regras_lote2():
    from compor import compor_nfse

    cli = {
        "cnpj": "11.111.111/0001-11",
        "municipio": "São Paulo",
        "uf": "SP",
        "codigos_servico": [{"nacional": "17.06.01", "municipal": "001"}],
        "descricao_padrao": "Serviços comissionados",
        "aliquota_lei_12741_pct": None,
        "dados_bancarios": {"banco": "260", "agencia": "0001", "conta": "12345-6"},
        "incluir_banco_sempre": True,
        "texto_dispensa_irrf": False,
    }
    ped = {
        "tomador": {"cnpj_cpf": "22.222.222/0001-22"},
        "valor": 1000.0,
        "descricao": {"texto": None, "tipo": "ausente", "lacunas": []},
        "dados_bancarios": {"banco": None, "agencia": None, "conta": None, "pix": None},
        "exige_dados_bancarios_no_corpo": False,
    }
    nota = compor_nfse(ped, cli)
    assert nota["descricao_base"] == "Serviços comissionados"
    assert nota["descricao_preenchida_pelo_cadastro"] is True
    assert nota["lei_12741_valor"] is None
    assert nota["banco"]["conta"] == "12345-6"


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print(f"ok  {nome}")
