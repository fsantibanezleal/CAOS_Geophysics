#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"; mkdir -p data/downloads
curl -L --fail --retry 3 -o data/downloads/simpeg-gravity.tar.gz https://storage.googleapis.com/simpeg/doc-assets/gravity.tar.gz
curl -L --fail --retry 3 -o data/downloads/simpeg-magnetics.tar.gz https://github.com/simpeg/user-tutorials/raw/main/assets/04-magnetics/inv_magnetics_induced_3d_files.tar.gz
sha256sum data/downloads/*.tar.gz
