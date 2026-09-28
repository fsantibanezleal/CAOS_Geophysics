$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
foreach ($SourceId in @('simpeg-gravity', 'simpeg-magnetics')) {
    & python (Join-Path $RepoRoot 'data-pipeline/acquire.py') --source-id $SourceId
    if ($LASTEXITCODE -ne 0) { throw "Acquisition failed for $SourceId (exit $LASTEXITCODE)" }
}
Write-Host '[fetch-data] Both reviewed assets are hash-verified under ignored data/downloads/.'
