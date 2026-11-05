"""Fetch the two checksum-pinned USGS Long Valley gravity source files."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "downloads" / "long-valley"
ASSETS = (
    ("GravitySurveys.txt", "https://pubs.usgs.gov/dds/dds-81/MonitoringData/Gravity/SpreadsheetFormatData/GravitySurveys.txt", 5_029, "d7cca18741ef85fa7ea6fe448dabfee40900de6ed45ba5ea3d13b9e9f9ec1424"),
    ("gravitymetadata.htm", "https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/gravitymetadata.htm", 25_537, "6eeb2dccc73900d409f2126dcdf7a9a910ffebaabf7f22054528a8afd7ebebb7"),
)
MAX_BYTES = 1024 * 1024


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "CAOS-Geophysics-research-data-intake/1"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status} for pinned USGS source")
        body = response.read(MAX_BYTES + 1)
    if not body or len(body) > MAX_BYTES:
        raise RuntimeError("USGS response is empty or exceeds the 1 MiB safety limit")
    return body


def source_digest(name: str, body: bytes) -> str:
    if name == "gravitymetadata.htm":
        text = body.decode("iso-8859-1")
        text, scripts = re.subn(r'<script>\(function\(\)\{function c\(\).*?</script>', '<!-- volatile Cloudflare injection removed -->', text, count=1, flags=re.DOTALL)
        if scripts != 1:
            raise RuntimeError(f"expected one transient Cloudflare script in {name}; found {scripts}")
        canonical, count = re.subn(r'data-cfemail="[0-9a-fA-F]{2,}"', 'data-cfemail="[volatile-contact-token]"', text)
        if count < 1:
            raise RuntimeError(f"no expected rotating Cloudflare contact token found in {name}")
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return hashlib.sha256(body).hexdigest()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url, expected_bytes, expected_sha256 in ASSETS:
        body = fetch(url)
        actual = source_digest(name, body)
        if len(body) != expected_bytes or actual != expected_sha256:
            raise RuntimeError(f"pinned source identity mismatch for {name}: {len(body)} bytes, sha256={actual}")
        fd, temp_name = tempfile.mkstemp(prefix=f".{name}.", dir=DEST)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, DEST / name)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        print(f"verified {name}: bytes={expected_bytes} source_sha256={hashlib.sha256(body).hexdigest()} normalized_sha256={actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
