param(
    [string]$NdkRoot = 'C:\Program Files\Unity\Hub\Editor\2021.3.20f1\Editor\Data\PlaybackEngines\AndroidPlayer\NDK'
)
$ErrorActionPreference = 'Stop'
$probeRoot = Split-Path -Parent $PSScriptRoot
$probeCompiler = Join-Path $NdkRoot 'toolchains\llvm\prebuilt\windows-x86_64\bin\clang.exe'
if (-not (Test-Path -LiteralPath $probeCompiler)) { throw "NDK clang not found: $probeCompiler" }
$probeOutputDir = Join-Path $PSScriptRoot 'private'
New-Item -ItemType Directory -Force -Path $probeOutputDir | Out-Null
$probeOutput = Join-Path $probeOutputDir 'cpu-probe'
& $probeCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror (Join-Path $PSScriptRoot 'cpu_probe.c') -o $probeOutput
if ($LASTEXITCODE -ne 0) { throw 'CPU diagnostic build failed' }
Get-FileHash -LiteralPath $probeOutput -Algorithm SHA256
