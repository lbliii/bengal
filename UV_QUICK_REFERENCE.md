# UV Quick Reference for Bengal

Quick commands for working with Bengal using `uv`.

## Initial Setup

```bash
# One-time: Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Recommended (uses Python 3.14t if available)
make setup
make install
```

## Daily Development

```bash
# Re-sync dev dependencies (frozen by default in Makefile)
make install
```

## Lock File Management

```bash
# Update the uv lockfile after changing pyproject.toml
uv lock

# Sync dependencies (includes dev group when requested)
uv sync --group dev
```

## Why uv?

- Faster than pip
- Better dependency resolution
- Lock file support for reproducible builds
- Modern Rust-based implementation
- Compatible with existing pip/pyproject.toml setup

## Common Tasks

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=bengal

# Format code
uv run ruff format bengal/ tests/

# Lint
uv run ruff check bengal/ tests/

# Type check
uv run mypy bengal/

# Build example site
cd examples/showcase
bengal site build

# Start dev server
bengal site serve
```

## Clean Start

```bash
# Remove virtual environment
rm -rf .venv

# Create fresh environment
make setup
make install
```

## CI/CD Integration (Future)

```yaml
# GitHub Actions
- name: Install uv
  run: pip install uv

- name: Setup environment
  run: |
    uv venv
    source .venv/bin/activate
    uv pip install -e ".[dev]"

- name: Run tests
  run: pytest
```

## Troubleshooting

### Can't find uv
```bash
# Add to PATH (if not done automatically)
export PATH="$HOME/.cargo/bin:$PATH"

# Verify installation
uv --version
```

### Wrong Python version
```bash
# Specify Python version
uv venv --python 3.14

# Or use .python-version file (already set to 3.14)
```

### Dependency conflicts
```bash
# uv has better resolver, but if issues persist:
uv pip install -e ".[dev]" --resolution=highest
```


## More Info

- [uv Documentation](https://docs.astral.sh/uv/)
- [Bengal Contributing Guide](CONTRIBUTING.md)
