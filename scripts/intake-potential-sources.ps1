param(
    [Parameter(Mandatory = $true)][string]$File,
    [Parameter(Mandatory = $true)][string]$Output,
    [string]$PythonPath = $env:GEOPHYSICS_INTAKE_PYTHON
)
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $PythonPath) { $PythonPath = Join-Path $RepoRoot '.venv-intake/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw 'Choose an isolated interpreter with -PythonPath or GEOPHYSICS_INTAKE_PYTHON; see guide 11.'
}
& $PythonPath -c 'import sys; raise SystemExit(0 if sys.prefix != sys.base_prefix else 2)'
if ($LASTEXITCODE -ne 0) { throw 'Source intake requires a virtualenv, not the global interpreter.' }
if (-not [IO.Path]::IsPathRooted($File)) { $File = Join-Path $RepoRoot $File }
if (-not [IO.Path]::IsPathRooted($Output)) { $Output = Join-Path $RepoRoot $Output }
& $PythonPath (Join-Path $RepoRoot 'data-pipeline/potential_sources.py') --file $File --output $Output
if ($LASTEXITCODE -ne 0) { throw "Potential-source intake failed (exit $LASTEXITCODE); existing bytes were not replaced." }
Write-Host '[potential-intake] Local inspection only; unresolved modelling gates remain open.'
