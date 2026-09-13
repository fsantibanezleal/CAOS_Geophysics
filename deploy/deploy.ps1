param(
    [string]$Key = "D:\_Repos\_Web_Projects\_CAOS_MANAGE\credentials\general\ssh\hetzner_fasl_prod",
    [string]$HostName = "89.167.4.175",
    [string]$Domain = "geophysics.ml.fasl-work.com"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$dist = Join-Path $repo "frontend\dist"
if (-not (Test-Path (Join-Path $dist "index.html"))) { throw "Missing frontend/dist/index.html. Run the local build first." }
if (-not (Test-Path $Key)) { throw "Missing SSH key: $Key" }

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
$archive = Join-Path $env:TEMP "inverse-earth-$stamp.tar.gz"
$keyCopy = Join-Path $env:TEMP "inverse-earth-key-$stamp"
try {
    $keyText = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($Key)).Replace("`r", "")
    [IO.File]::WriteAllText($keyCopy, $keyText, [Text.UTF8Encoding]::new($false))
    tar --force-local -czf $archive -C $dist .
    scp -i $keyCopy -o StrictHostKeyChecking=accept-new $archive "root@$HostName`:/tmp/$stamp.tar.gz"
    scp -i $keyCopy -o StrictHostKeyChecking=accept-new (Join-Path $PSScriptRoot "$Domain.nginx") "root@$HostName`:/tmp/$Domain.nginx"
    $remote = "set -eu; root=/var/www/$Domain; release=`$root/releases/$stamp; mkdir -p `$release; tar -xzf /tmp/$stamp.tar.gz -C `$release; install -m 0644 /tmp/$Domain.nginx /etc/nginx/sites-available/$Domain; ln -sfn /etc/nginx/sites-available/$Domain /etc/nginx/sites-enabled/$Domain; ln -sfn `$release `$root/current; rm -f /tmp/$stamp.tar.gz /tmp/$Domain.nginx; nginx -t; systemctl reload nginx; printf 'release=%s\n' `$release"
    ssh -i $keyCopy -o StrictHostKeyChecking=accept-new "root@$HostName" $remote
} finally {
    Remove-Item -LiteralPath $archive, $keyCopy -Force -ErrorAction SilentlyContinue
}
