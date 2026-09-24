param([switch]$Gpu)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3.12' } else { 'python' }
function VenvPy($dir) { $p = Join-Path $dir 'Scripts/python.exe'; if (-not (Test-Path $p)) { $p = Join-Path $dir 'bin/python' }; return $p }
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
Write-Host '[setup] complete. Run .\scripts\precompute.ps1, then cd frontend; npm install; npm run build'
