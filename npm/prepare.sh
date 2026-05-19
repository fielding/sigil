#!/usr/bin/env bash
# Compatibility wrapper for humans who still run npm/prepare.sh directly.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec node "$SCRIPT_DIR/prepare.mjs"
