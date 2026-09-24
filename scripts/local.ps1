param([ValidateSet('dev','build','check','stop')][string]$Command = 'check')
$ErrorActionPreference = 'Stop'; Set-Location (Join-Path $PSScriptRoot '..')
switch ($Command) {
  'dev' { Set-Location frontend; npm run dev }
  'build' { Set-Location frontend; npm install; npm run build }
  'check' { $py = Join-Path '.venv-pipeline' 'Scripts/python.exe'; if (-not (Test-Path $py)) { $py = Join-Path '.venv-pipeline' 'bin/python' }; & $py -m pytest; & python scripts/check_artifacts.py; & python scripts/check_template_residue.py }
  'stop' { Write-Host 'Stop this app with Ctrl+C in the terminal that launched its dev server. Other Node processes are not touched.' }
}
