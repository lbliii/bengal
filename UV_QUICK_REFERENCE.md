# UV Quick Reference for Bengal

Quick commands for working with Bengal using `uv`.

## Initial Setup

```bash
# One-time: Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install Bengal in development mode
uv pip install -e ".[dev]"
```

## Daily Development

```bash
# Install a new dependency
uv pip install package-name

# Install and add to pyproject.toml (manual edit still needed)
uv pip install package-name
# Then add to pyproject.toml dependencies

# Upgrade all dependencies
uv pip install -e ".[dev]" --upgrade

# Reinstall/sync current environment
uv pip install -e ".[dev]"
```

## Lock File Management

```bash
# Generate/update lock file after changing pyproject.toml
uv pip compile pyproject.toml -o requirements.lock --all-extras

# Install from lock file (exact versions)
uv pip sync requirements.lock
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
pytest

# Run tests with coverage
pytest --cov=bengal

# Format code
black bengal/

# Lint
ruff check bengal/

# Type check
mypy bengal/

# Build example site
cd examples/showcase
bengal build

# Start dev server
bengal serve
```

## Clean Start

```bash
# Remove virtual environment
rm -rf .venv

# Create fresh environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
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
uv venv --python 3.12

# Or use .python-version file (already set to 3.12)
```

### Dependency conflicts
```bash
# uv has better resolver, but if issues persist:
uv pip install -e ".[dev]" --resolution=highest
```


## More Info

- [uv Documentation](https://docs.astral.sh/uv/)
- [Bengal Contributing Guide](CONTRIBUTING.md)
- [Bengal Getting Started](GETTING_STARTED.md)
