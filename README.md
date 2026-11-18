# Automação de NFS-e por email · Fase 0

O sistema vai ler os pedidos de nota que chegam por email, extrair os campos com um LLM, emitir pela API da Sefin Nacional depois de um clique de aprovação e responder ao cliente. Este repositório tem a Fase 0: gabarito, schema, prompt e o harness que mede a extração antes de construir o sistema.

- Plano completo, com decisões, arquitetura e fases: [`docs/PLANO.md`](docs/PLANO.md)
- Contexto e regras para o Claude Code: [`CLAUDE.md`](CLAUDE.md)

**Atenção: `raw/`, `data/` e os relatórios de avaliação têm dados pessoais e bancários de clientes.** Repositório só privado; o `.gitignore` já deixa esses arquivos de fora.

## Começar no VS Code (Windows)

1. Descompacte e abra a pasta `nfse-automacao` no VS Code (Arquivo → Abrir Pasta).
2. Instale as extensões recomendadas quando o VS Code oferecer: Python, Pylance, Python Debugger, Claude Code e Mermaid para o preview do plano.
3. Rode Terminal → Executar Tarefa → **Preparar ambiente**. A tarefa cria a `.venv`, instala as dependências, roda os testes e mostra placa de vídeo, RAM, Ollama e o login do Claude Code.
4. Selecione o interpretador da `.venv` (Ctrl+Shift+P → Python: Select Interpreter).
5. Rode as tarefas **Eval: Ollama (todos os modelos)**, **Eval: Claude pelo plano** e, com o crédito do Google AI Pro ativado, **Eval: Gemini pago**. Depois rode **Comparativo**.

Para a tarefa do Gemini pago, grave a chave uma vez com `setx GEMINI_API_KEY "<chave>"` e reabra o VS Code. A chave tem de ser de um projeto ligado à conta de faturamento que recebe o crédito; confira no faturamento do Google Cloud se o uso está saindo do crédito.

O extrator `claude-code` chama o `claude` do terminal. A extensão do VS Code traz o Claude Code só para o painel; para o terminal, instale o CLI ([setup](https://code.claude.com/docs/en/setup)). Antes de rodar dado de cliente pelo plano, desligue "Help improve Claude" em Configurações → Privacidade, no app do Claude.

As tarefas chamam o PowerShell com `-ExecutionPolicy Bypass`, então funcionam mesmo com scripts bloqueados no Windows. Para depurar, as configurações de `.vscode/launch.json` usam o `.env` (modelo em `.env.example`).

## O que tem aqui

| Caminho | O que é |
| --- | --- |
| `CLAUDE.md` | Contexto, regras e próximos passos para o Claude Code |
| `docs/PLANO.md` | Plano completo, exportado do doc online |
| `scripts/setup.ps1`, `scripts/eval_local.ps1` | Preparar o ambiente; rodar os modelos locais e o Claude pelo plano |
| `.vscode/` | Tarefas, depuração, extensões recomendadas e configurações do projeto |
| `requirements.txt`, `.env.example` | Dependências e modelo das variáveis locais |
| `raw/` | PDFs originais: emails (impressão do Gmail) e notas emitidas |
| `data/casos.json` | Manifesto: caso → texto do pedido → notas que saíram dele, horários |
| `data/inputs/*.txt` | Texto do pedido como chegou ao escritório, sem a resposta da equipe (evita vazamento do gabarito) |
| `data/rotulos_extracao.json` | Saída esperada do extrator para cada pedido (feita à mão, só com o texto do pedido) |
| `data/gabarito_notas.json` | Campos das notas emitidas, gerado por `build_gabarito.py` a partir dos PDFs |
| `data/gabarito_manual.json` | Notas que o parser não lê (NF-e de produto), digitadas |
| `data/cadastro_rascunho.json` | Cadastro de clientes tirado das notas: código de serviço, alíquota da Lei 12.741, conta, remetentes |
| `schema/extracao_v1.json` | JSON Schema da saída do extrator |
| `harness/prompt_v1.md` | Prompt de sistema do extrator |
| `harness/parse_danfse.py` | Lê o DANFSe v2.0 (layout nacional) do PDF |
| `harness/compor.py` | Regras: cadastro + extração → campos da nota (município de incidência, Lei 12.741, descrição) |
| `harness/extratores.py` | Extratores: `oraculo`, `regex`, `claude`, `claude-code`, `ollama`, `openai`, `replay` |
| `harness/avaliar.py`, `harness/run_eval.py` | Comparação campo a campo e relatório |
| `harness/cobertura.py` | De onde vem cada campo da nota (email, cadastro, regra, consulta) |
| `tests/test_encanamento.py` | Schema, rótulos e extratores de LLM com respostas simuladas |
| `reports/` | Relatórios gerados |

## Como rodar

Requer Python 3.11+ e `pip install -r requirements.txt` (a tarefa **Preparar ambiente** faz isso). O `data/gabarito_notas.json` já vem montado: o `pdftotext` (poppler) só é preciso para remontá-lo com notas novas (no Windows, `conda install -c conda-forge poppler`).

Os comandos abaixo são de bash. No PowerShell, troque `export VAR=...` por `$env:VAR = "..."`; a seção de modelos locais tem o bloco pronto para o Windows.

```bash
python -I harness/build_gabarito.py            # PDFs das notas -> data/gabarito_notas.json
python -I harness/cobertura.py                 # tabela de origem dos campos
python -I harness/run_eval.py --extrator oraculo   # extração perfeita: testa só as regras
python -I harness/run_eval.py --extrator regex     # linha de base sem LLM

# LLM comercial (pip install anthropic)
export ANTHROPIC_API_KEY=...
python -I harness/run_eval.py --extrator claude --modelo claude-haiku-5-5
python -I harness/run_eval.py --extrator claude --modelo claude-sonnet-5-5

# LLM local no Ollama
python -I harness/run_eval.py --extrator ollama --modelo qwen3.5:9b

# Reavaliar saídas gravadas, sem chamar o modelo de novo
python -I harness/run_eval.py --extrator replay --replay reports/saidas_claude_AAAAMMDD-HHMMSS.json

python -I tests/test_encanamento.py
```

Cada rodada grava `reports/avaliacao_<extrator>_<data>.md` (resumo e divergências), um `.csv` campo a campo e `saidas_<extrator>_<data>.json` com as saídas brutas.

## Modelos locais na RTX 4070 do notebook (8 GB)

Confira a placa antes: `nvidia-smi` mostra a VRAM (a 4070 de notebook tem 8 GB; a de desktop, 12 GB).

| Modelo | Na 4070 de notebook (8 GB) |
| --- | --- |
| `qwen3.5:9b` | Cabe inteiro na GPU |
| `gemma4:12b` | No limite: parte do modelo vai para a RAM |
| `qwen3:14b` | Não cabe inteiro: mais lento |
| `qwen3.6:35b-a3b` | Quase tudo na RAM: bem mais lento; só com 32 GB de RAM |

No Windows, a tarefa **Eval: Ollama (todos os modelos)** chama `scripts/eval_local.ps1`, que faz o mesmo que o bloco abaixo. No PowerShell, da raiz do projeto:

```powershell
$modelos = "qwen3.5:9b", "gemma4:12b", "qwen3:14b", "qwen3.6:35b-a3b"
foreach ($m in $modelos) { ollama pull $m }
foreach ($m in $modelos) {
  foreach ($p in "0", "1") {
    $env:NFSE_OLLAMA_PENSAR = $p
    python -I harness/run_eval.py --extrator ollama --modelo $m
  }
}
Remove-Item Env:NFSE_OLLAMA_PENSAR
python -I harness/comparar.py   # tabela modelo × campo em reports/comparativo.md
```

No Linux ou macOS (bash):

```bash
for m in qwen3.5:9b gemma4:12b qwen3:14b qwen3.6:35b-a3b; do
  ollama pull $m
  NFSE_OLLAMA_PENSAR=0 python -I harness/run_eval.py --extrator ollama --modelo $m
  NFSE_OLLAMA_PENSAR=1 python -I harness/run_eval.py --extrator ollama --modelo $m
done
python -I harness/comparar.py
```

- `NFSE_OLLAMA_PENSAR`: `0` desliga o raciocínio (mais rápido), `1` liga, vazio usa o padrão do modelo.
- `NFSE_OLLAMA_CTX`: contexto em tokens (padrão 8192). Contexto maior ocupa VRAM e pode empurrar o modelo para a RAM.
- Durante a rodada, `ollama ps` mostra quanto do modelo ficou na GPU.
- O Ollama também responde no formato da OpenAI: `--extrator openai --provedor ollama` testa o mesmo modelo pelo caminho dos free tiers.

## Desenvolver sem gastar

Caso real só passa pelo Ollama local, pelo Claude ou por um nível pago que não treina com os dados. Os níveis gratuitos de Gemini, Groq e GitHub Models recebem só lote anonimizado. Fora do notebook, o harness exige `NFSE_DADOS_ANONIMIZADOS=1` ou, com chave de nível pago, `NFSE_NIVEL_PAGO=1`.

As contas pessoais do Marsel (plano Pro da Anthropic e Google AI Pro) servem só para validar o MVP. Na entrega, as chaves passam a ser do escritório e as pessoais são revogadas; o checklist está em `docs/PLANO.md`, em Fases e entregas.

| Extrator | Custo | Caso real? | O que precisa |
| --- | --- | --- | --- |
| `ollama` | Zero | Sim: não sai do notebook | Ollama rodando (seção acima) |
| `claude-code` | Sai do limite do seu plano Pro ou Max | Sim, com "Help improve Claude" desligado | `claude` instalado e logado no plano |
| `claude` | Crédito mensal de API do Max (US$ 100) ou do Ultra (US$ 200); o Pro não tem | Sim: termos comerciais da API | Chave do Console ligado ao plano em `ANTHROPIC_API_KEY` |
| `openai --provedor gemini` com `NFSE_NIVEL_PAGO=1` | Crédito mensal do Google AI Pro (US$ 10/mês), ativado no Google Developer Program | Sim: no nível pago o Google não usa os dados para melhorar produtos | Chave de um projeto com faturamento ativo em `GEMINI_API_KEY` |
| `openai --provedor gemini` | Nível gratuito | Não: o Google usa o conteúdo para melhorar produtos | Chave do AI Studio em `GEMINI_API_KEY` |
| `openai --provedor groq` | Nível gratuito | Não: sem contrato de dados | Chave em `GROQ_API_KEY` |
| `openai --provedor github` | Nível gratuito | Não: sem contrato de dados | Token com escopo `models:read` em `GITHUB_TOKEN` |

No PowerShell, da raiz do projeto:

```powershell
# Claude pelo seu plano, sem custo extra (usa o login do claude, nunca uma chave de API)
python -I harness/run_eval.py --extrator claude-code --modelo haiku
python -I harness/run_eval.py --extrator claude-code --modelo sonnet

# Claude pela API, gastando o crédito mensal do Max ou do Ultra
$env:ANTHROPIC_API_KEY = "<chave do Console ligado ao plano>"
python -I harness/run_eval.py --extrator claude --modelo claude-haiku-5-5

# Gemini no nível pago, com o crédito do Google AI Pro: caso real permitido
$env:NFSE_NIVEL_PAGO = "1"
$env:GEMINI_API_KEY = "<chave de um projeto com faturamento ativo>"
python -I harness/run_eval.py --extrator openai --provedor gemini --modelo gemini-3.8-flash
python -I harness/run_eval.py --extrator openai --provedor gemini --modelo gemini-4-argon   # teto de qualidade
Remove-Item Env:NFSE_NIVEL_PAGO

# Níveis gratuitos: só com um lote anonimizado, numa pasta com a mesma estrutura de data/
$env:NFSE_DADOS = "data_anon"
$env:NFSE_DADOS_ANONIMIZADOS = "1"
$env:GEMINI_API_KEY = "<chave do AI Studio>"
python -I harness/run_eval.py --extrator openai --provedor gemini --modelo gemini-3.8-flash
$env:GITHUB_TOKEN = "<token com models:read>"
python -I harness/run_eval.py --extrator openai --provedor github --modelo openai/gpt-4.1
```

- O nome do modelo é o do catálogo de cada provedor (AI Studio, console do Groq, GitHub Marketplace); os limites gratuitos mudam e aparecem nesses painéis.
- `NFSE_NIVEL_PAGO=1` é uma declaração sua: use só com chave de projeto com faturamento ativo. No painel de faturamento do Google Cloud, confira se o crédito do Google AI Pro está abatendo o uso da API. O relatório sai com `:pago` no nome.
- `NFSE_OAI_PAUSA`: segundos entre chamadas, para caber no limite por minuto. Um 429 já faz o harness esperar e tentar de novo.
- O extrator `openai` pede JSON Schema; se o provedor recusar, cai para JSON livre e depois texto, e valida tudo no schema com uma chance de correção.
- Relatórios de um lote fora de `data/` levam o nome da pasta, para o comparativo não misturar lotes.
- Lote anonimizado: copie `data/` para `data_anon/` e troque nomes de pessoa física, CPFs, contas, emails e telefones pelos mesmos valores falsos em `inputs/`, `rotulos_extracao.json`, `gabarito_notas.json` e `cadastro_rascunho.json`. A troca tem de ser igual em todos os arquivos, senão o gabarito deixa de bater.

## Duas medidas

- **Extração:** saída do modelo × `rotulos_extracao.json` (tomador, valor, descrição, local do serviço, conta, vencimento, quantidade de notas, prazo).
- **Nota composta:** extração + cadastro + regras × nota emitida (cliente certo, tomador, valor, código, município de incidência do ISS, Lei 12.741, texto de IRRF, conta no corpo, núcleo da descrição).

A descrição é comparada por partes, não por igualdade de texto: a equipe escreve o rodapé (Lei 12.741, conta) de jeitos diferentes em cada nota.

## Como incluir o próximo lote

1. Pôr os arquivos em `raw/` (de preferência `.eml` do pedido e `.xml` da nota).
2. Acrescentar o caso em `data/casos.json` e o texto do pedido em `data/inputs/` sem as respostas da equipe.
3. Rodar `build_gabarito.py`.
4. Rótulos: rodar um extrator de LLM, conferir a saída e corrigir à mão em `rotulos_extracao.json` (bem mais rápido que escrever do zero).
5. Atualizar o cadastro com o histórico, nunca com as notas do próprio lote de teste.

## Limitações conhecidas

- 5 pedidos não medem acurácia; servem para validar o desenho, o schema e o harness.
- O cadastro saiu das mesmas notas, então a medida de nota composta é otimista.
- A regra de município de incidência cobre só o item 12 da LC 116; falta o resto do art. 3º.
- O parser lê o layout do DANFSe v2.0; com o XML da nota ele vira dispensável.
- Os extratores `claude`, `claude-code`, `ollama` e `openai` foram testados só com respostas simuladas; a primeira rodada real é a sua.
