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

mkdir -p "$SCRIPT_DIR/lib/demo_index"
cp "$REPO_ROOT/examples/demo-app/.intent/index/"*.json "$SCRIPT_DIR/lib/demo_index/"
echo "Copied demo index to npm/lib/demo_index/"
