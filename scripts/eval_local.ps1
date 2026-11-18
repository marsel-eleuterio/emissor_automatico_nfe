<#
Roda o eval com os modelos do Ollama, com e sem raciocínio, e opcionalmente com o Claude
pelo plano (claude -p). No fim, monta reports\comparativo.md.

Uso, da raiz do projeto:
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_local.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_local.ps1 -Modelos "qwen3.5:9b" -SemPull
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_local.ps1 -ComClaude
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\eval_local.ps1 -SoClaude
#>
param(
    # Lista separada por vírgula (com -File, o PowerShell não monta arrays sozinho).
    [string]$Modelos = "qwen3.5:9b,gemma4:12b,qwen3:14b,qwen3.6:35b-a3b",
    [switch]$SemPull,
    [switch]$ComClaude,
    [switch]$SoClaude
)
$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

$py = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

if (-not $SoClaude) {
    if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
        throw "Ollama não encontrado. Instale em https://ollama.com/download ou use -SoClaude."
    }
    foreach ($m in ($Modelos -split ",")) {
        $m = $m.Trim()
        if (-not $m) { continue }
        if (-not $SemPull) {
            Write-Host ""
            Write-Host "== Baixando $m"
            ollama pull $m
        }
        foreach ($pensar in @("0", "1")) {
            $env:NFSE_OLLAMA_PENSAR = $pensar
            Write-Host ""
            Write-Host "== $m (raciocínio = $pensar)"
            & $py -I harness\run_eval.py --extrator ollama --modelo $m
        }
    }
    Remove-Item Env:NFSE_OLLAMA_PENSAR -ErrorAction SilentlyContinue
}

if ($ComClaude -or $SoClaude) {
    foreach ($m in @("haiku", "sonnet")) {
        Write-Host ""
        Write-Host "== Claude $m pelo plano"
        & $py -I harness\run_eval.py --extrator claude-code --modelo $m
    }
}

Write-Host ""
& $py -I harness\comparar.py
Write-Host "Comparativo em reports\comparativo.md"
