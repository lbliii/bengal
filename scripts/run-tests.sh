#!/bin/zsh
set -e  # Exit on error

# Canonical: use the project .venv + uv dependency groups (see Makefile).
VENV_PATH=".venv"
if [ ! -d "$VENV_PATH" ]; then
  echo "Error: $VENV_PATH not found. Run: make setup"
  exit 1
fi

# Ensure dev dependencies are synced (frozen by default).
make install

echo "Using Python: $(uv run python --version) from $(uv run python -c 'import sys; print(sys.executable)')"

exec uv run pytest "$@"
