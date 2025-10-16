#!/bin/zsh
set -e  # Exit on error

# Activate the venv (use venv-3.14t if free-threaded)
VENV_PATH="venv-3.14"
if [ ! -d "$VENV_PATH" ]; then
  echo "Error: $VENV_PATH not found. Create it with: python3.14 -m venv $VENV_PATH"
  exit 1
fi

source "$VENV_PATH/bin/activate"
echo "Using Python: $(python --version) from $(which python)"

# Install/reinstall if needed (editable mode for dev)
pip install -e '.[dev]'

# Run pytest with your preferred flags (from pytest.ini: -n auto for parallel, etc.)
exec python -m pytest "$@"
