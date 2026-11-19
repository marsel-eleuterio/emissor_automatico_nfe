# Contexto para o Claude Code

Automação da emissão de NFS-e a partir dos pedidos que chegam por email num escritório de contabilidade: ler o pedido, extrair os campos com um LLM, aprovar com um clique, emitir pela API da Sefin Nacional e responder ao cliente com PDF e XML. O plano completo, com decisões, arquitetura, estados da nota e fases, está em `docs/PLANO.md`.

Estamos na **Fase 0**: medir com o harness deste repositório se um LLM extrai os pedidos bem o bastante, antes de construir o worker. O desenvolvimento não pode gerar custo: notebook Windows com RTX 4070 de 8 GB, Ollama, o plano Pro do Claude, o Google AI Pro (Gemini, com US$ 10 por mês de crédito no Google Cloud / GenAI pelo Google Developer Program) e o Google Workspace do escritório. As contas pessoais do Marsel (plano Pro da Anthropic e Google AI Pro) servem só para validar o MVP; na entrega, a produção passa a usar só chaves e contas do escritório.

## Regras

- Português em tudo: código, comentários, mensagens, relatórios e docs, no estilo do código que já existe.
- O LLM só extrai campos do email. Código de serviço, alíquota, retenções, Lei 12.741 e município de incidência do ISS vêm do cadastro e das regras em `harness/compor.py`, nunca do modelo.
- `raw/`, `data/`, `data_lote2/`, `*.msg`, `reports/avaliacao_*` e `reports/saidas_*` têm dados pessoais e bancários de clientes. Não copie esses dados para commits, issues, prompts de serviços externos ou qualquer lugar fora do notebook. O repositório é privado e o `.gitignore` já deixa esses arquivos de fora.
- Dado real de cliente só passa pelo Ollama local, pelo Claude (`--extrator claude-code`) ou por nível pago que não treina com os dados: Gemini num projeto com faturamento, pago com o crédito do Google AI Pro (`NFSE_NIVEL_PAGO=1`). Níveis gratuitos (Gemini, Groq, GitHub Models) só recebem lote anonimizado. Fora do notebook, o extrator `openai` exige `NFSE_DADOS_ANONIMIZADOS=1` ou `NFSE_NIVEL_PAGO=1`. Não contorne essa trava nem declare nível pago sem faturamento ativo.
- Nenhuma conta pessoal no código: chaves, IDs de projeto e emails vêm do ambiente (`.env` no notebook, Secret Manager na VM), para a entrega ser só trocar segredos. O worker e qualquer código que rode sem o Marsel na frente usam chave de API ou o Ollama, nunca o `claude -p` logado no plano: o extrator `claude-code` é só para o eval no notebook.
- Rótulos (`data/rotulos_extracao.json`) e gabarito (`data/gabarito_notas.json`) não mudam para um extrator passar. Divergência é resultado; só corrija rótulo com evidência no email.
- Depois de mexer no harness, rode `python -I tests/test_encanamento.py`. Nenhuma dependência nova sem necessidade: hoje só `jsonschema`.
- Ambiente Windows + PowerShell. Rode os scripts com `python -I` (cada script acerta o próprio `sys.path`) e abra arquivos com `encoding="utf-8"`.

## Mapa

| Caminho | O que é |
| --- | --- |
| `docs/PLANO.md` | Plano completo (cópia do doc online) |
| `schema/extracao_v1.json` | JSON Schema da saída do extrator |
| `harness/prompt_v1.md`, `harness/prompt_v2.md` | Prompts de sistema do extrator (`prompt_v2.md` é o padrão; sobrescrevível via `NFSE_PROMPT`) |
| `harness/extratores.py` | Extratores: `oraculo`, `regex`, `claude`, `claude-code`, `ollama`, `openai`, `replay` |
| `harness/compor.py` | Cadastro + extração → campos da nota (inclui fallback de `descricao_padrao` e `incluir_banco_sempre`) |
| `harness/avaliar.py`, `harness/run_eval.py` | Comparação campo a campo e relatórios em `reports/` |
| `harness/comparar.py` | Tabela modelo × campo em `reports/comparativo.md` (ou `--lote data_lote2` → `reports/comparativo_data_lote2.md`) |
| `harness/anonimizar.py` | Gera `data_anon/` trocando dados pessoais/bancários para testes em níveis gratuitos |
| `harness/parse_danfse.py`, `harness/build_gabarito.py` | PDF do DANFSe nacional e NFS-e municipal de SP → gabarito |
| `data/`, `data_lote2/` | Casos, textos dos pedidos, rótulos, gabarito e cadastro (dados reais, fora do git) |
| `tests/test_encanamento.py` | Schema, rótulos, anonimizador, regras do Lote 2 e extratores com respostas simuladas |
| `scripts/` | `setup.ps1` prepara o ambiente; `eval_local.ps1` roda os modelos locais |

## Comandos (PowerShell, na raiz)

```powershell
python -I tests/test_encanamento.py
python -I harness/run_eval.py --extrator oraculo                         # só as regras
python -I harness/run_eval.py --extrator regex                           # linha de base
python -I harness/run_eval.py --extrator ollama --modelo gemma4:12b      # com NFSE_OLLAMA_PENSAR=0
python -I harness/run_eval.py --extrator claude-code --modelo haiku      # Claude pelo plano Pro
python -I harness/run_eval.py --extrator replay --replay reports/saidas_<extrator>_<data>.json
python -I harness/comparar.py
python -I harness/comparar.py --lote data_lote2
powershell -ExecutionPolicy Bypass -File scripts/eval_local.ps1 -ComClaude
```

Resultado atual:
- **Lote 1 (`data/`, 5 pedidos / 6 notas — `reports/comparativo.md`):** oráculo `114/114`, `claude-code:sonnet` `114/114`, `claude-code:haiku` `114/114` (v1) / `49/49` nota composta (v2), `gemini-3.5-flash-lite` (`data_anon/`) `111/114`, `ollama:gemma4:12b:sem-pensar` `103/114` (47/49 nota composta), `regex` `102/114`.
- **Lote 2 (`data_lote2/`, 22 pedidos / 24 NFS-e — `reports/comparativo_data_lote2.md`, com `prompt_v2.md`):** oráculo `463/476` (203/216 nota composta; 7 divergências são erros manuais da Lei 12.741 nos PDFs e 4 são pedidos recorrentes sem tomador/valor), `claude-code:sonnet` `454/476` (254/260 extração, 200/216 nota composta), `claude-code:haiku` `449/476` (251/260, 198/216), `ollama:gemma4:12b:sem-pensar` `442/476` (245/260, 197/216 — salto de +38 pts sobre v1), `regex` `336/462`.

## Próximos passos

1. Fechar com o escritório as 4 pendências de escopo do MVP (mapa da carteira, volume, procuração eletrônica vs A1, demanda de NF-e/WhatsApp) e obter as alíquotas mensais do Simples.
2. Montar o cadastro a partir do histórico real (Jettax), não das notas de teste, e reavaliar a nota composta.
3. Coletar amostra complementar em `.eml` + XML (retenções de ISS/IRRF/INSS, tomador PF, anexos, mais NF-e) e ler XML da NFS-e no lugar do PDF.
4. Testar procuração eletrônica na produção restrita da Sefin Nacional e iniciar a Fase 1: worker (Gmail → extração → checagens → planilha) com a máquina de estados e reserva de DPS descritas em `docs/PLANO.md`.

## Decisões que só mudam conversando

- Aprovação humana antes de emitir. O envio ao cliente é automático, mas só depois da nota autorizada, com texto fixo de modelo.
- SQLite é a fonte da verdade; a planilha do Google é só a tela da equipe.
- A emissão nunca reenvia às cegas: em timeout, consulta a DPS na Sefin antes de tentar de novo.
- Contas pessoais do Marsel só até validar o MVP; na entrega, chaves e contas do escritório (checklist em `docs/PLANO.md`, Entrega ao escritório). A produção nunca usa as credenciais do plano Pro.
