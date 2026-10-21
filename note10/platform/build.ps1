param(
    [string]$NdkRoot = 'C:\Program Files\Unity\Hub\Editor\2021.3.20f1\Editor\Data\PlaybackEngines\AndroidPlayer\NDK'
)
$ErrorActionPreference = 'Stop'
$platformCompiler = Join-Path $NdkRoot 'toolchains\llvm\prebuilt\windows-x86_64\bin\clang.exe'
if (-not (Test-Path -LiteralPath $platformCompiler)) { throw 'NDK clang missing' }
$platformOutput = Join-Path (Split-Path -Parent $PSScriptRoot) 'private'
New-Item -ItemType Directory -Force -Path $platformOutput | Out-Null
$platformSource = Join-Path $PSScriptRoot 'gicv2.c'
$platformTests = Join-Path $PSScriptRoot 'test_gicv2.c'
& $platformCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $platformSource $platformTests -o (Join-Path $platformOutput 'gicv2-tests')
if ($LASTEXITCODE -ne 0) { throw 'Android GICv2 model test build failed' }
$platformFlags = @('-march=armv8.2-a','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-mgeneral-regs-only','-mstrict-align','-Wall','-Wextra','-Werror','-c')
& $platformCompiler --target=aarch64-none-elf @platformFlags $platformSource -o (Join-Path $platformOutput 'gicv2-freestanding.o')
if ($LASTEXITCODE -ne 0) { throw 'GICv2 ELF object build failed' }
& $platformCompiler --target=arm64-apple-darwin @platformFlags $platformSource -o (Join-Path $platformOutput 'gicv2-macho.o')
if ($LASTEXITCODE -ne 0) { throw 'GICv2 Apple arm64 object build failed' }
$platformMmio = Join-Path $PSScriptRoot 'gicv2_mmio.c'
& $platformCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $platformSource $platformMmio (Join-Path $PSScriptRoot 'test_gicv2_mmio.c') -o (Join-Path $platformOutput 'gicv2-mmio-tests')
if ($LASTEXITCODE -ne 0) { throw 'GICv2 memory-buffer adapter test build failed' }
& $platformCompiler --target=aarch64-none-elf @platformFlags $platformMmio -o (Join-Path $platformOutput 'gicv2-mmio-freestanding.o')
if ($LASTEXITCODE -ne 0) { throw 'GICv2 MMIO ELF object build failed' }
& $platformCompiler --target=arm64-apple-darwin @platformFlags $platformMmio -o (Join-Path $platformOutput 'gicv2-mmio-macho.o')
if ($LASTEXITCODE -ne 0) { throw 'GICv2 MMIO Mach-O object build failed' }
Write-Output "GICv2 objects and memory-buffer Android tests built in $platformOutput"
