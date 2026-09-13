param([string]$Case = 'all', [int]$Seed = 42, [string]$Output = '')
$ErrorActionPreference = 'Stop'; Set-Location (Join-Path $PSScriptRoot '..')
$py = Join-Path '.venv-pipeline' 'Scripts/python.exe'; if (-not (Test-Path $py)) { $py = Join-Path '.venv-pipeline' 'bin/python' }
$argsList = @('data-pipeline/run.py', $Case, '--seed', $Seed); if ($Output) { $argsList += @('--output', $Output) }
& $py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
