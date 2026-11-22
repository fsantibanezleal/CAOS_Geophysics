$ErrorActionPreference = 'Stop'
$paperRoot = $PSScriptRoot
Push-Location $paperRoot
try {
    latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) {
        throw "latexmk failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
