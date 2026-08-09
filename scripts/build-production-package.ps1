[CmdletBinding()]
param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$builder = Join-Path $PSScriptRoot "build_production_package.py"
$arguments = @($builder)
if ($OutputPath) {
    $arguments += @("--output", $OutputPath)
}

& python @arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
