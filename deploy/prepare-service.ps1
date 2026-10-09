param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [Parameter(Mandatory = $true)][string]$Python,
    [string]$BuildDirectory
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not [IO.Path]::IsPathFullyQualified($OutputDirectory)) {
    throw 'OutputDirectory must be an explicit absolute new path.'
}
if (-not [IO.Path]::IsPathFullyQualified($Python) -or -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Supply the existing trusted local interpreter. No environment installation is performed.'
}
$prepareArguments = @('-B', (Join-Path $source 'scripts/prepare_service_release.py'), '--source', $source, '--output', $OutputDirectory)
if ($BuildDirectory) {
    if (-not [IO.Path]::IsPathFullyQualified($BuildDirectory)) { throw 'BuildDirectory must be explicit and absolute.' }
    $prepareArguments += @('--build', $BuildDirectory)
}
& $Python @prepareArguments
if ($LASTEXITCODE -ne 0) { throw 'Qualification preparation failed; retain the output for diagnosis.' }
Write-Output 'Prepared qualification bytes only. No upload, host change, activation or acceptance.'
