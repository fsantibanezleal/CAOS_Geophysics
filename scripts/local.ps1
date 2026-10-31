param([ValidateSet('dev','build','check','stop')][string]$Command = 'check')
$ErrorActionPreference = 'Stop'; Set-Location (Join-Path $PSScriptRoot '..')
switch ($Command) {
  'dev' { Set-Location frontend; npm run dev }
  'build' { Set-Location frontend; npm ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }; npm run build; if ($LASTEXITCODE -ne 0) { throw 'frontend build failed' } }
  'check' {
    $py = Join-Path '.venv-pipeline' 'Scripts/python.exe'; if (-not (Test-Path $py)) { $py = Join-Path '.venv-pipeline' 'bin/python' }
    if (-not (Test-Path $py)) { throw 'Run scripts/setup.ps1 -Gpu to create .venv-pipeline before validation.' }
    & $py tests/run_validation.py; if ($LASTEXITCODE -ne 0) { throw "Scientific validation failed with exit code $LASTEXITCODE" }
    & $py scripts/check_artifacts.py; if ($LASTEXITCODE -ne 0) { throw 'Artifact integrity gate failed.' }
    & $py scripts/check_phase_assets.py; if ($LASTEXITCODE -ne 0) { throw 'M13 asset integrity gate failed.' }
    & $py scripts/check_sdd_convergence.py; if ($LASTEXITCODE -ne 0) { throw 'SDD convergence integrity gate failed.' }
    & $py scripts/check_template_residue.py; if ($LASTEXITCODE -ne 0) { throw 'Template residue gate failed.' }
    Push-Location frontend
    try { npm test; if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }; npm run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' } } finally { Pop-Location }
  }
  'stop' { Write-Host 'Stop this app with Ctrl+C in the terminal that launched its dev server. Other Node processes are not touched.' }
}
