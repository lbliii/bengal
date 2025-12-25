# RFC: Autodoc Extraction as Standalone Package

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0007 |
| **Title** | Extract Autodoc as Standalone OSS Package |
| **Status** | Draft |
| **Created** | 2025-12-25 |
| **Author** | Bengal Core Team |
| **Depends On** | None |
| **Supersedes** | None |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Extract Bengal's autodoc system into a standalone Python package |
| **Why** | Zero-import AST extraction is better than Sphinx autodoc; reusable by any SSG |
| **Effort** | ~6-8 hours for MVP, ~2 days for production-ready |
| **Risk** | Low — minimal coupling, clear extraction boundaries |
| **Constraints** | Must remain pure Python stdlib; must maintain Bengal compatibility |

**Key Insight**: Bengal's autodoc has three valuable components that don't exist elsewhere:
1. **Multi-style docstring parser** with auto-detection (Google/NumPy/Sphinx)
2. **Zero-import Python extractor** using pure AST (no crashes on missing deps)
3. **Unified DocElement model** that works across Python/CLI/OpenAPI

**Strategic Value**: Foundational primitive for the SSG ecosystem. Every documentation tool needs this.

---

## Motivation

### Current Landscape

| Tool | Approach | Problem |
|------|----------|---------|
| **sphinx.ext.autodoc** | Imports your code | Crashes on missing deps, slow, side effects |
| **pdoc** | Imports your code | Same problems as Sphinx |
| **mkdocstrings** | Imports your code | Same problems, plus complex setup |
| **pydoc** | Imports your code | Limited output, ancient API |
| **docstring-parser** | Parse only | No AST extraction, no type hints |

**Gap**: No production-quality tool does AST-based extraction with:
- Zero code import (safe, fast, no deps required)
- Multi-style docstring parsing
- Type hint extraction
- Parallel extraction (free-threading ready)

### What Bengal Has

```
bengal/autodoc/
├── docstring_parser.py    # 787 lines - PURE STDLIB
├── base.py                # 411 lines - 1 trivial import to remove
├── models/                # ~500 lines - PURE STDLIB (dataclasses)
│   ├── __init__.py
│   ├── common.py
│   ├── python.py
│   ├── cli.py
│   └── openapi.py
└── extractors/            # ~1500 lines - minimal coupling
    ├── __init__.py
    ├── python/            # 6 files, ~900 lines
    │   ├── __init__.py
    │   ├── extractor.py
    │   ├── signature.py
    │   ├── module_info.py
    │   ├── inheritance.py
    │   ├── skip_logic.py
    │   └── aliases.py
    ├── cli.py             # Click/Typer/argparse
    └── openapi.py         # OpenAPI 3.x specs
```

**Total extractable**: ~3,200 lines of high-quality, tested code.

---

## Design

### Package Architecture

**Option A: Monorepo with Multiple Packages** (Recommended)

```
astdoc/                          # Repository name
├── packages/
│   ├── pydocparse/              # Docstring parsing only
│   │   ├── pyproject.toml
│   │   └── src/pydocparse/
│   │       ├── __init__.py
│   │       ├── parser.py        # Main parse_docstring()
│   │       ├── google.py        # GoogleDocstringParser
│   │       ├── numpy.py         # NumpyDocstringParser
│   │       └── sphinx.py        # SphinxDocstringParser
│   │
│   ├── astdoc/                  # Full AST extraction
│   │   ├── pyproject.toml       # depends on pydocparse
│   │   └── src/astdoc/
│   │       ├── __init__.py
│   │       ├── base.py          # DocElement, Extractor ABC
│   │       ├── models/          # Typed metadata
│   │       └── extractors/
│   │           ├── python/
│   │           ├── cli.py
│   │           └── openapi.py
│   │
│   └── astdoc-cli/              # Optional CLI tool
│       ├── pyproject.toml
│       └── src/astdoc_cli/
│
├── tests/
├── docs/
└── README.md
```

**Why Monorepo**:
- `pydocparse` useful standalone (docstring parsing for linters, etc.)
- `astdoc` includes everything (most users want this)
- Clear dependency hierarchy
- Single CI/CD, single issue tracker

### Public API

#### pydocparse (Docstring Parsing)

```python
from pydocparse import parse_docstring, detect_style

# Auto-detect and parse
doc = parse_docstring('''
    Brief summary.

    Args:
        name: The name to use
        count: Number of iterations

    Returns:
        str: The result
''')

print(doc.summary)      # "Brief summary."
print(doc.args)         # {"name": "The name to use", "count": "Number of iterations"}
print(doc.returns)      # "str: The result"

# Explicit style
doc = parse_docstring(docstring, style="numpy")

# Style detection only
style = detect_style(docstring)  # "google", "numpy", "sphinx", or "plain"
```

#### astdoc (Full Extraction)

```python
from astdoc import PythonExtractor, DocElement
from pathlib import Path

# Extract entire package
extractor = PythonExtractor(
    exclude_patterns=["*/tests/*", "*/__pycache__/*"],
    include_private=False,
)
elements: list[DocElement] = extractor.extract(Path("src/mypackage"))

# Access structured data
for elem in elements:
    if elem.element_type == "module":
        print(f"Module: {elem.qualified_name}")
        for child in elem.children:
            if child.element_type == "class":
                print(f"  Class: {child.name}")
                meta = child.typed_metadata  # PythonClassMetadata
                print(f"    Bases: {meta.bases}")
                print(f"    Is dataclass: {meta.is_dataclass}")
            elif child.element_type == "function":
                meta = child.typed_metadata  # PythonFunctionMetadata
                print(f"  Function: {child.name}{meta.signature}")
                print(f"    Params: {meta.parameters}")
                print(f"    Returns: {meta.return_type}")
```

#### CLI Extraction

```python
from astdoc import CLIExtractor

# Extract Click/Typer app
extractor = CLIExtractor(framework="click")
elements = extractor.extract("mypackage.cli:main")

for elem in elements:
    meta = elem.typed_metadata  # CLICommandMetadata
    print(f"Command: {elem.name}")
    print(f"  Options: {meta.options}")
    print(f"  Arguments: {meta.arguments}")
```

#### OpenAPI Extraction

```python
from astdoc import OpenAPIExtractor
from pathlib import Path

# Extract from OpenAPI spec
extractor = OpenAPIExtractor()
elements = extractor.extract(Path("api/openapi.yaml"))

for elem in elements:
    if elem.element_type == "endpoint":
        meta = elem.typed_metadata  # OpenAPIEndpointMetadata
        print(f"{meta.method.upper()} {meta.path}")
        print(f"  Parameters: {meta.parameters}")
        print(f"  Request body: {meta.request_body}")
```

### DocElement Model

```python
@dataclass
class DocElement:
    """Universal representation of any documented element."""

    # Identity
    name: str                      # "build", "Site", "GET /users"
    qualified_name: str            # "bengal.core.site.Site.build"
    element_type: str              # "module", "class", "function", "endpoint", "command"

    # Documentation
    description: str               # Main description/docstring
    examples: list[str]            # Usage examples
    see_also: list[str]            # Cross-references
    deprecated: str | None         # Deprecation notice

    # Source location
    source_file: Path | None       # Source file path
    line_number: int | None        # Line number in source

    # Structured data
    metadata: dict[str, Any]       # Legacy dict-based metadata
    typed_metadata: DocMetadata    # Strongly-typed metadata (new)

    # Hierarchy
    children: list[DocElement]     # Nested elements (methods, subcommands)

    # Serialization
    def to_dict(self) -> dict      # For caching/JSON
    @classmethod
    def from_dict(cls, data)       # Deserialize
```

### Typed Metadata

```python
# Python-specific
@dataclass(frozen=True)
class PythonFunctionMetadata:
    signature: str                          # "(name: str, count: int = 0) -> str"
    parameters: tuple[ParameterInfo, ...]   # Structured params
    return_type: str | None                 # "str"
    is_async: bool
    is_classmethod: bool
    is_staticmethod: bool
    is_property: bool
    is_generator: bool
    decorators: tuple[str, ...]
    parsed_doc: ParsedDocstring | None

@dataclass(frozen=True)
class PythonClassMetadata:
    bases: tuple[str, ...]                  # ("BaseClass", "Mixin")
    decorators: tuple[str, ...]
    is_exception: bool
    is_dataclass: bool
    is_abstract: bool
    is_mixin: bool
    parsed_doc: ParsedDocstring | None

# CLI-specific
@dataclass(frozen=True)
class CLICommandMetadata:
    options: tuple[CLIOptionInfo, ...]
    arguments: tuple[CLIArgumentInfo, ...]
    is_group: bool
    parent_command: str | None

# OpenAPI-specific
@dataclass(frozen=True)
class OpenAPIEndpointMetadata:
    method: str                             # "get", "post", etc.
    path: str                               # "/users/{id}"
    parameters: tuple[OpenAPIParameterInfo, ...]
    request_body: OpenAPIRequestBody | None
    responses: tuple[OpenAPIResponse, ...]
    security: tuple[str, ...]
```

---

## Extraction Plan

### Phase 1: Docstring Parser (2 hours)

**Goal**: Extract `pydocparse` as completely standalone package.

**Files to extract**:
- `bengal/autodoc/docstring_parser.py` → `pydocparse/parser.py`

**Changes required**:
1. Split into separate files (google.py, numpy.py, sphinx.py)
2. Add `__init__.py` with public API
3. Create `pyproject.toml`
4. Add tests (port from Bengal)

**Validation**:
```bash
pip install -e packages/pydocparse
python -c "from pydocparse import parse_docstring; print(parse_docstring('Args:\n    x: test').args)"
```

### Phase 2: Core Models (1 hour)

**Goal**: Extract base classes and typed metadata.

**Files to extract**:
- `bengal/autodoc/base.py` → `astdoc/base.py`
- `bengal/autodoc/models/*.py` → `astdoc/models/`

**Changes required**:
1. Remove `TYPE_CHECKING` import of `DocMetadata` (make it a Protocol or Union)
2. Remove Bengal error imports (create `astdoc.errors`)
3. Add `pyproject.toml` with `pydocparse` dependency

**Validation**:
```bash
pip install -e packages/astdoc
python -c "from astdoc import DocElement; print(DocElement.__annotations__)"
```

### Phase 3: Python Extractor (2 hours)

**Goal**: Extract AST-based Python documentation extractor.

**Files to extract**:
- `bengal/autodoc/extractors/python/*.py` → `astdoc/extractors/python/`
- `bengal/autodoc/utils.py` → `astdoc/utils.py`

**Changes required**:
1. Replace `from bengal.errors import ...` with `from astdoc.errors import ...`
2. Replace `from bengal.config.defaults import get_max_workers` with inline logic
3. Replace `from bengal.utils.logger import get_logger` with stdlib logging
4. Update all internal imports

**Validation**:
```bash
pip install -e packages/astdoc
python -c "
from astdoc import PythonExtractor
from pathlib import Path
elements = PythonExtractor().extract(Path('packages/astdoc/src/astdoc'))
print(f'Extracted {len(elements)} modules')
"
```

### Phase 4: CLI Extractor (1 hour)

**Goal**: Extract Click/Typer/argparse documentation extractor.

**Files to extract**:
- `bengal/autodoc/extractors/cli.py` → `astdoc/extractors/cli.py`

**Changes required**:
1. Same import replacements as Phase 3
2. Ensure Click/Typer are optional dependencies

**Validation**:
```bash
pip install -e "packages/astdoc[cli]"
python -c "from astdoc import CLIExtractor; print(CLIExtractor)"
```

### Phase 5: OpenAPI Extractor (1 hour)

**Goal**: Extract OpenAPI specification parser.

**Files to extract**:
- `bengal/autodoc/extractors/openapi.py` → `astdoc/extractors/openapi.py`

**Changes required**:
1. Same import replacements
2. Ensure PyYAML is optional dependency

**Validation**:
```bash
pip install -e "packages/astdoc[openapi]"
python -c "from astdoc import OpenAPIExtractor; print(OpenAPIExtractor)"
```

### Phase 6: Bengal Integration (1 hour)

**Goal**: Make Bengal depend on extracted package.

**Changes**:
1. Add `astdoc` to Bengal's dependencies
2. Replace `bengal/autodoc/` with thin wrapper:

```python
# bengal/autodoc/__init__.py
"""
Autodoc - now powered by astdoc.

This module re-exports astdoc classes with Bengal-specific extensions
for virtual page generation.
"""
from astdoc import (
    DocElement,
    Extractor,
    PythonExtractor,
    CLIExtractor,
    OpenAPIExtractor,
    parse_docstring,
)
from astdoc.models import (
    PythonFunctionMetadata,
    PythonClassMetadata,
    # ... etc
)

# Bengal-specific orchestration stays here
from bengal.autodoc.orchestration import (
    VirtualAutodocOrchestrator,
    AutodocRunResult,
)
```

3. Update all Bengal imports to use new structure
4. Run full Bengal test suite

---

## File Mapping

| Bengal Path | Package | New Path |
|-------------|---------|----------|
| `autodoc/docstring_parser.py` | pydocparse | `parser.py` (split into 4 files) |
| `autodoc/base.py` | astdoc | `base.py` |
| `autodoc/models/__init__.py` | astdoc | `models/__init__.py` |
| `autodoc/models/common.py` | astdoc | `models/common.py` |
| `autodoc/models/python.py` | astdoc | `models/python.py` |
| `autodoc/models/cli.py` | astdoc | `models/cli.py` |
| `autodoc/models/openapi.py` | astdoc | `models/openapi.py` |
| `autodoc/extractors/__init__.py` | astdoc | `extractors/__init__.py` |
| `autodoc/extractors/python/*` | astdoc | `extractors/python/*` |
| `autodoc/extractors/cli.py` | astdoc | `extractors/cli.py` |
| `autodoc/extractors/openapi.py` | astdoc | `extractors/openapi.py` |
| `autodoc/utils.py` | astdoc | `utils.py` |
| `autodoc/config.py` | ❌ | Bengal-specific, stays |
| `autodoc/orchestration/*` | ❌ | Bengal-specific, stays |

---

## Dependency Changes

### pydocparse

```toml
[project]
name = "pydocparse"
version = "0.1.0"
description = "Multi-style Python docstring parser with auto-detection"
requires-python = ">=3.10"
dependencies = []  # Pure stdlib!

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "mypy", "ruff"]
```

### astdoc

```toml
[project]
name = "astdoc"
version = "0.1.0"
description = "AST-based Python API documentation extractor"
requires-python = ">=3.10"
dependencies = [
    "pydocparse>=0.1.0",
]

[project.optional-dependencies]
cli = ["click>=8.0"]          # For CLIExtractor
openapi = ["pyyaml>=6.0"]     # For OpenAPIExtractor
all = ["click>=8.0", "pyyaml>=6.0"]
dev = ["pytest", "pytest-cov", "mypy", "ruff"]
```

---

## Testing Strategy

### Unit Tests (Port from Bengal)

```
tests/
├── pydocparse/
│   ├── test_google.py       # Google-style parsing
│   ├── test_numpy.py        # NumPy-style parsing
│   ├── test_sphinx.py       # Sphinx-style parsing
│   └── test_detection.py    # Auto-detection
│
└── astdoc/
    ├── test_python_extractor.py
    ├── test_signature.py
    ├── test_inheritance.py
    ├── test_cli_extractor.py
    ├── test_openapi_extractor.py
    └── test_doc_element.py
```

### Integration Tests

```python
def test_extract_real_package():
    """Extract astdoc itself as integration test."""
    extractor = PythonExtractor()
    elements = extractor.extract(Path("src/astdoc"))

    assert len(elements) > 0

    # Find DocElement class
    doc_element = None
    for elem in elements:
        for child in elem.children:
            if child.name == "DocElement":
                doc_element = child
                break

    assert doc_element is not None
    assert doc_element.element_type == "class"
    assert "name" in [c.name for c in doc_element.children]
```

### Benchmark Tests

```python
def test_extraction_performance():
    """Ensure extraction is fast."""
    extractor = PythonExtractor()

    start = time.perf_counter()
    elements = extractor.extract(Path("src/astdoc"))
    elapsed = time.perf_counter() - start

    # Should extract in under 100ms
    assert elapsed < 0.1
```

---

## Documentation

### README.md

```markdown
# astdoc

**AST-based Python API documentation extractor.**

Unlike Sphinx autodoc, astdoc extracts documentation using pure AST parsing—no code imports, no dependency crashes, no side effects.

## Features

- 🚀 **Zero-import extraction** — Never crashes on missing dependencies
- 🔍 **Multi-style docstrings** — Auto-detects Google, NumPy, and Sphinx styles
- 📦 **Unified model** — Same `DocElement` for Python, CLI, and OpenAPI
- ⚡ **Parallel extraction** — Free-threading ready (Python 3.13t/3.14t)
- 🎯 **Type-safe** — Strongly-typed metadata with frozen dataclasses

## Installation

\`\`\`bash
pip install astdoc

# With CLI extraction (Click/Typer)
pip install astdoc[cli]

# With OpenAPI extraction
pip install astdoc[openapi]

# Everything
pip install astdoc[all]
\`\`\`

## Quick Start

\`\`\`python
from astdoc import PythonExtractor
from pathlib import Path

# Extract your package
extractor = PythonExtractor()
elements = extractor.extract(Path("src/mypackage"))

for elem in elements:
    print(f"{elem.element_type}: {elem.qualified_name}")
    print(f"  {elem.description[:50]}...")
\`\`\`

## Why Not Sphinx autodoc?

| Feature | Sphinx autodoc | astdoc |
|---------|---------------|--------|
| Imports your code | ✅ Yes | ❌ No |
| Crashes on missing deps | ✅ Yes | ❌ No |
| Executes module code | ✅ Yes | ❌ No |
| Pure static analysis | ❌ No | ✅ Yes |
| Type hint extraction | ⚠️ Limited | ✅ Full |
| Parallel extraction | ❌ No | ✅ Yes |
```

---

## Timeline

| Phase | Task | Effort | Blocker |
|-------|------|--------|---------|
| 1 | Extract pydocparse | 2 hr | None |
| 2 | Extract core models | 1 hr | Phase 1 |
| 3 | Extract Python extractor | 2 hr | Phase 2 |
| 4 | Extract CLI extractor | 1 hr | Phase 3 |
| 5 | Extract OpenAPI extractor | 1 hr | Phase 3 |
| 6 | Bengal integration | 1 hr | Phases 3-5 |
| 7 | Documentation | 2 hr | Phase 6 |
| 8 | CI/CD + PyPI | 1 hr | Phase 7 |

**Total: ~11 hours** (1.5 days)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hidden coupling | Low | Medium | Comprehensive grep for bengal imports |
| Test failures | Medium | Low | Port tests incrementally |
| API breakage | Low | High | Keep Bengal wrapper for backwards compat |
| Naming conflict | Low | Low | Check PyPI for existing "astdoc" |

---

## Success Criteria

1. **pydocparse** passes all docstring parsing tests
2. **astdoc** extracts Bengal's own codebase correctly
3. Bengal test suite passes with new dependency
4. Published to PyPI with documentation
5. Adoption by at least one external project (validation)

---

## Future Work

- [ ] Tree-sitter based extraction (for non-Python languages)
- [ ] TypeScript/JavaScript extractor
- [ ] Rust extractor
- [ ] Documentation drift detection (compare docs to code)
- [ ] Integration with popular SSGs (MkDocs, Sphinx, etc.)

---

## Appendix: Import Replacements

### Bengal → astdoc

```python
# Before (Bengal)
from bengal.errors import BengalDiscoveryError, ErrorCode
from bengal.config.defaults import get_max_workers
from bengal.utils.logger import get_logger

# After (astdoc)
from astdoc.errors import ExtractionError  # Simple exception
import os
max_workers = int(os.environ.get("ASTDOC_MAX_WORKERS", os.cpu_count() or 4))
import logging
logger = logging.getLogger(__name__)
```

### New Error Types

```python
# astdoc/errors.py
class AstdocError(Exception):
    """Base exception for astdoc."""
    pass

class ExtractionError(AstdocError):
    """Failed to extract documentation from source."""
    def __init__(self, message: str, source_file: Path | None = None):
        self.source_file = source_file
        super().__init__(message)

class ParseError(AstdocError):
    """Failed to parse source file."""
    pass
```
