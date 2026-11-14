$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
try {
    $python = & (Join-Path $PSScriptRoot 'ensure-local-runtime.ps1')
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    & $python (Join-Path $PSScriptRoot 'start-local-system.py')
    if ($LASTEXITCODE -ne 0) { throw 'Local startup failed; see .local-system/logs.' }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
