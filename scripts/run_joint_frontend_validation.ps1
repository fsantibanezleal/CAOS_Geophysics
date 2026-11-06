param(
  [string]$DataRoot = 'E:\_Datos\CAOS_Geophysics'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$validationRoot = Join-Path ([System.IO.Path]::GetFullPath($DataRoot)) 'validation'

$fixtures = [ordered]@{
  GEOPHYSICS_JOINT_MATRIX_FIXTURE = Join-Path $validationRoot 'combined-joint-input-matrix-20261031'
  GEOPHYSICS_JOINT_OUTPUT_FIXTURE = Join-Path $validationRoot 'combined-joint-output-matrix-20261031\joint-control-00\output'
  GEOPHYSICS_JOINT_OUTPUT_MATRIX_FIXTURE = Join-Path $validationRoot 'combined-joint-output-matrix-20261031'
  GEOPHYSICS_JOINT_MAX_OUTPUT_FIXTURE = Join-Path $validationRoot 'combined-joint-maximum-resource-20261031\output'
  GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE = Join-Path $validationRoot 'joint-instrument-replay-20261031\current-instrument-case00'
  GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT = Join-Path $validationRoot 'combined-api-custody-20261031'
}

$requiredFiles = @(
  (Join-Path $fixtures.GEOPHYSICS_JOINT_MATRIX_FIXTURE 'joint-control-00\development\request.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_MATRIX_FIXTURE 'joint-control-00\sealed\sealed.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_OUTPUT_FIXTURE 'workflow.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_OUTPUT_MATRIX_FIXTURE 'matrix.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_MAX_OUTPUT_FIXTURE 'workflow.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE 'workflow.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT 'actual-history.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT 'actual-index.json')
  (Join-Path $fixtures.GEOPHYSICS_JOINT_CUSTODY_API_RECEIPT 'actual-export.zip')
)
foreach ($path in $requiredFiles) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Required retained joint-survey fixture is missing: $path"
  }
}
foreach ($name in $fixtures.Keys) {
  Set-Item -Path "Env:$name" -Value ([System.IO.Path]::GetFullPath($fixtures[$name]))
}

# Do not accidentally turn missing real failure/evaluation artifacts into evidence
# by inheriting unrelated process-level fixture paths.
foreach ($name in @(
  'GEOPHYSICS_JOINT_EVALUATION_FIXTURE'
  'GEOPHYSICS_JOINT_ABORT_FIXTURE'
  'GEOPHYSICS_JOINT_DURABLE_ABORT_FIXTURE'
)) {
  Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
}

$testFiles = @(
  'src/test/joint-input.test.ts'
  'src/test/joint-result.test.ts'
  'src/test/joint-result-component.test.ts'
  'src/test/joint-read-queue.test.ts'
  'src/test/joint-runtime-profile.test.ts'
  'src/test/joint-custody.test.ts'
  'src/test/joint-hash-admission.test.ts'
)
Push-Location (Join-Path $repoRoot 'frontend')
try {
  & npm test -- --reporter=dot @testFiles
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}
exit $exitCode
