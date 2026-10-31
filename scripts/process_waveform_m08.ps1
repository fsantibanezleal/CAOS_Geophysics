param([string]$PythonPath)
$WaveformArguments = $args
$ErrorActionPreference = 'Stop'
if (-not $PythonPath -or -not [System.IO.Path]::IsPathFullyQualified($PythonPath)) {
    Write-Output '{"status":"rejected","reason":"path_contract"}'
    exit 3
}
try {
    & $PythonPath -B (Join-Path $PSScriptRoot 'process_waveform_m08.py') @WaveformArguments --python $PythonPath
} catch {
    Write-Output '{"status":"engine_unavailable","reason":"supervisor_unavailable"}'
    exit 4
}
exit $LASTEXITCODE
