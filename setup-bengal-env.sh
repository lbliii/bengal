#!/bin/bash
# Activate Bengal environment with Python 3.14t
# Usage: source setup-bengal-env.sh

# Ensure we are in the project root
cd "$(dirname "${BASH_SOURCE[0]}")"

# If .venv doesn't exist, suggest running make setup
if [ ! -d ".venv" ]; then
    echo "Error: .venv not found. Run 'make setup' first."
    return 1
fi

source .venv/bin/activate

echo "✅ Bengal environment activated"
echo "Python: $(python --version)"
# echo "Bengal: $(bengal --version)" # commented out as bengal might not be in path if not installed yet
