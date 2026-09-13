#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f frontend/package.json ] || { echo "frontend/package.json is required" >&2; exit 1; }
cd frontend
[ -d node_modules ] || npm install
node copy-data.mjs
npm run dev
