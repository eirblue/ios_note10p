param(
    [string]$NdkRoot = 'C:\Program Files\Unity\Hub\Editor\2021.3.20f1\Editor\Data\PlaybackEngines\AndroidPlayer\NDK'
)
$ErrorActionPreference = 'Stop'
$compatToolDir = Join-Path $NdkRoot 'toolchains\llvm\prebuilt\windows-x86_64\bin'
$compatCompiler = Join-Path $compatToolDir 'clang.exe'
if (-not (Test-Path -LiteralPath $compatCompiler)) { throw "NDK clang not found: $compatCompiler" }
$compatOutput = Join-Path (Split-Path -Parent $PSScriptRoot) 'private'
New-Item -ItemType Directory -Force -Path $compatOutput | Out-Null
$compatSource = Join-Path $PSScriptRoot 'auth_branch.c'
$compatTests = Join-Path $PSScriptRoot 'test_auth_branch.c'
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $compatSource $compatTests -o (Join-Path $compatOutput 'auth-branch-tests')
if ($LASTEXITCODE -ne 0) { throw 'Android test executable build failed' }
$compatFlags = @('-march=armv8.2-a', '-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector', '-mgeneral-regs-only', '-mstrict-align', '-Wall', '-Wextra', '-Werror', '-c')
& $compatCompiler --target=aarch64-none-elf @compatFlags $compatSource -o (Join-Path $compatOutput 'auth-branch-freestanding.o')
if ($LASTEXITCODE -ne 0) { throw 'Freestanding ELF object build failed' }
& $compatCompiler --target=arm64-apple-darwin @compatFlags $compatSource -o (Join-Path $compatOutput 'auth-branch-macho.o')
if ($LASTEXITCODE -ne 0) { throw 'Apple arm64 object build failed' }
$compatRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$fixupSource = Join-Path $PSScriptRoot 'fixup24.c'
$fixupTests = Join-Path $PSScriptRoot 'test_fixup24.c'
$fixupReferenceDir = Join-Path $compatRoot 'research\ios27'
$fixupReference = Join-Path $fixupReferenceDir 'fixup-chains.h'
$fixupReferenceMeta = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'fixup-reference.json') -Raw | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $fixupReference)) { throw 'Run python note10/compat/fetch_fixup_reference.py first' }
$fixupStream = [System.IO.File]::OpenRead($fixupReference)
$fixupHasher = [System.Security.Cryptography.SHA256]::Create()
try {
    $fixupDigest = [System.BitConverter]::ToString($fixupHasher.ComputeHash($fixupStream)).Replace('-', '').ToLowerInvariant()
} finally {
    $fixupStream.Dispose()
    $fixupHasher.Dispose()
}
if ($fixupDigest -ne $fixupReferenceMeta.sha256) { throw 'Pinned Apple test reference hash mismatch' }
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror '-I' $fixupReferenceDir $fixupSource $fixupTests -o (Join-Path $compatOutput 'fixup24-tests')
if ($LASTEXITCODE -ne 0) { throw 'Fixup24 test build failed' }
& $compatCompiler --target=aarch64-none-elf @compatFlags $fixupSource -o (Join-Path $compatOutput 'fixup24-freestanding.o')
if ($LASTEXITCODE -ne 0) { throw 'Fixup24 ELF object build failed' }
& $compatCompiler --target=arm64-apple-darwin @compatFlags $fixupSource -o (Join-Path $compatOutput 'fixup24-macho.o')
if ($LASTEXITCODE -ne 0) { throw 'Fixup24 Apple arm64 object build failed' }
$loaderValueSource = Join-Path $PSScriptRoot 'fixup_value.c'
$loaderImportSource = Join-Path $PSScriptRoot 'import_table.c'
$loaderTests = Join-Path $PSScriptRoot 'test_loader_values.c'
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror '-I' $fixupReferenceDir $fixupSource $loaderValueSource $loaderImportSource $loaderTests -o (Join-Path $compatOutput 'loader-value-tests')
if ($LASTEXITCODE -ne 0) { throw 'Loader value tests build failed' }
foreach ($loaderComponent in @('fixup_value', 'import_table')) {
    $loaderComponentSource = Join-Path $PSScriptRoot ($loaderComponent + '.c')
    & $compatCompiler --target=aarch64-none-elf @compatFlags $loaderComponentSource -o (Join-Path $compatOutput ($loaderComponent + '-freestanding.o'))
    if ($LASTEXITCODE -ne 0) { throw 'Loader component ELF object build failed' }
    & $compatCompiler --target=arm64-apple-darwin @compatFlags $loaderComponentSource -o (Join-Path $compatOutput ($loaderComponent + '-macho.o'))
    if ($LASTEXITCODE -ne 0) { throw 'Loader component Apple arm64 object build failed' }
}
$qarmaSource = Join-Path $PSScriptRoot 'qarma.c'
$softPacSource = Join-Path $PSScriptRoot 'soft_pac.c'
$softPacTests = Join-Path $PSScriptRoot 'test_soft_pac.c'
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $qarmaSource $softPacSource $compatSource $fixupSource $loaderValueSource $softPacTests -o (Join-Path $compatOutput 'soft-pac-tests')
if ($LASTEXITCODE -ne 0) { throw 'Software PAC tests build failed' }
foreach ($pacComponent in @('qarma', 'soft_pac')) {
    $pacComponentSource = Join-Path $PSScriptRoot ($pacComponent + '.c')
    & $compatCompiler --target=aarch64-none-elf @compatFlags $pacComponentSource -o (Join-Path $compatOutput ($pacComponent + '-freestanding.o'))
    if ($LASTEXITCODE -ne 0) { throw 'PAC component ELF object build failed' }
    & $compatCompiler --target=arm64-apple-darwin @compatFlags $pacComponentSource -o (Join-Path $compatOutput ($pacComponent + '-macho.o'))
    if ($LASTEXITCODE -ne 0) { throw 'PAC component Apple arm64 object build failed' }
}
$pacInstructionSource = Join-Path $PSScriptRoot 'pac_instruction.c'
$pacInstructionTests = Join-Path $PSScriptRoot 'test_pac_instruction.c'
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $qarmaSource $softPacSource $pacInstructionSource $pacInstructionTests -o (Join-Path $compatOutput 'pac-instruction-tests')
if ($LASTEXITCODE -ne 0) { throw 'PAC instruction tests build failed' }
& $compatCompiler --target=aarch64-none-elf @compatFlags $pacInstructionSource -o (Join-Path $compatOutput 'pac_instruction-freestanding.o')
if ($LASTEXITCODE -ne 0) { throw 'PAC instruction ELF object build failed' }
& $compatCompiler --target=arm64-apple-darwin @compatFlags $pacInstructionSource -o (Join-Path $compatOutput 'pac_instruction-macho.o')
if ($LASTEXITCODE -ne 0) { throw 'PAC instruction Apple arm64 object build failed' }
$hintInterceptTests = Join-Path $PSScriptRoot 'test_hint_intercept.c'
$hintSitesSource = Join-Path $PSScriptRoot 'hint_sites.c'
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $qarmaSource $softPacSource $pacInstructionSource $hintSitesSource $hintInterceptTests -o (Join-Path $compatOutput 'hint-intercept-tests')
if ($LASTEXITCODE -ne 0) { throw 'Android hint interception experiment build failed' }
$hintSitesTests = Join-Path $PSScriptRoot 'test_hint_sites.c'
& $compatCompiler --target=aarch64-linux-android24 -O2 -fPIE -pie -Wall -Wextra -Werror $qarmaSource $softPacSource $pacInstructionSource $hintSitesSource $hintSitesTests -o (Join-Path $compatOutput 'hint-sites-tests')
if ($LASTEXITCODE -ne 0) { throw 'Hint site tests build failed' }
& $compatCompiler --target=aarch64-none-elf @compatFlags $hintSitesSource -o (Join-Path $compatOutput 'hint_sites-freestanding.o')
if ($LASTEXITCODE -ne 0) { throw 'Hint sites ELF object build failed' }
& $compatCompiler --target=arm64-apple-darwin @compatFlags $hintSitesSource -o (Join-Path $compatOutput 'hint_sites-macho.o')
if ($LASTEXITCODE -ne 0) { throw 'Hint sites Apple arm64 object build failed' }
Write-Output "Objects and Android tests built in $compatOutput"
