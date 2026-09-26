param(
    [string]$Output = '',
    [string]$EdiSource = '',
    [switch]$ReuseTrained,
    [switch]$SkipNumerical
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Version = (Get-Content (Join-Path $RepoRoot 'VERSION') -Raw).Trim()
if (-not $Output) { $Output = "data/experiments/release-$Version" }
if (-not $EdiSource) { $EdiSource = 'data/downloads/clear-lake/USGS-GMEG.2022.cl061.edi' }
$CandidateRoot = [IO.Path]::GetFullPath((Join-Path $RepoRoot $Output))
$ExperimentsRoot = [IO.Path]::GetFullPath((Join-Path $RepoRoot 'data/experiments'))
if (-not $CandidateRoot.StartsWith($ExperimentsRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Release output must be a named directory inside ignored data/experiments; canonical artifacts are protected.'
}
$SourcePath = [IO.Path]::GetFullPath((Join-Path $RepoRoot $EdiSource))
if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
    throw "Missing hash-pinned Clear Lake EDI source. Obtain the station file identified in data/source-ledger.json and save it at $SourcePath before baking."
}
$Python = Join-Path $RepoRoot '.venv-pipeline/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Missing .venv-pipeline; run scripts/setup.ps1 -Gpu first.' }

function Invoke-ReleasePython([string[]]$ScriptArgs) {
    & $Python @ScriptArgs
    if ($LASTEXITCODE -ne 0) { throw "Release stage failed: $($ScriptArgs[0]) (exit $LASTEXITCODE)" }
}

Set-Location $RepoRoot
if (-not $SkipNumerical) {
    $RebuildArgs = @('data-pipeline/rebuild.py', '--output', $CandidateRoot, '--resume')
    if ($ReuseTrained) { $RebuildArgs += @('--reuse-trained-from', (Join-Path $RepoRoot 'data/derived/v2/models')) }
    Invoke-ReleasePython $RebuildArgs
}
Invoke-ReleasePython @('data-pipeline/edi.py', '--fixture-bundle', '--bootstrap-samples', '128', '--calibration-realizations', '48', '--output', (Join-Path $CandidateRoot 'edi'))
Invoke-ReleasePython @('scripts/build_field_screen.py', '--source', $SourcePath, '--output-root', $CandidateRoot)
Invoke-ReleasePython @('data-pipeline/catalog.py', '--root', $CandidateRoot)
Invoke-ReleasePython @('scripts/check_artifacts.py', '--data', $CandidateRoot)
Invoke-ReleasePython @('scripts/validate_recovery.py', '--data', $CandidateRoot, '--report', (Join-Path $CandidateRoot 'validation.json'))
Invoke-ReleasePython @('scripts/validate_fwi_exports.py', '--data', $CandidateRoot, '--report', (Join-Path $CandidateRoot 'fwi-replay.json'))
Write-Host "Candidate release validated: $CandidateRoot"
Write-Host 'Canonical data/derived/v2, Git branches and public hosts were not changed.'
