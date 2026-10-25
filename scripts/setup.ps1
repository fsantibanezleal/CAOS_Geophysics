param([switch]$Gpu, [switch]$Notebooks, [switch]$M08, [switch]$Api)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3.12' } else { 'python' }
function VenvPy($dir) { $p = Join-Path $dir 'Scripts/python.exe'; if (-not (Test-Path $p)) { $p = Join-Path $dir 'bin/python' }; return $p }
if ($Api) {
  Write-Host '[setup] creating isolated .venv-api'
  if (-not (Test-Path '.venv-api')) { Invoke-Expression "$py -m venv .venv-api" }
  $apiPython = VenvPy '.venv-api'
  & $apiPython -m pip install --upgrade pip -q
  & $apiPython -m pip install -r requirements-api.txt -r requirements-dev.txt -q
  & $apiPython -m pip check
  Write-Host '[setup] API environment ready. Run .\.venv-api\Scripts\python.exe -m pytest tests\api -q.'
  exit 0
}
if ($Notebooks) {
  Write-Host '[setup] creating isolated .venv-notebooks'
  if (-not (Test-Path '.venv-notebooks')) { Invoke-Expression "$py -m venv .venv-notebooks" }
  # PowerShell variables are case-insensitive: `$notebooks` aliases the
  # `[switch]$Notebooks` parameter and attempts to assign a path to a switch.
  $notebookPython = VenvPy '.venv-notebooks'
  & $notebookPython -m pip install --upgrade pip -q
  & $notebookPython -m pip install -r notebooks/requirements.txt -q
  Write-Host '[setup] notebook environment ready. Run .\.venv-notebooks\Scripts\python.exe scripts/run_notebooks.py --check --tmp <device-temp-root>.'
  exit 0
}
if ($M08) {
  Write-Host '[setup] creating isolated .venv-m08'
  if (-not (Test-Path '.venv-m08')) { Invoke-Expression "$py -m venv .venv-m08" }
  $m08Python = VenvPy '.venv-m08'
  & $m08Python -m pip install --upgrade pip -q
  & $m08Python -m pip install -r data-pipeline/requirements-m08.txt -q
  & $m08Python -m pip check
  Write-Host '[setup] M08 environment ready. Set M08_TEST_SCIENCE_PYTHON to .venv-m08/Scripts/python.exe for local validation.'
  exit 0
}
Write-Host '[setup] creating root .venv and offline .venv-pipeline'
if (-not (Test-Path '.venv')) { Invoke-Expression "$py -m venv .venv" }
if (-not (Test-Path '.venv-pipeline')) { Invoke-Expression "$py -m venv .venv-pipeline" }
$runtime = VenvPy '.venv'; $offline = VenvPy '.venv-pipeline'
& $runtime -m pip install --upgrade pip -q
& $offline -m pip install --upgrade pip -q
& $runtime -m pip install -r requirements.txt -q
& $offline -m pip install -r requirements-precompute.txt -r requirements-dev.txt -q
if ($Gpu) {
  Write-Host '[setup] installing CUDA PyTorch from the official CUDA 12.6 index'
  & $offline -m pip install -r requirements-gpu.txt -q
}
else { & $offline -m pip install torch==2.14.0 deepwave==0.0.27 }
Write-Host '[setup] complete. Run .\scripts\rebuild-release.ps1 for the full candidate release, then validate before promotion.'
