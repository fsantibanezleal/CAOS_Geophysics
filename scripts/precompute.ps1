param([string]$Case = 'all', [string]$Output = '')
$ErrorActionPreference = 'Stop'; Set-Location (Join-Path $PSScriptRoot '..')
$py = Join-Path '.venv-pipeline' 'Scripts/python.exe'; if (-not (Test-Path $py)) { $py = Join-Path '.venv-pipeline' 'bin/python' }
$argsList = @('data-pipeline/rebuild.py'); if ($Case -ne 'all') { $argsList += @('--cases', $Case) }; if ($Output) { $argsList += @('--output', $Output) }
& $py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
