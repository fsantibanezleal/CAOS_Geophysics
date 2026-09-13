$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path "frontend/package.json")) { throw "frontend/package.json is required" }
Set-Location frontend
if (-not (Test-Path node_modules)) { npm install }
node copy-data.mjs
npm run dev
