[CmdletBinding()]
param(
    [string]$OutputDirectory = "portable\qianzhixuehang-portable-win-x64",
    [string]$PythonVersion = "3.12.6",
    [switch]$ExcludeFfmpeg,
    [switch]$SkipChecksums
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$PortableRoot = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "portable"))
$OutputPath = if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
}
else {
    [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $OutputDirectory))
}
$portablePrefix = $PortableRoot.TrimEnd('\') + '\'
if (-not $OutputPath.StartsWith($portablePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDirectory must be a child of $PortableRoot"
}

$SourcePython = Join-Path $ProjectRoot "backend\venv\Scripts\python.exe"
$SourceSitePackages = Join-Path $ProjectRoot "backend\venv\Lib\site-packages"
$CacheDir = Join-Path $ProjectRoot ".portable-cache"
$PythonArchive = Join-Path $CacheDir "python-$PythonVersion-embed-amd64.zip"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$PythonRuntime = Join-Path $OutputPath "runtime\python"
$FfmpegRuntime = Join-Path $OutputPath "runtime\ffmpeg"

function ConvertFrom-CodePoints([int[]]$CodePoints) {
    return -join ($CodePoints | ForEach-Object { [char]$_ })
}

$KnowledgeDirectoryName = "rag" + (ConvertFrom-CodePoints @(0x6587, 0x6863))
$LaunchFileName = (ConvertFrom-CodePoints @(0x4E00, 0x952E, 0x542F, 0x52A8)) + ".bat"
$StopFileName = (ConvertFrom-CodePoints @(0x505C, 0x6B62, 0x670D, 0x52A1)) + ".bat"
$CheckFileName = (ConvertFrom-CodePoints @(0x68C0, 0x67E5, 0x5B8C, 0x6574, 0x6027)) + ".bat"
$ConfigureFileName = (ConvertFrom-CodePoints @(0x914D, 0x7F6E, 0x63A5, 0x53E3, 0x5BC6, 0x94A5)) + ".bat"
$BasicFrameworkDoc = (ConvertFrom-CodePoints @(0x57FA, 0x672C, 0x6846, 0x67B6)) + ".md"
$CompetitionDoc = (ConvertFrom-CodePoints @(0x8D5B, 0x9898)) + ".md"

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label is missing: $Path"
    }
}

function Invoke-Robocopy([string]$Source, [string]$Destination, [string[]]$Extra = @()) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Copy source is missing: $Source"
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $arguments = @(
        $Source,
        $Destination,
        "/E",
        "/COPY:DAT",
        "/DCOPY:DAT",
        "/R:2",
        "/W:1",
        "/XJ",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP"
    ) + $Extra
    & robocopy @arguments | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "Robocopy failed with exit code ${LASTEXITCODE}: $Source"
    }
}

function Resolve-CommandTarget([string]$Name) {
    $command = Get-Command $Name -ErrorAction Stop
    $item = Get-Item -LiteralPath $command.Source
    if ($item.LinkType -and $item.Target) {
        $target = @($item.Target)[0]
        return [System.IO.Path]::GetFullPath([string]$target)
    }
    return [System.IO.Path]::GetFullPath($item.FullName)
}

Assert-File $SourcePython "Prepared Python 3.12 virtual environment"
Assert-File (Join-Path $ProjectRoot "frontend\dist\index.html") "Learner frontend build"
Assert-File (Join-Path $ProjectRoot "admin\dist\index.html") "Admin frontend build"
Assert-File (Join-Path $ProjectRoot "ppth5\dist-web\index.html") "PPT frontend build"
Assert-File (Join-Path $ProjectRoot "backend\data\course_knowledge_index.json") "Knowledge index"
Assert-File (Join-Path $ProjectRoot "backend\data\tcm_qa_pairs.json") "TCM QA index"
Assert-File (Join-Path $ProjectRoot "backend\data\tcm_graph_index.json") "TCM graph retrieval index"
Assert-File (Join-Path $ProjectRoot "backend\data\tcm_hybrid_corpus.db.gz") "TCM hybrid corpus"
Assert-File (Join-Path $ProjectRoot "backend\data\tcm_hybrid_corpus_manifest.json") "TCM hybrid corpus manifest"

& $SourcePython -c "import bcrypt, cv2, fastapi, fitz, flask, json_repair, langgraph, oss2, paramiko, pydantic, requests, torch, torchvision, ultralytics, uvicorn, waitress" *> $null
if ($LASTEXITCODE -ne 0) {
    throw "The prepared backend virtual environment is incomplete. Install both requirement files before building."
}

if (Test-Path -LiteralPath $OutputPath) {
    if (-not $OutputPath.StartsWith($portablePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove an output path outside the portable directory."
    }
    Remove-Item -LiteralPath $OutputPath -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $OutputPath, $CacheDir | Out-Null

Write-Host "[1/7] Copying application source and prebuilt frontends..."
$backendSource = Join-Path $ProjectRoot "backend"
Invoke-Robocopy $backendSource (Join-Path $OutputPath "backend") @(
    "/XD",
    (Join-Path $backendSource "venv"),
    (Join-Path $backendSource ".venv"),
    (Join-Path $backendSource "tests"),
    (Join-Path $backendSource "__pycache__"),
    (Join-Path $backendSource ".pytest_cache"),
    (Join-Path $backendSource "data"),
    (Join-Path $backendSource "generated"),
    "/XF",
    ".env",
    "*.pyc",
    "*.log",
    "*.sqlite",
    "*.sqlite3",
    "*.sqlite3-*"
)

$frontendSource = Join-Path $ProjectRoot "frontend"
Invoke-Robocopy $frontendSource (Join-Path $OutputPath "frontend") @(
    "/XD",
    "node_modules",
    (Join-Path $frontendSource "node_modules"),
    (Join-Path $frontendSource ".git"),
    (Join-Path $frontendSource "test-results"),
    (Join-Path $frontendSource "playwright-report"),
    (Join-Path $frontendSource "coverage"),
    "/XF",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.log"
)

$adminSource = Join-Path $ProjectRoot "admin"
Invoke-Robocopy $adminSource (Join-Path $OutputPath "admin") @(
    "/XD",
    "node_modules",
    (Join-Path $adminSource "node_modules"),
    (Join-Path $adminSource ".git"),
    (Join-Path $adminSource "test-results"),
    (Join-Path $adminSource "playwright-report"),
    (Join-Path $adminSource "coverage"),
    "/XF",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.log"
)

$pptSource = Join-Path $ProjectRoot "ppth5"
Invoke-Robocopy $pptSource (Join-Path $OutputPath "ppth5") @(
    "/XD",
    "node_modules",
    (Join-Path $pptSource "node_modules"),
    (Join-Path $pptSource ".git"),
    (Join-Path $pptSource "backend\.venv"),
    (Join-Path $pptSource "backend\venv"),
    (Join-Path $pptSource "backend\tests"),
    (Join-Path $pptSource "backend\__pycache__"),
    "/XF",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.pyc",
    "*.log"
)

$imgSource = Join-Path $ProjectRoot "img"
if (Test-Path -LiteralPath $imgSource -PathType Container) {
    Invoke-Robocopy $imgSource (Join-Path $OutputPath "img") @("/XD", "node_modules", (Join-Path $imgSource "node_modules"), (Join-Path $imgSource ".git"))
}

Write-Host "[2/7] Copying the knowledge corpus and clean index..."
Invoke-Robocopy (Join-Path $ProjectRoot $KnowledgeDirectoryName) (Join-Path $OutputPath $KnowledgeDirectoryName)
$backendData = Join-Path $OutputPath "backend\data"
New-Item -ItemType Directory -Force -Path `
    $backendData, `
    (Join-Path $backendData "extract_cache"), `
    (Join-Path $backendData "multimodal_inputs"), `
    (Join-Path $backendData "profile_portraits"), `
    (Join-Path $OutputPath "backend\generated\video") | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "backend\data\course_knowledge_index.json") -Destination $backendData -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "backend\data\tcm_qa_pairs.json") -Destination $backendData -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "backend\data\tcm_graph_index.json") -Destination $backendData -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "backend\data\tcm_hybrid_corpus.db.gz") -Destination $backendData -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "backend\data\tcm_hybrid_corpus_manifest.json") -Destination $backendData -Force
$langGraphData = Join-Path $ProjectRoot "backend\data\langgraph"
if (Test-Path -LiteralPath $langGraphData -PathType Container) {
    Invoke-Robocopy $langGraphData (Join-Path $backendData "langgraph")
}

Write-Host "[3/7] Preparing the self-contained Python $PythonVersion runtime..."
if (-not (Test-Path -LiteralPath $PythonArchive -PathType Leaf)) {
    Write-Host "Downloading the official Python embeddable runtime once..."
    Invoke-WebRequest -UseBasicParsing -Uri $PythonUrl -OutFile $PythonArchive
}
New-Item -ItemType Directory -Force -Path $PythonRuntime | Out-Null
Expand-Archive -LiteralPath $PythonArchive -DestinationPath $PythonRuntime -Force
$pthFile = Join-Path $PythonRuntime "python312._pth"
Assert-File $pthFile "Python embedded path configuration"
@("python312.zip", ".", "Lib\site-packages", "import site") | Set-Content -LiteralPath $pthFile -Encoding ASCII
Invoke-Robocopy $SourceSitePackages (Join-Path $PythonRuntime "Lib\site-packages") @(
    "/XD",
    "__pycache__",
    "~*",
    "/XF",
    "*.pyc"
)

Write-Host "[4/7] Preparing optional FFmpeg tools..."
$ffmpegBin = Join-Path $FfmpegRuntime "bin"
if ($ExcludeFfmpeg) {
    Write-Host "  FFmpeg omitted for the sub-1GB competition submission."
}
else {
    $ffmpegSource = Resolve-CommandTarget "ffmpeg"
    $ffprobeSource = Resolve-CommandTarget "ffprobe"
    New-Item -ItemType Directory -Force -Path $ffmpegBin | Out-Null
    Copy-Item -LiteralPath $ffmpegSource -Destination (Join-Path $ffmpegBin "ffmpeg.exe") -Force
    Copy-Item -LiteralPath $ffprobeSource -Destination (Join-Path $ffmpegBin "ffprobe.exe") -Force
    $ffmpegHome = Split-Path -Parent (Split-Path -Parent $ffmpegSource)
    foreach ($licenseName in @("LICENSE", "README.txt")) {
        $licensePath = Join-Path $ffmpegHome $licenseName
        if (Test-Path -LiteralPath $licensePath -PathType Leaf) {
            Copy-Item -LiteralPath $licensePath -Destination $FfmpegRuntime -Force
        }
    }
}

Write-Host "[5/7] Adding launchers, documentation, and dependency inventory..."
$packageScripts = Join-Path $OutputPath "scripts"
$licenses = Join-Path $OutputPath "licenses"
$docs = Join-Path $OutputPath "docs"
New-Item -ItemType Directory -Force -Path $packageScripts, $licenses, $docs, (Join-Path $OutputPath "logs"), (Join-Path $OutputPath "state") | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\start-portable.ps1") -Destination $packageScripts -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\stop-portable.ps1") -Destination $packageScripts -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\check-portable.ps1") -Destination $packageScripts -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\verify-manifest.py") -Destination $packageScripts -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\launch.bat") -Destination (Join-Path $OutputPath $LaunchFileName) -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\stop.bat") -Destination (Join-Path $OutputPath $StopFileName) -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\check.bat") -Destination (Join-Path $OutputPath $CheckFileName) -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\configure.bat") -Destination (Join-Path $OutputPath $ConfigureFileName) -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "portable\README-portable.md") -Destination (Join-Path $OutputPath "README.md") -Force

foreach ($docName in @("README.md", "AGENT_ARCHITECTURE.md", "SCORING_MATRIX.md", "THIRD_PARTY_NOTICES.md", $BasicFrameworkDoc, $CompetitionDoc)) {
    $docPath = Join-Path $ProjectRoot $docName
    if (Test-Path -LiteralPath $docPath -PathType Leaf) {
        $destinationName = if ($docName -eq "README.md") { "PROJECT-README.md" } else { $docName }
        Copy-Item -LiteralPath $docPath -Destination (Join-Path $docs $destinationName) -Force
    }
}
Copy-Item -LiteralPath (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES.md") -Destination (Join-Path $licenses "PROJECT-THIRD-PARTY-NOTICES.md") -Force
$pythonLicense = Join-Path $PythonRuntime "LICENSE.txt"
if (Test-Path -LiteralPath $pythonLicense) {
    Copy-Item -LiteralPath $pythonLicense -Destination (Join-Path $licenses "PYTHON-LICENSE.txt") -Force
}
if (Test-Path -LiteralPath (Join-Path $FfmpegRuntime "LICENSE")) {
    Copy-Item -LiteralPath (Join-Path $FfmpegRuntime "LICENSE") -Destination (Join-Path $licenses "FFMPEG-LICENSE.txt") -Force
}

$freeze = & $SourcePython -m pip freeze --local
$freeze | Set-Content -LiteralPath (Join-Path $OutputPath "DEPENDENCIES.lock.txt") -Encoding UTF8
[ordered]@{
    product = "QianZhiXueHang"
    packageType = "windows-x64-portable"
    builtAt = (Get-Date).ToString("o")
    python = $PythonVersion
    backendPort = 3000
    pptInternalPort = 8765
    secretsIncluded = $false
    userDataIncluded = $false
    ffmpegIncluded = (-not $ExcludeFfmpeg)
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputPath "BUILD-INFO.json") -Encoding UTF8

Write-Host "[6/7] Verifying that private and development-only files were excluded..."
$unexpectedEnv = @(Get-ChildItem -LiteralPath $OutputPath -Recurse -Force -File | Where-Object { $_.Name -eq ".env" })
if ($unexpectedEnv.Count -gt 0) { throw "A private .env file entered the portable package." }
$unexpectedDb = @(Get-ChildItem -LiteralPath (Join-Path $OutputPath "backend\data") -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "\.sqlite" })
if ($unexpectedDb.Count -gt 0) { throw "A runtime SQLite database entered the portable package." }
$unexpectedNodeModules = @(Get-ChildItem -LiteralPath $OutputPath -Recurse -Directory -Force | Where-Object { $_.Name -eq "node_modules" })
if ($unexpectedNodeModules.Count -gt 0) { throw "node_modules entered the portable package." }

$portablePython = Join-Path $PythonRuntime "python.exe"
$env:PYTHONDONTWRITEBYTECODE = "1"
& $portablePython -c "import bcrypt, cv2, fastapi, fitz, flask, json_repair, langgraph, oss2, paramiko, pydantic, requests, torch, torchvision, ultralytics, uvicorn, waitress; print('portable imports ok')"
if ($LASTEXITCODE -ne 0) { throw "The embedded Python runtime could not import all required libraries." }
if (-not $ExcludeFfmpeg) {
    & (Join-Path $ffmpegBin "ffmpeg.exe") -version *> $null
    if ($LASTEXITCODE -ne 0) { throw "The bundled FFmpeg executable failed." }
}

Write-Host "[7/7] Generating SHA-256 manifest..."
if (-not $SkipChecksums) {
    $manifestPath = Join-Path $OutputPath "MANIFEST.json"
    $entries = [System.Collections.Generic.List[object]]::new()
    $files = @(Get-ChildItem -LiteralPath $OutputPath -Recurse -File | Where-Object { $_.FullName -ne $manifestPath } | Sort-Object FullName)
    $index = 0
    foreach ($file in $files) {
        $index++
        if ($index % 500 -eq 0) { Write-Host "  hashed $index/$($files.Count) files" }
        $relative = $file.FullName.Substring($OutputPath.Length).TrimStart('\').Replace('\', '/')
        $entries.Add([ordered]@{
            path = $relative
            size = [int64]$file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        })
    }
    $entries | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

$allFiles = @(Get-ChildItem -LiteralPath $OutputPath -Recurse -File)
$totalBytes = ($allFiles | Measure-Object Length -Sum).Sum
$knowledgeFiles = @(Get-ChildItem -LiteralPath (Join-Path $OutputPath $KnowledgeDirectoryName) -Recurse -File)
$knowledgeBytes = ($knowledgeFiles | Measure-Object Length -Sum).Sum
Write-Host ""
Write-Host "Portable package ready: $OutputPath"
Write-Host "Files: $($allFiles.Count)"
Write-Host "Size: $([math]::Round($totalBytes / 1GB, 2)) GB"
Write-Host "Knowledge corpus: $($knowledgeFiles.Count) files / $([math]::Round($knowledgeBytes / 1MB, 1)) MB"
