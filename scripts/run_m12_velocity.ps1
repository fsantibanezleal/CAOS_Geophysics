param(
    [ValidateSet('cpu', 'cuda')][string]$Device = 'cpu',
    [string]$Output,
    [ValidateRange(1, 10000)][int]$Epochs = 40,
    [switch]$Verify,
    [switch]$Fixture,
    [string]$Python
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Output)) { throw 'M12 requires an explicit absolute external -Output path.' }
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $Python) {
    foreach ($candidate in @('.venv-pipeline/Scripts/python.exe', '.venv-m12/Scripts/python.exe')) {
        $resolved = Join-Path $root $candidate
        if (Test-Path -LiteralPath $resolved) { $Python = $resolved; break }
    }
}
if (-not $Python) { throw 'Create an ignored local Python environment with NumPy, SciPy and PyTorch, or pass -Python.' }
Push-Location $root
try {
    $arguments = @('scripts/run_m12_velocity.py', '--output', $Output)
    if ($Verify) { $arguments += '--verify' }
    else {
        $arguments += @('--device', $Device, '--epochs', $Epochs)
        if ($Fixture) { $arguments += '--fixture' }
    }
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw "M12 pipeline exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
