param([string]$Credentials, [switch]$RotatePassword)
$ErrorActionPreference = 'Stop'
$taskRepo = Split-Path $PSScriptRoot -Parent
$taskPython = Join-Path $taskRepo '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Create the pinned repository runtime .venv first.' }
$taskArguments = @((Join-Path $PSScriptRoot 'provision_account.py'))
if ($Credentials) { $taskArguments += @('--credentials', $Credentials) }
if ($RotatePassword) { $taskArguments += '--rotate-password' }
& $taskPython @taskArguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
