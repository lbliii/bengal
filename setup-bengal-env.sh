#!/bin/bash
# Activate Bengal environment with Python 3.14
# Usage: source setup-bengal-env.sh

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

cd /Users/lb/Documents/bengal
source .venv/bin/activate

echo "✅ Bengal environment activated"
echo "Python: $(python --version)"
echo "Bengal: $(bengal --version)"
