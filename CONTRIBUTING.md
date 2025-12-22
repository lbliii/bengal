# Contributing to Bengal

Bengal uses **uv** with **PEP 735 dependency groups** for development. Python 3.14+ is required, with 3.14t (free-threading) recommended for best performance.

## Quick Start

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/bengal.git
cd bengal

# Create virtual environment (Python 3.14t)
make setup

# Install dependencies
make install

# Verify
uv run bengal --version
```

## Development Commands

| Command | Description |
|---------|-------------|
| `make setup` | Create virtual environment with Python 3.14t |
| `make install` | Install dependencies (dev group included) |
| `make test` | Run test suite (excludes slow/performance tests) |
| `make typecheck` | Run mypy type checking |
| `make build` | Build the documentation site |
| `make serve` | Start development server |
| `make clean` | Remove build artifacts and caches |

## Code Quality

Before committing, run:

```bash
# Format code
uv run ruff format bengal/ tests/

# Lint (with auto-fix)
uv run ruff check bengal/ tests/ --fix

# Type check
make typecheck
```

All code must pass linting and type checking. Type hints are required for all functions.

## Running Tests

```bash
# Default: fast tests only (excludes performance/stateful)
make test

# Run specific test file
uv run pytest tests/unit/test_page.py

# Run with coverage
uv run pytest --cov=bengal

# Include slow tests
uv run pytest -m "not performance"

# Run all tests (including performance)
uv run pytest -m ""
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `unit` | Fast, isolated unit tests |
| `integration` | Multi-component tests |
| `slow` | Long-running tests (>10s) |
| `performance` | Benchmark tests (excluded by default) |
| `stateful` | State-machine tests (excluded by default) |
| `cli` | CLI command tests |

## Commit Messages

Use descriptive atomic commits that read like a changelog:

```bash
git add -A && git commit -m "<scope>: <description>"
```

### Format

- **scope**: Primary area (`core`, `orchestration`, `rendering`, `cache`, `cli`, `tests`, `docs`)
- **description**: Clear verb-first description of what changed

### Examples

```bash
# Good
git commit -m "core: add incremental build support for assets"
git commit -m "rendering: fix template inheritance for nested sections"
git commit -m "tests: add integration tests for taxonomy discovery"

# Bad
git commit -m "fix bug"        # Too vague
git commit -m "updates"        # No information
```

For multi-area changes, separate with semicolons:

```bash
git commit -m "core: extract theme resolution; utils: add ThemeResolver helper"
```

## Project Structure

```text
bengal/
├── bengal/
│   ├── core/           # Passive data models (no I/O, no logging)
│   ├── orchestration/  # Build coordination and operations
│   ├── rendering/      # Template and content rendering
│   ├── discovery/      # Content/asset discovery
│   ├── cache/          # Caching infrastructure
│   ├── health/         # Validation and checks
│   └── cli/            # Command-line interface
├── tests/
│   ├── unit/           # Fast, isolated tests
│   ├── integration/    # Multi-component tests
│   └── roots/          # Reusable test fixtures
└── site/               # Documentation site source
```

## Key Principles

- **Core is passive**: No I/O, no logging in `bengal/core/`
- **Orchestration coordinates**: Build logic lives in `bengal/orchestration/`
- **Tests required**: All changes need tests
- **Type hints required**: Use Python type hints everywhere
- **Coverage target**: 85% minimum

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes following existing patterns
3. Add tests for new functionality
4. Run linters and type checking
5. Commit with descriptive messages
6. Push and create a PR

## Resources

- **[UV Quick Reference](UV_QUICK_REFERENCE.md)** — uv commands and troubleshooting
- **[Type Checking Guide](TYPE_CHECKING_GUIDE.md)** — mypy patterns for Bengal
- **[Contributor Quickstart](site/content/docs/get-started/quickstart-contributor.md)** — Detailed setup guide
