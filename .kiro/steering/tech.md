# Bengal - Technology Stack

## Build System & Dependencies

- **Build system**: setuptools with pyproject.toml
- **Python version**: 3.14+ (required), 3.14t free-threaded recommended
- **Package manager**: uv (recommended) or pip
- **Dependency management**: pyproject.toml with optional dependencies

## Core Dependencies

- **CLI**: Click 8.1.7+ for command-line interface
- **Templating**: Jinja2 3.1.0+ for template rendering
- **Markdown**: Mistune 3.0.0+ (default parser, high performance)
- **Configuration**: PyYAML 6.0+ and toml 0.10.0+
- **Syntax highlighting**: Pygments 2.18.0+
- **Front matter**: python-frontmatter 1.0.0+
- **Asset optimization**: csscompressor 0.9.5+, jsmin 3.0.1+
- **Image processing**: Pillow 10.0.0+
- **Terminal UI**: Rich 13.7.0+, questionary 2.0.0+
- **File watching**: watchdog 3.0.0+ (dev server)
- **HTTP client**: httpx 0.27.0+ (link checking)

## Optional Dependencies

- **CSS optimization**: lightningcss 0.2.0+ (Rust-based, may not support all Python versions)
- **Alternative parser**: markdown 3.5.0+ (python-markdown, slower than mistune)

## Development Dependencies

- **Testing**: pytest 8.0.0+ with plugins (cov, mock, xdist, timeout, asyncio)
- **Property testing**: hypothesis 6.92.0+
- **Type checking**: mypy 1.11.0+
- **Linting/formatting**: ruff 0.14.0+ (Python 3.14 support required)
- **HTML validation**: beautifulsoup4 4.12.0+ (integration tests only)

## Common Commands

### Installation
```bash
# Using uv (recommended)
uv pip install -e .
uv pip install -e ".[server]"  # With dev server support

# Using pip
pip install -e .
```

### Development Setup
```bash
# Clone and setup
git clone https://github.com/lbliii/bengal.git
cd bengal

# Install with uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests (excludes performance/stateful)
pytest

# Run with coverage
pytest --cov=bengal --cov-report=html

# Run in parallel
pytest -n auto

# Run specific test types
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m hypothesis     # Property-based tests only
```

### Code Quality
```bash
# Lint and format
ruff check .
ruff format .

# Type checking
mypy bengal/

# Pre-commit hooks
pre-commit run --all-files
```

### Site Operations
```bash
# Create new site
bengal new site mysite

# Build site (maximum performance)
PYTHON_GIL=0 bengal site build --fast

# Development server
bengal site serve --port 5173

# Generate documentation
bengal utils autodoc --source mylib --output content/api
```

### Performance Testing
```bash
# Run benchmarks
pytest tests/performance/ -m performance

# Memory profiling
python -m memory_profiler benchmarks/memory_profiler.py
```

## Configuration Files

- **pyproject.toml**: Project metadata, dependencies, tool configuration
- **bengal.toml/bengal.yaml**: Site configuration (user projects)
- **pytest.ini**: Test configuration
- **.pre-commit-config.yaml**: Git hooks configuration
- **requirements.lock**: Locked dependencies for reproducible builds

## Performance Optimizations

- **Free-threading**: Use Python 3.14t with `PYTHON_GIL=0` for 1.8x speedup
- **Parallel builds**: ThreadPoolExecutor for concurrent processing
- **Incremental builds**: Dependency tracking for 18-42x faster rebuilds
- **Template caching**: Compiled template bytecode caching
- **Asset optimization**: Minification and fingerprinting
- **Fast mode**: `--fast` flag for maximum build speed
