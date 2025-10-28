# GitHub Copilot Instructions for Bengal

## Project Overview

Bengal is a high-performance static site generator (SSG) written in Python, designed with a modular architecture and built for Python 3.14+. It generates static websites from Markdown content with front matter, supporting features like incremental builds, parallel processing, taxonomy systems, and AST-based Python API documentation generation.

### Key Features
- **Performance**: 256 pages/sec on Python 3.14, with 2-4x speedup through parallel processing
- **Incremental Builds**: 15-50x faster rebuilds with intelligent caching and dependency tracking
- **AST-based Autodoc**: Generate Python API documentation without importing code
- **Rich Content Model**: Taxonomies (tags, categories), navigation, menus, and cascading metadata
- **Template Engine**: Jinja2-based with automatic navigation and breadcrumbs
- **Development Server**: File watching with auto-reload
- **Themes**: Support for project, installed, and bundled themes with swizzling

## Python Version and Modern Syntax

Bengal requires **Python 3.14+** and uses modern Python features:

### Type Hints (PEP 695)
- ✅ Use `X | Y` instead of `Union[X, Y]`
- ✅ Use `X | None` instead of `Optional[X]`
- ✅ Use `type` keyword for type aliases: `type PageID = str | int`
- ✅ Use PEP 695 generic syntax: `class Container[T]: ...`
- ✅ Use `isinstance(obj, Type1 | Type2)` instead of `isinstance(obj, (Type1, Type2))`
- ✅ Always include `from __future__ import annotations` at the top of files

### Code Style
- Line length: 100 characters (enforced by ruff)
- Use descriptive variable names
- Add Google-style docstrings to all public functions/classes
- Follow PEP 8 guidelines

## Architecture

### Core Components
- **Site**: Root object representing the entire website
- **Page**: Individual content pages parsed from Markdown
- **Section**: Collections of pages with shared metadata
- **Asset**: Static files (CSS, JS, images)
- **Menu**: Hierarchical navigation system

### Directory Structure
```
bengal/
├── bengal/              # Main package
│   ├── core/           # Core object model (Site, Page, Section)
│   ├── rendering/      # Rendering pipeline (Markdown, templates)
│   ├── discovery/      # Content and asset discovery
│   ├── config/         # Configuration system
│   ├── cache/          # Incremental build cache
│   ├── postprocess/    # Sitemap, RSS, link validation
│   ├── server/         # Dev server with file watching
│   ├── themes/         # Default bundled themes
│   ├── autodoc/        # AST-based documentation generation
│   └── cli/            # Command-line interface
├── tests/              # Test suite
│   ├── unit/          # Fast, isolated unit tests
│   ├── integration/   # Multi-component integration tests
│   ├── roots/         # Reusable test site templates
│   └── _testing/      # Test infrastructure helpers
├── examples/           # Example sites
└── architecture/       # Detailed architecture docs
```

### Key Architecture Principles
1. **Modular Design**: Clear separation of concerns, no "God objects"
2. **Delegation Pattern**: Site delegates to specialized orchestrators
3. **Dependency Injection**: BuildContext for clean service passing
4. **Parallel-Friendly**: Thread-safe operations for concurrent processing
5. **Extensible**: Plugin architecture for custom parsers and validators

See `architecture/` directory for detailed documentation on each subsystem.

## Development Workflow

### Setup
```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo-url>
cd bengal
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Common Commands

#### Testing
```bash
# Run all tests (fast)
pytest -n auto -m "not slow"

# Run all tests (full suite)
pytest -n auto

# Run specific test file
pytest tests/test_page.py

# Run with coverage
pytest --cov=bengal

# Run only slow tests
pytest -m slow

# Run only integration tests
pytest -m integration
```

#### Linting and Formatting
```bash
# Format code
ruff format bengal/

# Lint and auto-fix
ruff check --fix bengal/

# Type check
mypy bengal/
```

#### Building
```bash
# Create a test site
bengal new site mysite
cd mysite

# Build the site
bengal site build

# Fast mode (parallel, quiet output)
bengal site build --fast

# Development server
bengal site serve
```

### Pre-commit Hooks
The project uses pre-commit hooks. Configuration is in `.pre-commit-config.yaml`.

## Testing Guidelines

### Test Organization
- **Unit tests** (`tests/unit/`): Fast, isolated tests of individual functions/classes
- **Integration tests** (`tests/integration/`): Tests involving multiple components
- **Test roots** (`tests/roots/`): Minimal, reusable site templates

### Using Test Roots
Use the `@pytest.mark.bengal` marker for declarative site setup:

```python
@pytest.mark.bengal(testroot="test-basic")
def test_simple_build(site, build_site):
    """Test basic site building."""
    build_site()
    assert len(site.pages) == 1
    assert (site.output_dir / "index.html").exists()
```

### Available Test Roots
- `test-basic`: Minimal 1-page site
- `test-baseurl`: Tests baseurl handling
- `test-taxonomy`: 3 pages with tags
- `test-templates`: Template examples
- `test-assets`: Custom + theme assets
- `test-cascade`: Nested sections with cascade frontmatter

### Test Markers
- `@pytest.mark.slow`: Long-running tests (>5s)
- `@pytest.mark.hypothesis`: Property-based tests
- `@pytest.mark.serial`: Must run sequentially
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.performance`: Performance benchmarks
- `@pytest.mark.stateful`: Tests with stateful behavior

### CLI Testing
Use the `run_cli()` helper:

```python
from tests._testing.cli import run_cli

def test_version():
    result = run_cli(["--version"])
    result.assert_ok()
    assert "Bengal" in result.stdout
```

## Dependencies

### Core Dependencies
- **click**: CLI framework
- **jinja2**: Template engine
- **mistune**: Markdown parser
- **pyyaml**: YAML configuration
- **pygments**: Syntax highlighting
- **python-frontmatter**: Front matter parsing

### Optional Dependencies
- **server**: `watchdog` for file watching
- **css**: `lightningcss` for advanced CSS optimization
- **dev**: pytest, mypy, ruff, hypothesis (for development)

## Common Patterns

### Creating New Pages
Pages are created from Markdown files with front matter:

```markdown
---
title: Page Title
date: 2025-01-01
tags: [tag1, tag2]
---

Content here...
```

### Configuration
Configuration uses `bengal.toml` or `bengal.yaml`:

```toml
[site]
title = "My Site"
baseurl = "https://example.com"

[build]
output_dir = "public"
content_dir = "content"
fast_mode = true
```

### Error Handling
- Use specific exception types
- Provide helpful error messages with context
- Log warnings for recoverable errors
- Fail fast for critical errors

## Performance Considerations

- Use iterative approaches over deep recursion
- Support parallel processing where possible (use `ThreadPoolExecutor`)
- Cache expensive operations
- Profile before optimizing (use `--dev` flag for performance metrics)
- Incremental builds are the default (use cache system in `bengal/cache/`)

## Documentation

When making changes:
- Update relevant architecture docs in `architecture/`
- Add/update docstrings following Google style
- Update CHANGELOG.md for user-facing changes
- Update README.md if adding major features

## File Watching and Development Server

The dev server (`bengal site serve`) uses `watchdog` to watch for file changes and triggers rebuilds. Configuration in `bengal/server/`.

## Incremental Builds

The cache system (`bengal/cache/`) tracks dependencies using an inverted index pattern:
- Tracks file mtimes and content hashes
- Identifies changed files and their dependents
- Rebuilds only what's necessary (15-50x faster)

## When Working on Bengal

1. **Read the architecture docs**: Check `architecture/` for detailed component documentation
2. **Follow modern Python syntax**: Use PEP 695 type hints and Python 3.14+ features
3. **Write tests**: Add tests for new features, aim for >80% coverage
4. **Run tests frequently**: Use `pytest -n auto -m "not slow"` for fast feedback
5. **Format and lint**: Run `ruff format` and `ruff check --fix` before committing
6. **Type check**: Run `mypy` to ensure type correctness
7. **Keep changes focused**: Make surgical, minimal changes
8. **Update docs**: Keep architecture docs in sync with code changes

## Troubleshooting

### Common Issues
- **Import errors**: Ensure you installed with `pip install -e ".[dev]"`
- **Test failures**: Check if you're using Python 3.14+
- **Slow tests**: Use `-m "not slow"` to skip long-running tests during development
- **Type errors**: Ensure `from __future__ import annotations` is at the top of files

### CI/CD
The project uses GitHub Actions for testing (`.github/workflows/tests.yml`):
- **fast-check**: Quick signal (unit + most integration tests)
- **full-suite**: Coverage and baseurl portability tests
- **stateful**: Stateful workflow tests (nightly/manual)
- **performance**: Performance benchmarks (nightly/manual)

## Additional Resources

- **Architecture**: See `ARCHITECTURE.md` and `architecture/` directory
- **Contributing**: See `CONTRIBUTING.md` for detailed contribution guidelines
- **Getting Started**: See `GETTING_STARTED.md` for user-focused documentation
- **Test Coverage**: See `TEST_COVERAGE.md` for coverage goals and status
