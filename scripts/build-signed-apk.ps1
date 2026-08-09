param(
    [string]$MobileDir = (Join-Path $PSScriptRoot "..\mobile"),
    [string]$SigningDir = (Join-Path $env:USERPROFILE ".codex\android-signing")
)

$ErrorActionPreference = "Stop"
$credentialPath = Join-Path $SigningDir "qianzhi-release-v2.credential.xml"
$keystorePath = Join-Path $SigningDir "qianzhi-release-v2.jks"
if (-not (Test-Path -LiteralPath $credentialPath) -or -not (Test-Path -LiteralPath $keystorePath)) {
    throw "Signing material is missing from $SigningDir"
}

$credential = Import-Clixml -LiteralPath $credentialPath
$password = $credential.GetNetworkCredential().Password
$env:QIANZHI_KEYSTORE_PATH = $keystorePath
$env:QIANZHI_KEYSTORE_PASSWORD = $password
$env:QIANZHI_KEY_ALIAS = "qianzhi-release"
$env:QIANZHI_KEY_PASSWORD = $password
$env:ANDROID_SDK_ROOT = Join-Path $env:USERPROFILE ".android-sdk"

try {
    Push-Location $MobileDir
    npm run build:native
    if ($LASTEXITCODE -ne 0) { throw "Native web build failed" }
    npx cap sync android
    if ($LASTEXITCODE -ne 0) { throw "Capacitor sync failed" }
    $localGradle = Join-Path $env:USERPROFILE ".gradle-distributions\gradle-8.14.3\bin\gradle.bat"
    if (Test-Path -LiteralPath $localGradle) {
        & $localGradle -p android assembleRelease
    } else {
        & ".\android\gradlew.bat" -p android assembleRelease
    }
    if ($LASTEXITCODE -ne 0) { throw "Android release build failed" }

    $apkPath = Join-Path $MobileDir "android\app\build\outputs\apk\release\app-release.apk"
    $metadataPath = Join-Path $MobileDir "android\app\build\outputs\apk\release\output-metadata.json"
    if (-not (Test-Path -LiteralPath $apkPath) -or -not (Test-Path -LiteralPath $metadataPath)) {
        throw "Signed release output is missing"
    }

    $buildToolsRoot = Join-Path $env:ANDROID_SDK_ROOT "build-tools"
    $buildTools = Get-ChildItem -LiteralPath $buildToolsRoot -Directory |
        Sort-Object { [version]$_.Name } -Descending |
        Select-Object -First 1
    $apkSigner = Join-Path $buildTools.FullName "apksigner.bat"
    if (-not (Test-Path -LiteralPath $apkSigner)) { throw "apksigner was not found" }
    & $apkSigner verify --verbose --print-certs $apkPath
    if ($LASTEXITCODE -ne 0) { throw "APK signature verification failed" }

    $metadata = Get-Content -Raw -LiteralPath $metadataPath | ConvertFrom-Json
    $versionName = [string]$metadata.elements[0].versionName
    if (-not $versionName) { throw "APK version name is missing" }
    $releaseDir = Join-Path $MobileDir "releases"
    New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
    $releaseName = "qianzhi-mobile-$versionName.apk"
    $releasePath = Join-Path $releaseDir $releaseName
    Copy-Item -LiteralPath $apkPath -Destination $releasePath -Force
    $hash = (Get-FileHash -LiteralPath $releasePath -Algorithm SHA256).Hash
    "$hash  $releaseName" | Set-Content -LiteralPath "$releasePath.sha256" -Encoding ascii
    Write-Output "Signed APK: $releasePath"
    Write-Output "SHA-256: $hash"
} finally {
    Pop-Location
    Remove-Item Env:QIANZHI_KEYSTORE_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:QIANZHI_KEYSTORE_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:QIANZHI_KEY_ALIAS -ErrorAction SilentlyContinue
    Remove-Item Env:QIANZHI_KEY_PASSWORD -ErrorAction SilentlyContinue
}
