$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
try {
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:YOLO_CONFIG_DIR = Join-Path $projectRoot '.backend-check\ultralytics'
    $python = & (Join-Path $PSScriptRoot 'ensure-local-runtime.ps1')
    & $python (Join-Path $PSScriptRoot 'check-backend-code.py')
    if ($LASTEXITCODE -ne 0) { throw 'Backend source or dependency check failed.' }
    if ($env:BENCAO_NONINTERACTIVE -ne '1') { Read-Host 'Press Enter to close' }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($env:BENCAO_NONINTERACTIVE -ne '1') { Read-Host 'Press Enter to close' }
    exit 1
}
