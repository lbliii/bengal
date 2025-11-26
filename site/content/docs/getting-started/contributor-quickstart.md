---
title: Contribute to Bengal
description: Set up your dev environment and make your first contribution
weight: 60
type: doc
draft: false
lang: en
tags: [onboarding, contribution, development]
keywords: [contributing, development, pull requests, git]
category: onboarding
---

# Contributor Quickstart

Get set up to contribute to Bengal's core development. This guide is for developers who want to fix bugs, add features, or improve Bengal itself.

## Prerequisites

- [Python 3.14+](/docs/getting-started/installation/) (preferably 3.14t free-threaded)
- Git
- Familiarity with Python development
- Basic knowledge of static site generators (helpful but not required)

## 1. Fork and Clone

Fork the repository on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/bengal.git
cd bengal
```

Add the upstream remote:

```bash
git remote add upstream https://github.com/lbliii/bengal.git
```

## 2. Set Up Development Environment

### Using uv (Recommended)

```bash
# Install uv if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with Python 3.14
uv venv --python 3.14

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Bengal in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Using pip

```bash
# Create virtual environment
python3.14 -m venv venv-3.14
source venv-3.14/bin/activate  # On Windows: venv-3.14\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### For Free-Threaded Python (1.8x faster)

```bash
# Install Python 3.14t (free-threaded build)
# See INSTALL_FREE_THREADED.md for full instructions

python3.14t -m venv venv-3.14t
source venv-3.14t/bin/activate
uv pip install -e ".[dev]"
```

## 3. Verify Installation

```bash
# Check version
bengal --version

# Should output: Bengal SSG, version X.X.X
```

## 4. Run Tests

Bengal uses pytest for testing. **Always run tests via the helper script:**

```bash
./scripts/run-tests.sh
```

This ensures the correct venv is activated and all tests pass.

### Run Specific Tests

```bash
# Run unit tests only
./scripts/run-tests.sh tests/unit/

# Run specific test file
./scripts/run-tests.sh tests/unit/test_site.py

# Run with verbose output
./scripts/run-tests.sh -v

# Run with coverage
./scripts/run-tests.sh --cov=bengal --cov-report=html
```

:::{warning}
**Never run `pytest` directly** from your system Python or conda. Always use `./scripts/run-tests.sh` to avoid version mismatches.
:::

## 5. Understand the Architecture

Bengal is organized into subsystems:

```
bengal/
├── core/               # Core data models (Site, Page, Section, Asset)
├── orchestration/      # Build coordination (render/build orchestrators)
├── rendering/          # Template engine, markdown, filters, shortcodes
├── cache/              # Build cache, indexes, dependency tracking
├── assets/             # Asset pipeline (CSS/JS/images)
├── discovery/          # Content discovery
├── health/             # Validators and health checks
├── cli/                # CLI commands
├── config/             # Configuration system
├── content_types/      # Content type system
└── utils/              # Shared utilities
```

### Key Files to Know

- `bengal/core/site.py` - Central orchestrator
- `bengal/core/page/__init__.py` - Page model
- `bengal/orchestration/render_orchestrator.py` - Main render loop
- `bengal/rendering/jinja_env.py` - Template engine setup
- `bengal/cache/build_cache.py` - Build cache system

### Read the Docs

- **[Architecture Overview](/docs/reference/architecture/)** - System design
- **[Design Principles](/docs/reference/architecture/core/design-principles/)** - Development philosophy
- **[Testing Strategy](../../../TESTING_STRATEGY.md)** - Testing approach

## 6. Build the Example Site

Test your setup by building the example site:

```bash
cd site
bengal site build

# Start dev server
bengal site serve
```

Visit **http://localhost:5173/** to see it running.

## 7. Make Your First Change

### Find an Issue

Browse [open issues](https://github.com/lbliii/bengal/issues) and look for:
- `good first issue` label
- `help wanted` label
- `bug` label (for bug fixes)

### Create a Branch

```bash
git checkout -b fix-issue-123
```

### Make Changes

Example: Fix a typo in documentation:

```bash
# Edit the file
vim README.md

# Test your changes
./scripts/run-tests.sh
```

### Follow Code Style

Bengal uses:
- **Black** for code formatting
- **isort** for import sorting
- **Type hints** for all functions
- **Docstrings** for all public APIs

Run formatters:

```bash
black bengal tests
isort bengal tests
```

### Write Tests

For bug fixes:
```python
# tests/unit/test_your_fix.py
def test_issue_123_is_fixed():
    """Test that issue #123 is resolved."""
    # Arrange
    site = Site.from_config(Path("."))

    # Act
    result = site.some_method()

    # Assert
    assert result == expected_value
```

For new features:
```python
# tests/unit/test_new_feature.py
def test_new_feature_works():
    """Test that new feature behaves correctly."""
    # Test the happy path
    assert new_feature() == expected

def test_new_feature_handles_errors():
    """Test that new feature handles edge cases."""
    with pytest.raises(ValueError):
        new_feature(invalid_input)
```

### Run Tests Again

```bash
./scripts/run-tests.sh
```

Make sure all tests pass!

## 8. Commit Your Changes

Bengal uses atomic commits with descriptive messages:

```bash
git add -A
git commit -m "core: fix cache invalidation when section slug changes (#123)"
```

### Commit Message Format

```
<subsystem>: <description> (#issue-number)

Examples:
- "core: decouple theme resolution from TemplateEngine"
- "cache: add dependency tracking for taxonomies"
- "cli: improve error messages in serve command"
- "docs: update installation guide for Python 3.14t"
- "tests: add coverage for incremental builds"
```

Subsystems: `core`, `orchestration`, `rendering`, `cache`, `assets`, `cli`, `config`, `health`, `docs`, `tests`

## 9. Push and Create PR

```bash
# Push to your fork
git push origin fix-issue-123
```

Go to GitHub and create a Pull Request:

1. Click "Compare & pull request"
2. Write a clear title: `Fix cache invalidation when section slug changes (#123)`
3. Describe your changes:

```markdown
## Changes
- Fixed issue where cache wasn't invalidated on section slug changes
- Added test coverage for this scenario

## Testing
- Added unit test in `tests/unit/test_cache.py`
- Verified all existing tests pass
- Tested manually with example site

Fixes #123
```

## 10. Respond to Review

Maintainers will review your PR and may request changes:

```bash
# Make requested changes
vim bengal/core/site.py

# Run tests
./scripts/run-tests.sh

# Commit and push
git add -A
git commit -m "address review feedback: add edge case handling"
git push origin fix-issue-123
```

## Development Workflow

### Typical Day-to-Day

```bash
# Pull latest changes
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature-my-feature

# Make changes, run tests frequently
vim bengal/core/site.py
./scripts/run-tests.sh

# Commit atomically
git add -A
git commit -m "core: add incremental asset tracking"

# Push and create PR
git push origin feature-my-feature
```

### Using Bengal's Development Tools

```bash
# Build with performance profiling
bengal site build --dev

# Run with memory profiling
bengal site build --dev --profile-memory

# Enable theme developer mode (extra validation)
bengal site build --theme-dev

# Fast mode (minimal output)
PYTHON_GIL=0 bengal site build --fast
```

## Debugging Tips

### Enable Debug Output

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Use pdb for Debugging

```python
import pdb; pdb.set_trace()
```

### Profile Performance

```bash
# Time a specific operation
python -m cProfile -s cumulative -m bengal.cli site build
```

### Check Cache State

```bash
# Inspect build cache
python -c "from bengal.cache.build_cache import BuildCache; cache = BuildCache('.'); print(cache.get_all_entries())"
```

## Testing Guidelines

### Test Organization

- `tests/unit/` - Unit tests for individual modules
- `tests/integration/` - Integration tests for full workflows
- `tests/performance/` - Performance benchmarks
- `tests/_testing/` - Testing utilities and fixtures

### Writing Good Tests

```python
import pytest
from pathlib import Path
from bengal.core.site import Site

def test_site_builds_successfully(tmp_path):
    """Test that a minimal site builds without errors."""
    # Arrange
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "index.md").write_text("# Home\n\nWelcome!")

    # Act
    site = Site.from_config(tmp_path)
    site.build()

    # Assert
    output_file = tmp_path / "public" / "index.html"
    assert output_file.exists()
    assert "Welcome!" in output_file.read_text()
```

### Run Benchmarks

```bash
cd benchmarks
pytest test_build.py --benchmark-only
```

## Code Review Checklist

Before submitting your PR, verify:

- [ ] All tests pass (`./scripts/run-tests.sh`)
- [ ] Code is formatted (`black`, `isort`)
- [ ] Type hints added for new functions
- [ ] Docstrings added for public APIs
- [ ] Tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] Atomic commits with descriptive messages
- [ ] No merge conflicts with main

## Troubleshooting

### Common Development Issues

**Tests failing:**
- Ensure you're using the correct Python version (3.14+)
- Activate your virtual environment: `source .venv/bin/activate`
- Run tests via helper script: `./scripts/run-tests.sh`
- Check for import errors or missing dependencies

**Import errors:**
- Verify editable install: `pip install -e ".[dev]"`
- Check Python path: `python -c "import bengal; print(bengal.__file__)"`
- Ensure you're in the project root directory

**Build issues:**
- Clear cache: `rm -rf .bengal-cache/`
- Clean output: `bengal site clean`
- Check config: `bengal config show`

**Git issues:**
- Verify upstream remote: `git remote -v`
- Sync with upstream: `git fetch upstream && git merge upstream/main`
- Check branch status: `git status`

## Next Steps

**Learn More:**
- **[CONTRIBUTING.md](../../../CONTRIBUTING.md)** - Full contribution guidelines
- **[Architecture Overview](/docs/reference/architecture/)** - Deep dive into Bengal's design
- **[Testing Strategy](../../../TESTING_STRATEGY.md)** - Testing philosophy

**Get Involved:**
- Join discussions on [GitHub](https://github.com/lbliii/bengal)
- Review other PRs
- Help triage issues
- Improve documentation

**Advanced Topics:**
- Implement new features
- Optimize performance
- Add new subsystems
- Create tools and utilities

Thank you for contributing to Bengal! 🙏
