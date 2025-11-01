# Bengal - Project Structure

## Repository Organization

```
bengal/                          # Main package directory
├── __init__.py                  # Package entry point, core exports
├── __main__.py                  # CLI entry point (python -m bengal)
├── analysis/                    # Graph analysis, PageRank, communities
├── assets/                      # Asset processing and optimization
├── autodoc/                     # AST-based documentation generation
├── cache/                       # Build cache and dependency tracking
├── cli/                         # Command-line interface modules
├── config/                      # Configuration loading and validation
├── content_types/               # Content strategies (blog, docs, portfolio)
├── core/                        # Core object model (Site, Page, Section, Asset)
├── discovery/                   # Content and asset discovery
├── fonts/                       # Google Fonts self-hosting system
├── health/                      # Build validation and health checks
├── orchestration/               # Build coordination and phase management
├── postprocess/                 # Sitemap, RSS, link validation
├── rendering/                   # Template engine, Markdown parsing
├── server/                      # Development server with live reload
├── services/                    # Service interfaces and implementations
├── themes/                      # Built-in themes and theme system
└── utils/                       # Shared utilities and helpers
```

## Core Module Responsibilities

### Core Object Model (`bengal/core/`)
- **site.py**: Site object, main orchestration entry point
- **page/**: Page objects with metadata, navigation, relationships
- **section.py**: Section hierarchy and organization
- **asset.py**: Asset processing and optimization
- **menu.py**: Navigation menu system

### Build Pipeline
- **discovery/**: Find and catalog content files and assets
- **orchestration/**: Coordinate build phases and dependency management
- **rendering/**: Process Markdown, apply templates, generate HTML
- **postprocess/**: Generate sitemaps, RSS feeds, validate links

### Supporting Systems
- **cache/**: Incremental build system with dependency tracking
- **config/**: Configuration loading with environment overrides
- **health/**: Validation system for build quality assurance
- **autodoc/**: AST-based Python and CLI documentation generation

## File Naming Conventions

### Python Modules
- **snake_case** for all Python files and directories
- **Descriptive names** that indicate purpose (e.g., `template_engine.py`, `link_validator.py`)
- **Avoid abbreviations** except for well-known terms (e.g., `cli`, `api`, `url`)

### Test Organization
```
tests/
├── unit/                        # Component isolation tests
│   ├── core/                   # Core object tests
│   ├── rendering/              # Template and parsing tests
│   ├── utils/                  # Utility function tests
│   └── ...
├── integration/                 # Multi-component workflow tests
├── performance/                 # Benchmark and performance tests
├── manual/                     # Manual testing scenarios
└── conftest.py                 # Shared fixtures and configuration
```

## Configuration Files

### Project Root
- **pyproject.toml**: Python project metadata, dependencies, tool config
- **pytest.ini**: Test runner configuration
- **.pre-commit-config.yaml**: Git hooks for code quality
- **requirements.lock**: Locked dependencies for reproducible builds

### User Projects (Generated)
- **bengal.toml** or **bengal.yaml**: Site configuration
- **content/**: Markdown content files
- **templates/**: Custom Jinja2 templates
- **assets/**: Static assets (CSS, JS, images)
- **public/**: Generated output directory

## Architecture Patterns

### Dependency Injection
- **BuildContext**: Lightweight container for build-time dependencies
- **Service interfaces**: Protocol-based services for testability
- **No global state**: All dependencies passed explicitly

### Modular Design
- **Single responsibility**: Each module has one clear purpose
- **Interface segregation**: Small, focused protocols
- **Dependency inversion**: Depend on abstractions, not concretions

### Error Handling
- **Structured exceptions**: Custom exception hierarchy
- **Error collection**: Collect multiple errors before failing
- **Graceful degradation**: Continue processing when possible

## Import Organization

### Import Order (enforced by ruff)
1. **Standard library imports**
2. **Third-party imports**
3. **Local application imports**

### Import Style
```python
# Standard library
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List

# Third-party
import click
from jinja2 import Environment

# Local
from bengal.core.site import Site
from bengal.utils.logger import get_logger
```

## Documentation Structure

### Architecture Documentation
```
architecture/
├── overview.md                  # High-level architecture overview
├── object-model.md             # Core objects and relationships
├── orchestration.md            # Build coordination
├── rendering.md                # Template and content processing
├── cache.md                    # Incremental build system
└── ...
```

### Development Documentation
- **README.md**: Project overview and quick start
- **CONTRIBUTING.md**: Development guidelines
- **TESTING_STRATEGY.md**: Testing approach and patterns
- **ARCHITECTURE.md**: Link to detailed architecture docs

## Package Data and Resources

### Included Resources
```python
# In pyproject.toml
[tool.setuptools.package-data]
bengal = [
    "themes/**/*",                    # Built-in themes
    "autodoc/templates/**/*.jinja2",  # Autodoc templates
    "cli/templates/**/*",             # CLI scaffolding templates
    "py.typed",                       # Type information marker
]
```

### Theme System
- **Built-in themes**: Included in package
- **Project themes**: In user's `themes/` directory
- **Installed themes**: Via pip/uv with `bengal-theme-` prefix

## Development Workflow

### Code Organization Principles
1. **Keep modules focused**: Single responsibility per file
2. **Minimize coupling**: Use dependency injection and protocols
3. **Test at the right level**: Unit tests for logic, integration for workflows
4. **Document interfaces**: Clear docstrings for public APIs
5. **Follow type hints**: Full type coverage for better IDE support

### Adding New Features
1. **Create module** in appropriate package directory
2. **Add tests** in corresponding `tests/unit/` or `tests/integration/`
3. **Update exports** in `__init__.py` if public API
4. **Document** in architecture docs if significant
5. **Add CLI commands** in `bengal/cli/` if user-facing
