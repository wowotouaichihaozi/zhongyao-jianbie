$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'This package requires 64-bit Windows 10/11.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$archive = Join-Path $projectRoot '.runtime\python-win64.zip'
$checksumFile = $archive + '.sha256'
if (-not (Test-Path -LiteralPath $archive) -or -not (Test-Path -LiteralPath $checksumFile)) {
    throw 'Bundled Python runtime missing. Extract the complete package with backend validation dependencies.'
}
$expected = (Get-Content -LiteralPath $checksumFile -Raw).Trim()
$stream = [System.IO.File]::OpenRead($archive)
$sha = [System.Security.Cryptography.SHA256]::Create()
try { $digest = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
finally { $sha.Dispose(); $stream.Dispose() }
if ($digest -ne $expected) { throw 'Python runtime archive is damaged. Extract the delivery ZIP again.' }
# A short per-user cache avoids Windows path-length limits on other computers.
$cacheRoot = Join-Path $env:LOCALAPPDATA 'BC'
$runtime = Join-Path $cacheRoot ('py-' + $digest.Substring(0, 12))
$python = Join-Path $runtime 'python.exe'
$ready = Join-Path $runtime '.ready'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$lock = $null
$deadline = [DateTime]::UtcNow.AddMinutes(5)
while (-not $lock) {
    try { $lock = [System.IO.File]::Open((Join-Path $runtime '.extract.lock'), [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None) }
    catch [System.IO.IOException] {
        if ([DateTime]::UtcNow -ge $deadline) { throw 'Another launcher is still preparing Python. Close it and retry.' }
        Start-Sleep -Milliseconds 400
    }
}
try {
$cachedDigest = if (Test-Path -LiteralPath $ready) { (Get-Content -LiteralPath $ready -Raw).Trim() } else { '' }
if ($cachedDigest -ne $digest -or -not (Test-Path -LiteralPath $python)) {
    Write-Host 'Preparing bundled Python and backend dependencies (first launch only)...'
    New-Item -ItemType Directory -Path $runtime -Force | Out-Null
    [System.Reflection.Assembly]::LoadWithPartialName('System.IO.Compression.FileSystem') | Out-Null
    $zip = [System.IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $zip.Entries) {
            $destination = [System.IO.Path]::GetFullPath((Join-Path $runtime $entry.FullName))
            if (-not $destination.StartsWith($runtime + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid runtime archive path.' }
            if (-not $entry.Name) { [System.IO.Directory]::CreateDirectory($destination) | Out-Null; continue }
            [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($destination)) | Out-Null
            $inputStream = $entry.Open()
            $outputStream = [System.IO.File]::Create($destination)
            try { $inputStream.CopyTo($outputStream) } finally { $outputStream.Dispose(); $inputStream.Dispose() }
        }
    } finally { $zip.Dispose() }
    & $python -c 'import flask, waitress, bcrypt, dotenv, requests, fitz, langgraph, torch, torchvision, ultralytics, fastapi, uvicorn' *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Bundled backend dependency check failed.' }
    Set-Content -LiteralPath $ready -Value $digest -Encoding ASCII
}
} finally { $lock.Dispose() }
Write-Output $python
