#!/usr/bin/env bash
# CI-friendly integration test runner for Sigil.
# Usage:
#   ./run_integration.sh              # run all integration tests (excluding real-world)
#   ./run_integration.sh --update     # update golden snapshot files
#   ./run_integration.sh -k "Demo"    # run only demo-app tests
#   ./run_integration.sh --quick      # skip slow tests (large graph)
#   ./run_integration.sh --realworld  # include real-world repo tests (clones from GitHub)
#   ./run_integration.sh --all        # run everything including real-world tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$SCRIPT_DIR"

PYTEST_ARGS=("-v" "--tb=short")
TEST_FILES=("test_integration.py")

# Parse arguments
UPDATE_GOLDEN=false
QUICK=false
REALWORLD=false
RUN_ALL=false
EXTRA_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --update)
            UPDATE_GOLDEN=true
            ;;
        --quick)
            QUICK=true
            ;;
        --realworld)
            REALWORLD=true
            ;;
        --all)
            RUN_ALL=true
            ;;
        *)
            EXTRA_ARGS+=("$arg")
            ;;
    esac
done

if $UPDATE_GOLDEN; then
    PYTEST_ARGS+=("--update-golden")
fi

if $QUICK; then
    PYTEST_ARGS+=("-k" "not LargeGraph")
fi

if $REALWORLD || $RUN_ALL; then
    TEST_FILES+=("test_realworld.py")
fi

echo "=== Sigil Integration Tests ==="
echo "Repo root: $REPO_ROOT"
echo "Demo app:  $REPO_ROOT/examples/demo-app/"
if $REALWORLD || $RUN_ALL; then
    echo "Mode:      including real-world repo tests"
fi
echo ""

# Run the integration tests
python3 -m pytest "${TEST_FILES[@]}" "${PYTEST_ARGS[@]}" "${EXTRA_ARGS[@]}"

EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo ""
    echo "=== All integration tests passed ==="
else
    echo ""
    echo "=== Integration tests FAILED (exit $EXIT) ==="
fi

exit $EXIT
