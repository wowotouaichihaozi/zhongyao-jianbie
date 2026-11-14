$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$launcherLock = $null
try {
    $stateRoot = Join-Path $projectRoot '.local-system'
    New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
    try {
        $launcherLock = [System.IO.File]::Open((Join-Path $stateRoot 'launcher.lock'), [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    } catch [System.IO.IOException] {
        Write-Host 'The local system is already starting or running. Keep its original window open.'
        $services = Join-Path $stateRoot 'services.json'
        if (Test-Path -LiteralPath $services) {
            try {
                $state = Get-Content -LiteralPath $services -Raw | ConvertFrom-Json
                $url = "http://127.0.0.1:$($state.frontendPort)/login"
                Write-Host "Local system: $url"
                if ($env:BENCAO_NO_BROWSER -ne '1') { & (Join-Path $PSScriptRoot 'open-browser.ps1') -Url $url }
            } catch { Write-Host 'Wait for the original startup window to display its address.' }
        }
        return
    }
    $python = & (Join-Path $PSScriptRoot 'ensure-local-runtime.ps1')
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    & $python (Join-Path $PSScriptRoot 'start-local-system.py')
    if ($LASTEXITCODE -ne 0) { throw 'Local startup failed; see .local-system/logs.' }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
} finally {
    if ($launcherLock) { $launcherLock.Dispose() }
}
