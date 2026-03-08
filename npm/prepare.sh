#!/usr/bin/env bash
# Copy sigil.py into the npm package for distribution
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$SCRIPT_DIR/lib"
cp "$REPO_ROOT/tools/intent/sigil.py" "$SCRIPT_DIR/lib/sigil.py"
echo "Copied sigil.py to npm/lib/"

cp "$REPO_ROOT/tools/intent_viewer/index.html" "$SCRIPT_DIR/lib/sigil_viewer.html"
echo "Copied intent_viewer to npm/lib/sigil_viewer.html"
