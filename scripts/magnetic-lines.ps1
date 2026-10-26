param(
    [Parameter(Mandatory=$true)][string]$Python,
    [ValidateSet('validate','run','replay')][string]$Mode = 'run',
    [string]$Csv, [string]$Metadata, [string]$Request,
    [string]$Bundle, [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw 'An existing pinned Python interpreter is required.' }
$entry = Join-Path $PSScriptRoot '../data-pipeline/magnetic_lines.py'
$parameters = @($entry, $Mode)
if ($Mode -eq 'replay') {
    $parameters += @('--bundle', $Bundle, '--output-directory', $OutputDirectory)
} else {
    $parameters += @('--csv', $Csv, '--metadata', $Metadata, '--request', $Request)
    if ($Mode -eq 'run') { $parameters += @('--output-directory', $OutputDirectory) }
}
& $Python @parameters
exit $LASTEXITCODE
