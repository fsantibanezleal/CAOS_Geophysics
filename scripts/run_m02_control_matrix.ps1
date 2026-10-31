param(
  [string]$OutputRoot = 'E:\_Temp\CAOS_Geophysics\validation\m02-control-matrix-parallel'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $repo '.venv-pipeline\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw "Pinned pipeline interpreter not found: $python" }

$output = [System.IO.Path]::GetFullPath($OutputRoot)
if ($output.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw 'Matrix outputs must remain outside every repository checkout.'
}
New-Item -ItemType Directory -Path $output -Force | Out-Null

$jobs = foreach ($condition in 0..3) {
  foreach ($family in 0..5) {
    Start-Job -ArgumentList $repo, $python, $output, $family, $condition -ScriptBlock {
    param($RepoPath, $PythonPath, $EvidenceRoot, $FamilyIndex, $ConditionIndex)
    Set-Location -LiteralPath $RepoPath
    $env:OPENBLAS_NUM_THREADS = '1'
    $env:OMP_NUM_THREADS = '1'
    $env:MKL_NUM_THREADS = '1'
    $env:NUMEXPR_NUM_THREADS = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'

    $nodeId = "tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix[$ConditionIndex-$FamilyIndex]"
    $log = Join-Path $EvidenceRoot "condition-$ConditionIndex-family-$FamilyIndex.log"
    $junit = Join-Path $EvidenceRoot "condition-$ConditionIndex-family-$FamilyIndex.junit.xml"
    & $PythonPath -m pytest $nodeId -q -x --tb=short -o junit_family=xunit1 "--junitxml=$junit" 2>&1 |
      Tee-Object -FilePath $log
    $code = $LASTEXITCODE
    [pscustomobject]@{ family = $FamilyIndex; condition = $ConditionIndex; exit_code = $code; log = $log; junit = $junit }
    }
  }
}

$results = [System.Collections.Generic.List[object]]::new()
$active = [System.Collections.Generic.List[object]]::new()
foreach ($job in $jobs) { $active.Add($job) }
$failed = $false
while ($active.Count -gt 0) {
  $finished = Wait-Job -Job @($active) -Any -Timeout 5
  if ($null -eq $finished) { continue }
  $result = Receive-Job -Job $finished -ErrorAction Stop | Where-Object { $_ -is [pscustomobject] } | Select-Object -Last 1
  if ($null -eq $result) {
    $result = [pscustomobject]@{ family = 'unknown'; exit_code = 1; log = ''; junit = '' }
  }
  $results.Add($result)
  [void]$active.Remove($finished)
  if ($result.exit_code -ne 0) {
    $failed = $true
  }
}
Get-Job | Where-Object { $_.Id -in $jobs.Id } | Remove-Job -Force
$results | Sort-Object condition, family | Format-Table -AutoSize
Write-Host "Matrix evidence: $output"
if ($failed -or $results.Count -ne 24 -or @($results | Where-Object exit_code -ne 0).Count -gt 0) {
  exit 1
}
