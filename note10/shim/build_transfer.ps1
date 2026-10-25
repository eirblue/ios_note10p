param([string]$NdkRoot='C:\Program Files\Unity\Hub\Editor\2021.3.20f1\Editor\Data\PlaybackEngines\AndroidPlayer\NDK',
      [string]$OutputDirectory='')
$ErrorActionPreference = 'Stop'
$transferTools = Join-Path $NdkRoot 'toolchains/llvm/prebuilt/windows-x86_64/bin'
$transferOutput = Join-Path (Split-Path -Parent $PSScriptRoot) 'private/xnu-transfer'
if ($OutputDirectory) { $transferOutput = [System.IO.Path]::GetFullPath($OutputDirectory) }
New-Item -ItemType Directory -Force -Path $transferOutput | Out-Null
& (Join-Path $transferTools 'clang.exe') --target=aarch64-none-elf '-march=armv8.2-a' -Wall -Wextra -Werror -c (Join-Path $PSScriptRoot 'xnu_transfer.S') -o (Join-Path $transferOutput 'transfer.o')
if ($LASTEXITCODE -ne 0) { throw 'Transfer entry assembly failed' }
& (Join-Path $transferTools 'ld.lld.exe') -T (Join-Path $PSScriptRoot 'cap_link.ld') (Join-Path $transferOutput 'transfer.o') -o (Join-Path $transferOutput 'transfer.elf')
if ($LASTEXITCODE -ne 0) { throw 'Transfer ELF link failed' }
Write-Output "PC research ELF only; no flash/boot packaging: $transferOutput"
