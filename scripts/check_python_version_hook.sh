#!/usr/bin/env bash
set -euo pipefail

# Resolve repository root relative to this script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Ensure common install locations are in PATH for pre-commit environments
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$ROOT_DIR/.venv/bin:$PATH"

find_uv() {
    # Check PATH first
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi

    # Explicit fallback paths (pre-commit may have restricted PATH)
    local paths=(
        "$HOME/.local/bin/uv"
        "$HOME/.cargo/bin/uv"
        "$ROOT_DIR/.venv/bin/uv"
        "/usr/local/bin/uv"
    )

    for p in "${paths[@]}"; do
        if [ -x "$p" ]; then
            echo "$p"
            return 0
        fi
    done

    return 1
}

if ! UV_BIN="$(find_uv)"; then
    echo "Executable \`uv\` not found" >&2
    echo "Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

exec "$UV_BIN" run python "$ROOT_DIR/scripts/check_python_version.py"
