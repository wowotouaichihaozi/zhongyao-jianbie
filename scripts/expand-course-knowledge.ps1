param(
    [Parameter(Mandatory = $true)]
    [string]$CorpusDirectory,
    [Parameter(Mandatory = $true)]
    [string]$IndexPath,
    [int]$MinimumMegabytes = 100,
    [int]$MaximumMegabytes = 110
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CorpusDirectory = [System.IO.Path]::GetFullPath($CorpusDirectory)
$IndexPath = [System.IO.Path]::GetFullPath($IndexPath)
$OutputRoot = Join-Path $CorpusDirectory 'knowledge-expansion-20260728'
$ManifestPath = Join-Path $ProjectRoot 'docs\knowledge-expansion-sources.json'
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('qianzhixuehang-knowledge-' + [guid]::NewGuid().ToString('N'))
$MaxBytes = [int64]$MaximumMegabytes * 1MB
$MinBytes = [int64]$MinimumMegabytes * 1MB

$Sources = @(
    @{ Id='freertos'; Name='FreeRTOS Kernel'; Repo='https://github.com/FreeRTOS/FreeRTOS-Kernel.git'; License='MIT'; Dirs=@('include','portable','examples') },
    @{ Id='riscv'; Name='RISC-V ISA Manual'; Repo='https://github.com/riscv/riscv-isa-manual.git'; License='CC-BY-4.0'; Dirs=@('src') },
    @{ Id='lvgl'; Name='LVGL'; Repo='https://github.com/lvgl/lvgl.git'; License='MIT'; Dirs=@('docs','src','examples') },
    @{ Id='tinyusb'; Name='TinyUSB'; Repo='https://github.com/hathach/tinyusb.git'; License='MIT'; Dirs=@('docs','src','examples') },
    @{ Id='lwip'; Name='lwIP'; Repo='https://github.com/lwip-tcpip/lwip.git'; License='BSD-3-Clause'; Dirs=@('doc','src') },
    @{ Id='pico-sdk'; Name='Raspberry Pi Pico SDK'; Repo='https://github.com/raspberrypi/pico-sdk.git'; License='BSD-3-Clause'; Dirs=@('src','docs','lib') },
    @{ Id='cmsis5'; Name='Arm CMSIS 5'; Repo='https://github.com/ARM-software/CMSIS_5.git'; License='Apache-2.0'; Dirs=@('CMSIS/Core','CMSIS/DSP','CMSIS/RTOS2','CMSIS/NN') },
    @{ Id='cmsis6'; Name='Arm CMSIS 6'; Repo='https://github.com/ARM-software/CMSIS_6.git'; License='Apache-2.0'; Dirs=@('CMSIS/Core','CMSIS/CoreValidation','CMSIS/Documentation') },
    @{ Id='cpputest'; Name='CppUTest'; Repo='https://github.com/cpputest/cpputest.git'; License='BSD-3-Clause'; Dirs=@('docs','include','src','examples') },
    @{ Id='unity'; Name='Unity Test'; Repo='https://github.com/ThrowTheSwitch/Unity.git'; License='MIT'; Dirs=@('docs','src','examples') },
    @{ Id='mbed-os'; Name='Arm Mbed OS'; Repo='https://github.com/ARMmbed/mbed-os.git'; License='Apache-2.0'; Dirs=@('platform','hal','drivers','rtos','events','connectivity','storage') }
)

$AllowedExtensions = @('.md','.markdown','.rst','.txt','.adoc','.tex','.h','.hpp','.c','.cc','.cpp','.s','.asm','.ld','.cmake','.py')
$SkipParts = @('.git','node_modules','build','dist','coverage','vendor','third_party','test','tests')
$SeenHashes = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$Manifest = [System.Collections.Generic.List[object]]::new()
$WrittenBytes = [int64]0

function Get-SafeFileName([string]$RelativePath, [string]$Hash) {
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($RelativePath)
    $stem = [regex]::Replace($stem, '[^a-zA-Z0-9._-]+', '-')
    if ([string]::IsNullOrWhiteSpace($stem)) { $stem = 'knowledge' }
    if ($stem.Length -gt 72) { $stem = $stem.Substring(0, 72) }
    return "$stem-$($Hash.Substring(0, 12)).txt"
}

function Test-SkippedPath([string]$Path) {
    $segments = $Path -split '[\\/]'
    foreach ($part in $SkipParts) {
        if ($segments -contains $part) { return $true }
    }
    return $false
}

function Get-Sha256([byte[]]$Bytes) {
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $algorithm.Dispose()
    }
}

try {
    New-Item -ItemType Directory -Force -Path $TempRoot, $CorpusDirectory, (Split-Path $IndexPath -Parent), (Split-Path $ManifestPath -Parent) | Out-Null
    if (Test-Path -LiteralPath $OutputRoot) {
        $resolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot)
        $resolvedCorpus = [System.IO.Path]::GetFullPath($CorpusDirectory).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
        if (-not $resolvedOutput.StartsWith($resolvedCorpus, [System.StringComparison]::OrdinalIgnoreCase) -or
            [System.IO.Path]::GetFileName($resolvedOutput) -ne 'knowledge-expansion-20260728') {
            throw "Refusing to replace unexpected output path: $resolvedOutput"
        }
        Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

    foreach ($source in $Sources) {
        if ($WrittenBytes -ge $MaxBytes) { break }
        $clonePath = Join-Path $TempRoot $source.Id
        & git clone --depth 1 --filter=blob:none --sparse --quiet $source.Repo $clonePath
        if ($LASTEXITCODE -ne 0) { throw "Failed to clone $($source.Repo)" }
        & git -C $clonePath sparse-checkout set --cone @($source.Dirs)
        if ($LASTEXITCODE -ne 0) { throw "Failed sparse checkout for $($source.Id)" }
        $commit = (& git -C $clonePath rev-parse HEAD).Trim()
        $sourceOutput = Join-Path $OutputRoot $source.Id
        New-Item -ItemType Directory -Force -Path $sourceOutput | Out-Null
        $sourceBytes = [int64]0
        $sourceFiles = 0

        $files = Get-ChildItem -LiteralPath $clonePath -Recurse -File | Where-Object {
            $AllowedExtensions -contains $_.Extension.ToLowerInvariant() -and
            -not (Test-SkippedPath $_.FullName) -and
            $_.Length -gt 40 -and $_.Length -le 2MB
        } | Sort-Object @{ Expression = { if ($_.Extension -in @('.md','.markdown','.rst','.txt','.adoc','.tex')) { 0 } else { 1 } } }, FullName

        foreach ($file in $files) {
            if ($WrittenBytes -ge $MaxBytes) { break }
            $relative = $file.FullName.Substring($clonePath.Length).TrimStart('\','/').Replace('\','/')
            $raw = [System.IO.File]::ReadAllBytes($file.FullName)
            $hash = Get-Sha256 $raw
            if (-not $SeenHashes.Add($hash)) { continue }
            try {
                $body = [System.Text.UTF8Encoding]::new($false, $true).GetString($raw)
            } catch {
                continue
            }
            if ([string]::IsNullOrWhiteSpace($body)) { continue }
            $header = @(
                "Source: $($source.Name)",
                "Repository: $($source.Repo)",
                "Commit: $commit",
                "License: $($source.License)",
                "Original-Path: $relative",
                "SHA256: $hash",
                "Imported-At: 2026-07-28",
                '',
                '---',
                ''
            ) -join "`n"
            $normalized = ($header + $body.Replace("`r`n", "`n").Replace("`r", "`n")).Trim() + "`n"
            $encoded = [System.Text.UTF8Encoding]::new($false).GetBytes($normalized)
            if ($WrittenBytes + $encoded.Length -gt $MaxBytes) { continue }
            $target = Join-Path $sourceOutput (Get-SafeFileName $relative $hash)
            [System.IO.File]::WriteAllBytes($target, $encoded)
            $WrittenBytes += $encoded.Length
            $sourceBytes += $encoded.Length
            $sourceFiles += 1
        }

        $Manifest.Add([ordered]@{
            id = $source.Id
            name = $source.Name
            repository = $source.Repo
            commit = $commit
            license = $source.License
            importedAt = '2026-07-28'
            normalizedFiles = $sourceFiles
            normalizedBytes = $sourceBytes
        })
    }

    if ($WrittenBytes -lt $MinBytes) {
        throw "Only $([math]::Round($WrittenBytes / 1MB, 2)) MB generated; minimum is $MinimumMegabytes MB"
    }

    $manifestPayload = [ordered]@{
        generatedAt = '2026-07-28'
        outputDirectory = 'knowledge-expansion-20260728'
        normalizedBytes = $WrittenBytes
        sha256Deduplicated = $true
        sources = $Manifest
    }
    [System.IO.File]::WriteAllText($ManifestPath, ($manifestPayload | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))

    $env:KNOWLEDGE_CORPUS_DIRECTORY = $CorpusDirectory
    $env:KNOWLEDGE_INDEX_PATH = $IndexPath
    $python = @'
import os
from pathlib import Path
from backend.course_knowledge import CourseKnowledgeBase

corpus = Path(os.environ["KNOWLEDGE_CORPUS_DIRECTORY"])
index = Path(os.environ["KNOWLEDGE_INDEX_PATH"])
knowledge = CourseKnowledgeBase(corpus_dir=corpus, cache_path=index)
knowledge._load()
print(f"indexed_chunks={len(knowledge._chunks)} index_bytes={index.stat().st_size}")
'@
    $python | python -
    if ($LASTEXITCODE -ne 0) { throw 'Course knowledge index rebuild failed' }

    Write-Host "Knowledge expansion complete: $([math]::Round($WrittenBytes / 1MB, 2)) MB"
    Write-Host "Manifest: $ManifestPath"
    Write-Host "Index: $IndexPath"
} finally {
    if (Test-Path -LiteralPath $TempRoot) {
        $resolvedTemp = [System.IO.Path]::GetFullPath($TempRoot)
        $systemTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        if ($resolvedTemp.StartsWith($systemTemp, [System.StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedTemp -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
