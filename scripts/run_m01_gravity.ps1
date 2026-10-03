# Python is deliberately selected from this worktree's isolated environment.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv-m01\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv-m01 and install data-pipeline/requirements-m01.txt first.'
}
& $pythonPath (Join-Path $repoRoot 'data-pipeline\gravity_processing.py') @args
exit $LASTEXITCODE
