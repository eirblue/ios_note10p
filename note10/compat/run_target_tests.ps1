# Explicit device-test runner: no boot, root, unlock or flash operations.
$ErrorActionPreference = 'Stop'
$testRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$testTarget = Get-Content -LiteralPath (Join-Path $testRoot 'note10/target.json') -Raw | ConvertFrom-Json
$testResearch = Join-Path $testRoot $testTarget.research_directory
$testSystemVersion = Join-Path $testResearch 'userland/System/Library/CoreServices/SystemVersion.plist'
if (-not (Test-Path -LiteralPath $testSystemVersion)) { throw 'Active target userland missing' }
$testAdb = Join-Path $testRoot 'host-tools/platform-tools/adb.exe'
$testModel = & $testAdb -d shell getprop ro.product.model
if ($LASTEXITCODE -ne 0 -or -not $testModel) { throw 'No authorized USB device' }
if ($testModel.Trim() -ne 'SM-N976N') { throw 'Expected SM-N976N' }
$testPrivate = Join-Path $testRoot 'note10/private'
$testResultDir = Join-Path $testPrivate ((Split-Path $testResearch -Leaf) + '-results')
New-Item -ItemType Directory -Force -Path $testResultDir | Out-Null
$testRemote = '/data/local/tmp/codex-note10-target-' + [guid]::NewGuid().ToString('N').Substring(0,12)
$testInputs = @('auth-branch-tests','pac-instruction-tests','fixup24-tests','loader-value-tests','hint-sites-tests','auth-branch-oracle.bin','pac-instruction-oracle.bin','fixup24-corpus.bin','fixup24-corpus.pages','launchd-fixups.bin','dyld-fixups.bin','SpringBoard-fixups.bin','hint-copies/launchd.hint-brk.sites','hint-copies/dyld.hint-brk.sites','hint-copies/SpringBoard.hint-brk.sites')
$testPlans = @(
    @{test='auth-branch-tests';args=@('auth-branch-oracle.bin')},
    @{test='pac-instruction-tests';args=@('pac-instruction-oracle.bin')},
    @{test='fixup24-tests';args=@('fixup24-corpus.bin','fixup24-corpus.pages')},
    @{test='loader-value-tests';args=@('fixup24-corpus.bin','launchd-fixups.bin','dyld-fixups.bin','SpringBoard-fixups.bin')},
    @{test='hint-sites-tests';args=@('launchd.hint-brk.sites','dyld.hint-brk.sites','SpringBoard.hint-brk.sites')}
)
& $testAdb -d shell mkdir $testRemote
if ($LASTEXITCODE -ne 0) { throw 'Temporary directory creation failed' }
$testHashes = @()
try {
    foreach ($testInput in $testInputs) {
        $testLocal = Join-Path $testPrivate $testInput
        & $testAdb -d push $testLocal ($testRemote + '/' + (Split-Path $testInput -Leaf))
        if ($LASTEXITCODE -ne 0) { throw 'Push failed' }
        $testHashes += [ordered]@{file=$testInput;sha256=(Get-FileHash -LiteralPath $testLocal -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
    foreach ($testPlan in $testPlans) {
        $testExecutable = $testRemote + '/' + $testPlan.test
        & $testAdb -d shell chmod 700 $testExecutable
        if ($LASTEXITCODE -ne 0) { throw 'Chmod failed' }
        $testArguments = @($testPlan.args | ForEach-Object { $testRemote + '/' + $_ })
        $testOutput = & $testAdb -d shell $testExecutable @testArguments
        $testExit = $LASTEXITCODE
        $testOutput | Set-Content -LiteralPath (Join-Path $testResultDir ($testPlan.test + '.json')) -Encoding utf8
        $testOutput
        if ($testExit -ne 0) { throw ('Device test failed: ' + $testPlan.test) }
    }
    [ordered]@{target=$testTarget;inputs=$testHashes} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $testResultDir 'inputs-sha256.json') -Encoding utf8
} finally {
    foreach ($testInput in $testInputs) { & $testAdb -d shell rm -f ($testRemote + '/' + (Split-Path $testInput -Leaf)) }
    & $testAdb -d shell rmdir $testRemote
    if ($LASTEXITCODE -ne 0) { throw 'Temporary directory cleanup failed' }
}
