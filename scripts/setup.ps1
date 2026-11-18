<#
Prepara o ambiente no Windows: cria a .venv, instala as dependências, roda os testes
e mostra placa de vídeo, RAM, Ollama e o login do Claude Code.

Uso, da raiz do projeto:
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
$ErrorActionPreference = "Stop"
$raiz = Split-Path $PSScriptRoot -Parent
Set-Location $raiz

function Existe([string]$comando) {
    return [bool](Get-Command $comando -ErrorAction SilentlyContinue)
}

if (-not (Existe "python")) {
    throw "Python não encontrado no PATH. Instale o Python 3.11+ ou rode este script num terminal do Anaconda."
}

$py = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Criando a .venv..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Não consegui criar a .venv." }
}

Write-Host "Instalando dependências..."
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Falha no pip install." }

Write-Host ""
Write-Host "== Testes do harness"
& $py -I tests\test_encanamento.py
if ($LASTEXITCODE -ne 0) { throw "Os testes falharam." }

Write-Host ""
Write-Host "== Placa de vídeo e memória"
if (Existe "nvidia-smi") {
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
} else {
    Write-Host "nvidia-smi não encontrado."
}
$ramGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Write-Host "RAM: $ramGB GB (o qwen3.6:35b-a3b só vale com 32 GB)"

Write-Host ""
Write-Host "== Ollama"
if (Existe "ollama") {
    ollama --version
    ollama list
} else {
    Write-Host "Ollama não encontrado: https://ollama.com/download"
}

Write-Host ""
Write-Host "== Claude Code no terminal (usado pelo extrator claude-code)"
if (Existe "claude") {
    claude --version
    claude auth status --text
} else {
    Write-Host "O comando claude não está no PATH. A extensão do VS Code não instala o CLI do terminal:"
    Write-Host "veja https://code.claude.com/docs/en/setup"
}
if ($env:ANTHROPIC_API_KEY) {
    Write-Host "Aviso: ANTHROPIC_API_KEY está definida. O Claude Code no terminal cobraria essa chave em vez do plano."
}

Write-Host ""
Write-Host "Pronto. No VS Code, selecione o interpretador .venv (Ctrl+Shift+P > Python: Select Interpreter)."
