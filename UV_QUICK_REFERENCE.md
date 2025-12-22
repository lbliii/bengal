# UV Quick Reference for Bengal

Quick commands for working with Bengal using `uv` with Python 3.14t (free-threading).

## Initial Setup

```bash
# One-time: Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment and install dependencies
make setup    # Creates .venv with Python 3.14t
make install  # Installs dependencies (frozen)
```

## Daily Development

```bash
# Re-sync dev dependencies (uses frozen lockfile)
make install

# Activate environment with GIL disabled
make shell

# Or manually:
source .venv/bin/activate
export PYTHON_GIL=0
```

## Lock File Management

```bash
# Update lockfile after changing pyproject.toml
uv lock

# Sync dependencies (PEP 735 dependency groups)
uv sync --group dev

# Sync from frozen lockfile (no updates)
uv sync --group dev --frozen
```

## Why uv?

- 10-100x faster than pip
- Native lockfile support for reproducible builds
- PEP 735 dependency groups support
- Rust-based implementation
- Built-in Python version management

## Common Tasks

### Testing

```bash
make test                          # Run all tests
uv run pytest                      # Same as above
uv run pytest --cov=bengal         # With coverage
uv run pytest -x                   # Stop on first failure
uv run pytest tests/unit/          # Run specific directory
```

### Type Checking

```bash
make typecheck                     # Standard type check
make typecheck-strict              # Strict mode (for debugging)
```

### Linting & Formatting

```bash
uv run ruff format bengal/ tests/  # Format code
uv run ruff check bengal/ tests/   # Lint
uv run ruff check --fix            # Auto-fix issues
```

### Building & Serving

```bash
make build                         # Build the documentation site
make serve                         # Start dev server

# Or directly:
uv run bengal site build site
uv run bengal site serve site

# Run any bengal command:
make run ARGS="site build site"
```

## Clean Start

```bash
make clean     # Remove .venv, caches, build artifacts

# Then recreate:
make setup
make install
```

## CI/CD Integration

```yaml
# GitHub Actions
- name: Install uv
  uses: astral-sh/setup-uv@v4

- name: Set up Python 3.14t
  run: uv python install 3.14t

- name: Setup environment
  run: |
    uv venv --python 3.14t
    uv sync --group dev --frozen

- name: Run tests
  run: uv run pytest
  env:
    PYTHON_GIL: 0
```

## Troubleshooting

### uv not found

```bash
# Add to PATH (if not done automatically)
export PATH="$HOME/.cargo/bin:$PATH"

# Verify installation
uv --version
```

### Wrong Python version

```bash
# Bengal requires Python 3.14t (free-threading build)
uv python install 3.14t

# Specify when creating venv
uv venv --python 3.14t

# Check current version
python --version
```

### Dependency conflicts

```bash
# Re-lock dependencies
uv lock

# Force resolution to highest versions
uv lock --upgrade

# Then sync
uv sync --group dev
```

### Free-threading issues

```bash
# Ensure GIL is disabled
export PYTHON_GIL=0

# Verify (should show "0")
python -c "import sys; print(sys._is_gil_enabled())"

# Use make shell for automatic setup
make shell
```

## Environment Activation

```bash
# Option 1: make shell (recommended - sets PYTHON_GIL=0)
make shell

# Option 2: Source helper script
source setup-bengal-env.sh

# Option 3: Manual activation
source .venv/bin/activate
export PYTHON_GIL=0
```

## Key Differences from pip

| pip | uv |
|-----|-----|
| `pip install -e ".[dev]"` | `uv sync --group dev` |
| `pip freeze > requirements.txt` | `uv lock` (creates uv.lock) |
| `pip install -r requirements.txt` | `uv sync --frozen` |
| `python -m pytest` | `uv run pytest` |

## More Info

- [uv Documentation](https://docs.astral.sh/uv/)
- [PEP 735 - Dependency Groups](https://peps.python.org/pep-0735/)
- [Bengal Contributing Guide](CONTRIBUTING.md)
