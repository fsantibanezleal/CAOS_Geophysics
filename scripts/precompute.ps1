param([string]$Case = 'all', [string]$Output = 'data/experiments/precompute')
$ErrorActionPreference = 'Stop'; Set-Location (Join-Path $PSScriptRoot '..')
$py = Join-Path '.venv-pipeline' 'Scripts/python.exe'; if (-not (Test-Path $py)) { $py = Join-Path '.venv-pipeline' 'bin/python' }
$argsList = @('data-pipeline/rebuild.py', '--output', $Output); if ($Case -ne 'all') { $argsList += @('--cases', $Case) }
& $py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
