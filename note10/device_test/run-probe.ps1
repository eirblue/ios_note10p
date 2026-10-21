param(
    [switch]$Check,
    [string]$Session,
    [string]$Adb,
    [string]$Out
)
$ErrorActionPreference = 'Stop'
$probePython = $null
$probePrefix = @()
foreach ($probeCandidate in @('C:\Python314\python.exe', 'C:\Python313\python.exe', 'C:\Python312\python.exe')) {
    if (Test-Path -LiteralPath $probeCandidate) { $probePython = $probeCandidate; break }
}
if (-not $probePython) {
    $probeCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($probeCommand) { $probePython = $probeCommand.Source; $probePrefix = @('-3') }
}
if (-not $probePython) { throw 'Python 3 is required. Use python note10/device_test/run_probe.py --run.' }
$probeArgs = @('-X', 'utf8', (Join-Path $PSScriptRoot 'run_probe.py'))
if ($Session) { $probeArgs += @('--pull-only', $Session) }
elseif (-not $Check) { $probeArgs += '--run' }
if ($Adb) { $probeArgs += @('--adb', $Adb) }
if ($Out) { $probeArgs += @('--out', $Out) }
& $probePython @probePrefix @probeArgs
exit $LASTEXITCODE
