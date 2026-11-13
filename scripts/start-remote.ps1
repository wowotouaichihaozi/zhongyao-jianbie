$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
try {
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $runtimeRoot = Join-Path $projectRoot '.runtime'
    $bundledNode = Join-Path $runtimeRoot 'node\node.exe'
    if (Test-Path -LiteralPath $bundledNode) {
        $nodeExecutable = $bundledNode
    } elseif ($nodeCommand -and ([int]((& $nodeCommand.Source --version).TrimStart('v').Split('.')[0]) -ge 20)) {
        $nodeExecutable = $nodeCommand.Source
    } else {
        Write-Host 'Downloading Node.js LTS (first launch only)...'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $releases = Invoke-RestMethod -Uri 'https://nodejs.org/dist/index.json'
        $release = $releases | Where-Object { $_.lts -and $_.files -contains 'win-x64-zip' } | Select-Object -First 1
        if (-not $release) { throw 'No suitable Node.js LTS runtime found.' }
        $archiveName = "node-$($release.version)-win-x64.zip"
        $baseUrl = "https://nodejs.org/dist/$($release.version)"
        New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
        $archivePath = Join-Path $runtimeRoot $archiveName
        Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/$archiveName" -OutFile $archivePath
        $checksums = (Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/SHASUMS256.txt").Content
        $checksumLine = ($checksums -split "`n" | Where-Object { $_.Trim().EndsWith("  $archiveName") } | Select-Object -First 1)
        $expectedHash = ($checksumLine -split '\s+')[0]
        if (-not $expectedHash -or (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $expectedHash) { throw 'Node.js download checksum mismatch.' }
        Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeRoot -Force
        $extractedRoot = (Resolve-Path -LiteralPath (Join-Path $runtimeRoot "node-$($release.version)-win-x64")).Path
        $resolvedRuntime = (Resolve-Path -LiteralPath $runtimeRoot).Path
        if (-not $extractedRoot.StartsWith($resolvedRuntime + '\')) { throw 'Runtime path check failed.' }
        Move-Item -LiteralPath $extractedRoot -Destination (Join-Path $runtimeRoot 'node')
        $nodeExecutable = $bundledNode
    }
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        if ($attempt -eq 0 -and $env:BENCAO_NO_BROWSER -ne '1') { & $nodeExecutable (Join-Path $PSScriptRoot 'local-web.mjs') --open }
        else { & $nodeExecutable (Join-Path $PSScriptRoot 'local-web.mjs') }
        if ($LASTEXITCODE -eq 0) { break }
        if ($attempt -eq 2) { throw 'Local server stopped repeatedly. See .local-web/errors.log.' }
        Write-Host 'Local server stopped unexpectedly; restarting in 2 seconds...'
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
