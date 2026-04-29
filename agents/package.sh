#!/usr/bin/env bash
# Package researchpipe-agent-ui as a downloadable .zip.
# Excludes node_modules / .next / .env.local — fresh-clone shape.
#
# Usage:
#   ./agents/package.sh [version]
#
# Output: backend/static/downloads/researchpipe-agent-ui-<version>.zip
set -euo pipefail

VERSION="${1:-0.1.0}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
SRC="$HERE/researchpipe-agent-ui"
OUT_DIR="$ROOT/backend/static/downloads"
OUT="$OUT_DIR/researchpipe-agent-ui-${VERSION}.zip"
LATEST="$OUT_DIR/researchpipe-agent-ui-latest.zip"

if [ ! -d "$SRC" ]; then
  echo "ERROR: source dir not found: $SRC" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -f "$OUT" "$LATEST"

echo "[package] zipping $SRC → $OUT"
cd "$HERE"
zip -rq "$OUT" "researchpipe-agent-ui" \
  -x "*/node_modules/*" \
  -x "*/.next/*" \
  -x "*/.env.local" \
  -x "*/.git/*" \
  -x "*.DS_Store"

# Symlink "latest" for stable download URL
ln -sf "researchpipe-agent-ui-${VERSION}.zip" "$LATEST"

SIZE=$(du -h "$OUT" | cut -f1)
echo "[package] OK: $OUT ($SIZE)"
echo "[package]     latest → $LATEST"
