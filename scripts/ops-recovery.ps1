$ErrorActionPreference = 'Stop'
& python (Join-Path $PSScriptRoot 'ops_recovery.py') @args
exit $LASTEXITCODE
