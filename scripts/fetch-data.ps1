$ErrorActionPreference = 'Stop'; Set-Location (Join-Path $PSScriptRoot '..')
$download = Join-Path (Get-Location) 'data/downloads'; New-Item -ItemType Directory -Force $download | Out-Null
$sources = @(
  @{ Name = 'simpeg-gravity.tar.gz'; Url = 'https://storage.googleapis.com/simpeg/doc-assets/gravity.tar.gz' },
  @{ Name = 'simpeg-magnetics.tar.gz'; Url = 'https://github.com/simpeg/user-tutorials/raw/main/assets/04-magnetics/inv_magnetics_induced_3d_files.tar.gz' }
)
foreach ($source in $sources) { $target = Join-Path $download $source.Name; if (-not (Test-Path $target)) { Invoke-WebRequest -Uri $source.Url -OutFile $target }; $hash = (Get-FileHash -Algorithm SHA256 $target).Hash.ToLowerInvariant(); Write-Host "$($source.Name) $hash" }
Write-Host '[fetch-data] raw downloads are ignored; original synthetic artifacts remain the public release inputs.'
