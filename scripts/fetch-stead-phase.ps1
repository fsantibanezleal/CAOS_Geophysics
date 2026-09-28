param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Destination
)

$ErrorActionPreference = 'Stop'
$sourceRoot = [System.IO.Path]::GetFullPath($Destination)
if (-not (Test-Path -LiteralPath $sourceRoot)) {
    New-Item -ItemType Directory -Path $sourceRoot | Out-Null
}
$sourceRoot = (Resolve-Path -LiteralPath $sourceRoot).Path
if ((Get-Item -LiteralPath $sourceRoot).LinkType) {
    throw 'STEAD destination cannot be a symbolic link.'
}

$sources = @(
    @{
        Name = 'metadata.csv'
        Url = 'https://seisbench.gfz-potsdam.de/mirror/datasets/stead/metadata.csv'
        Bytes = [long]402560190
        Sha256 = '9b9007406ebfef8c182060c8bb4266d29bbc433985f91f7e2dc476c8aca08efe'
    },
    @{
        Name = 'waveforms.hdf5'
        Url = 'https://seisbench.gfz-potsdam.de/mirror/datasets/stead/waveforms.hdf5'
        Bytes = [long]91127786704
        Sha256 = '4d73f567d9ea85fcdea5f2d8bf9cf47fd2e0c25b602793d41f56713efba62b1b'
    }
)

function Assert-SourceFile([string]$Path, [long]$ExpectedBytes, [string]$ExpectedSha256) {
    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.LinkType) { throw "Source cannot be a symbolic link: $Path" }
    if ($item.Length -ne $ExpectedBytes) {
        throw "Source byte count differs: $Path (got $($item.Length), expected $ExpectedBytes)"
    }
    $digest = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($digest -ne $ExpectedSha256) { throw "Source SHA-256 differs: $Path" }
}

Write-Host 'STEAD is CC BY 4.0; retain Mousavi et al. (2019), the source and license links, and modification notices in any derivative release.'
Write-Host 'These SHA-256 values pin our complete local mirror acquisition; the upstream mirror does not publish a matching checksum.'
foreach ($source in $sources) {
    $final = Join-Path $sourceRoot $source.Name
    $partial = "$final.partial"
    if (Test-Path -LiteralPath $final) {
        Assert-SourceFile $final $source.Bytes $source.Sha256
        Write-Host "Verified existing $($source.Name)"
        continue
    }
    if (Test-Path -LiteralPath $partial) {
        $staged = Get-Item -LiteralPath $partial
        if ($staged.LinkType -or $staged.Length -gt $source.Bytes) {
            throw "Partial source is a link or exceeds expected size: $partial"
        }
    }
    & curl.exe --location --fail --retry 5 --retry-delay 5 --continue-at - --output $partial $source.Url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed for $($source.Name); partial file remains for a later resume."
    }
    Assert-SourceFile $partial $source.Bytes $source.Sha256
    if (Test-Path -LiteralPath $final) {
        throw "A destination appeared during download; refusing to overwrite: $final"
    }
    Move-Item -LiteralPath $partial -Destination $final
    Write-Host "Verified and saved $($source.Name)"
}

Write-Host "STEAD source verified at $sourceRoot; raw data must remain outside public web assets."
