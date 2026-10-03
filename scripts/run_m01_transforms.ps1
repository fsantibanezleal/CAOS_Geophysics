$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $RepoRoot '.venv-m01/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $PythonPath)) { throw 'Create the owned .venv-m01 using requirements-m01-transforms.txt first.' }
& $PythonPath (Join-Path $RepoRoot 'data-pipeline/gravity_transforms.py') @args
exit $LASTEXITCODE
