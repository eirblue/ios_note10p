param([string]$NdkRoot='C:\Program Files\Unity\Hub\Editor\2021.3.20f1\Editor\Data\PlaybackEngines\AndroidPlayer\NDK')
$ErrorActionPreference = 'Stop'
$capTools = Join-Path $NdkRoot 'toolchains/llvm/prebuilt/windows-x86_64/bin'
$capOutput = Join-Path (Split-Path -Parent $PSScriptRoot) 'private/cap-probe'
New-Item -ItemType Directory -Force -Path $capOutput | Out-Null
& (Join-Path $capTools 'clang.exe') --target=aarch64-none-elf '-march=armv8.2-a' -Wall -Wextra -Werror -c (Join-Path $PSScriptRoot 'cap_entry.S') -o (Join-Path $capOutput 'cap-entry.o')
if ($LASTEXITCODE -ne 0) { throw 'Capability entry assembly failed' }
& (Join-Path $capTools 'ld.lld.exe') -T (Join-Path $PSScriptRoot 'cap_link.ld') (Join-Path $capOutput 'cap-entry.o') -o (Join-Path $capOutput 'cap-probe.elf')
if ($LASTEXITCODE -ne 0) { throw 'Capability ELF link failed' }
Write-Output "Privileged research ELF only, not a boot/flash image: $capOutput"
