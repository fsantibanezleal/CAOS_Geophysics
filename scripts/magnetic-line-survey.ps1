[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$SurveyArguments
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw 'Provide the existing Python executable explicitly.'
}
if (-not $env:GEOPHYSICS_EXISTING_PACKAGE_ROOT) {
    throw 'GEOPHYSICS_EXISTING_PACKAGE_ROOT must identify the reviewed installed environment.'
}
$surveyCli = Join-Path $PSScriptRoot '../data-pipeline/magnetic_line_survey_cli.py'
& $PythonExe -B -S $surveyCli @SurveyArguments
exit $LASTEXITCODE
