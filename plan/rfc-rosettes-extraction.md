# RFC: Rosettes Extraction to Standalone Package

**Status**: Draft  
**Created**: 2026-01-02  
**Author**: Bengal Contributors

---

## Executive Summary

Extract Rosettes, Bengal's syntax highlighting library, into a standalone Python package at `github.com/lbliii/rosettes`. This enables broader adoption while Bengal becomes a consumer of the external package.

**Key Metrics:**
- **55 language lexers** (hand-written state machines)
- **73 source files** to extract
- **27 test files** + fixtures
- **3 Bengal-specific imports** to remove (error handling)

---

## Background

Rosettes is a pure-Python syntax highlighter designed for free-threaded Python 3.14t. Key features:

- **O(n) guaranteed performance** — no regex backtracking
- **Zero ReDoS vulnerability** — hand-written state machine lexers
- **Thread-safe by design** — immutable state, no global mutable data
- **Pygments compatibility** — drop-in CSS class compatibility
- **Parallel processing** — `highlight_many()` for multi-core systems

Currently embedded at `bengal/rendering/rosettes/`, making it unavailable to the broader Python ecosystem.

---

## Goals

1. **Standalone package**: `pip install rosettes` works independently
2. **Zero external dependencies**: Pure Python, no runtime deps
3. **Backward compatibility**: Bengal continues working via external import
4. **Clean separation**: No Bengal-specific code in rosettes

### Non-Goals

- Changing rosettes API
- Adding new features during extraction
- Supporting Python < 3.14

---

## Current State Analysis

### Source Files

```
bengal/rendering/rosettes/
├── __init__.py          # Main API (highlight, tokenize, highlight_many)
├── _config.py           # LexerConfig, FormatConfig, HighlightConfig
├── _escape.py           # HTML escaping utilities
├── _parallel.py         # Parallel tokenization
├── _protocol.py         # Lexer, Formatter protocols
├── _registry.py         # Lazy lexer registry ⚠️ Bengal dependency
├── _types.py            # Token, TokenType
├── delegate.py          # Delegation utilities
├── formatters/
│   ├── __init__.py
│   └── html.py          # HTML formatter
├── lexers/
│   ├── __init__.py
│   ├── _scanners.py     # Shared scanner utilities
│   ├── _state_machine.py # Base class
│   └── *_sm.py          # 55 language lexers
├── themes/
│   ├── __init__.py      # Theme registry ⚠️ Bengal dependency (2 locations)
│   ├── _mapping.py      # Token → Role mapping
│   ├── _palette.py      # SyntaxPalette, AdaptivePalette
│   ├── _roles.py        # SyntaxRole enum
│   └── palettes/
│       └── __init__.py  # Built-in palettes
└── py.typed
```

### Test Files

```
tests/unit/rendering/rosettes/
├── conftest.py
├── test_parallel.py
├── test_registry.py
├── test_thread_safety.py
├── test_types.py
├── edge_cases/          # Unicode, escapes, boundaries, etc.
├── fixtures/            # Python, JavaScript, Rust, Kida fixtures (non-Python files)
├── formatters/          # HTML formatter tests
├── lexers/              # Lexer-specific tests
├── security/            # ReDoS prevention tests
└── themes/              # Palette and CSS generation tests
```

### Bengal Dependencies (to remove)

**1. `_registry.py:371-378`** — Runtime error for unknown languages:
```python
from bengal.errors import BengalRenderingError, ErrorCode

raise BengalRenderingError(
    f"Unknown language: {name!r}. Supported: {_SORTED_LANGUAGES}",
    code=ErrorCode.R011,
    ...
)
```

**2. `themes/__init__.py:139-146`** — Runtime error for unknown palettes:
```python
from bengal.errors import BengalRenderingError, ErrorCode

raise BengalRenderingError(
    f"Unknown syntax theme: {name!r}. Available: {available}",
    code=ErrorCode.R013,
    ...
)
```

**3. `themes/__init__.py:53`** — TYPE_CHECKING import (breaks type checking, not runtime):
```python
if TYPE_CHECKING:
    from bengal.errors import BengalRenderingError, ErrorCode
```

**Fix**: Replace runtime errors with standard `LookupError`, remove TYPE_CHECKING import:
```python
# Runtime errors
raise LookupError(f"Unknown language: {name!r}. Supported: {_SORTED_LANGUAGES}")

# TYPE_CHECKING block — remove Bengal import, update type annotations
```

---

## Implementation Plan

### Phase 1: Prepare Rosettes Repository

**Target**: `/Users/llane/Documents/github/python/rosettes/`

1. **Create package structure**:
   ```
   rosettes/
   ├── pyproject.toml
   ├── README.md
   ├── LICENSE
   ├── src/
   │   └── rosettes/
   │       ├── __init__.py
   │       ├── py.typed
   │       └── ... (all source files)
   └── tests/
       └── ... (all test files)
   ```

2. **Create `pyproject.toml`**:
   ```toml
   [build-system]
   requires = ["setuptools>=61.0"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "rosettes"
   version = "0.3.0"
   description = "Modern syntax highlighting for Python 3.14t — O(n) guaranteed, zero ReDoS"
   readme = "README.md"
   requires-python = ">=3.14"
   license = "MIT"
   keywords = ["syntax-highlighting", "lexer", "free-threading", "pygments"]
   classifiers = [
       "Development Status :: 4 - Beta",
       "Intended Audience :: Developers",
       "Programming Language :: Python :: 3.14",
       "Topic :: Text Processing :: Markup",
   ]
   dependencies = []  # Pure Python, no runtime deps

   [project.urls]
   Homepage = "https://github.com/lbliii/rosettes"
   Documentation = "https://github.com/lbliii/rosettes"
   Repository = "https://github.com/lbliii/rosettes"

   [tool.setuptools.packages.find]
   where = ["src"]
   ```

3. **Create README.md** with:
   - Feature overview (thread-safe, O(n), 55 languages)
   - Quick start examples
   - API reference
   - Pygments compatibility notes

### Phase 2: Copy and Transform Source

1. **Copy source files**:
   ```bash
   cp -r bengal/rendering/rosettes/* rosettes/src/rosettes/
   ```

2. **Transform imports** (automated via script):
   ```python
   # Before
   from bengal.rendering.rosettes._types import Token, TokenType

   # After
   from rosettes._types import Token, TokenType
   ```

3. **Remove Bengal error dependencies** (all use `LookupError`):
   - `_registry.py:371-378`: Replace `BengalRenderingError` → `LookupError`
   - `themes/__init__.py:139-146`: Replace `BengalRenderingError` → `LookupError`
   - `themes/__init__.py:53`: Remove TYPE_CHECKING import, update annotations

4. **Update lexer registry module paths**:
   ```python
   # Before
   "python": LexerSpec("bengal.rendering.rosettes.lexers.python_sm", ...)

   # After
   "python": LexerSpec("rosettes.lexers.python_sm", ...)
   ```

### Phase 3: Copy and Transform Tests

1. **Copy test files**:
   ```bash
   cp -r tests/unit/rendering/rosettes/* rosettes/tests/
   ```

2. **Transform test imports**:
   ```python
   # Before
   from bengal.rendering.rosettes import highlight

   # After
   from rosettes import highlight
   ```

3. **Copy fixtures** (non-Python files preserved as-is):
   ```bash
   # Already handled by copytree in migration script
   ```

4. **Verify test suite passes**:
   ```bash
   cd rosettes && pytest
   ```

### Phase 4: Update Bengal

1. **Add rosettes dependency** to `pyproject.toml`:
   ```toml
   dependencies = [
       "rosettes>=0.3.0",
       # ... existing deps
   ]
   ```

2. **Create deprecation shim** (`bengal/rendering/rosettes/__init__.py`):
   ```python
   """Deprecated: Use `rosettes` package directly.

   This shim provides backward compatibility during the transition period.
   Remove after 1-2 releases.
   """
   import warnings

   warnings.warn(
       "bengal.rendering.rosettes is deprecated. Use 'import rosettes' instead.",
       DeprecationWarning,
       stacklevel=2,
   )

   from rosettes import *  # noqa: F401, F403
   from rosettes import __all__  # noqa: F401
   ```

3. **Update Bengal adapter** (`bengal/rendering/highlighting/rosettes.py`):
   ```python
   # Before
   from bengal.rendering import rosettes
   from bengal.rendering.rosettes.themes import get_palette

   # After
   import rosettes
   from rosettes.themes import get_palette
   ```

4. **Update other Bengal imports** (see Related Files section)

5. **Delete embedded rosettes** (after deprecation period, or immediately if no external consumers):
   ```bash
   rm -rf bengal/rendering/rosettes/
   rm -rf tests/unit/rendering/rosettes/
   ```

### Phase 5: Validation

1. **Run rosettes test suite** in standalone repo
2. **Run Bengal test suite** with external rosettes dependency
3. **Verify import overhead unchanged** (rosettes already lazy-loads)
4. **Test parallel highlighting** works correctly
5. **Verify no remaining Bengal imports in rosettes**:
   ```bash
   grep -r "from bengal" rosettes/src/
   # Should return empty
   ```
6. **Verify type checking passes** in rosettes (pyright/mypy)

---

## Migration Script

Create `scripts/extract_rosettes.py`:

```python
#!/usr/bin/env python3
"""Extract rosettes from Bengal to standalone package."""

import re
import shutil
from pathlib import Path

BENGAL_ROOT = Path("/Users/llane/Documents/github/python/bengal")
ROSETTES_ROOT = Path("/Users/llane/Documents/github/python/rosettes")

# Import transformations
IMPORT_TRANSFORMS: list[tuple[str, str]] = [
    (r"from bengal\.rendering\.rosettes\.", "from rosettes."),
    (r"import bengal\.rendering\.rosettes\.", "import rosettes."),
    (r"bengal\.rendering\.rosettes\.", "rosettes."),
]

# Files requiring special error handling transformation
ERROR_FILES = {
    "_registry.py": {
        "import_pattern": r"from bengal\.errors import BengalRenderingError, ErrorCode\n",
        "import_replacement": "",
        "error_pattern": r"raise BengalRenderingError\(\s*f\"Unknown language: \{name!r\}\. Supported: \{_SORTED_LANGUAGES\}\",\s*code=ErrorCode\.R011,\s*suggestion=[^)]+\)",
        "error_replacement": 'raise LookupError(f"Unknown language: {name!r}. Supported: {_SORTED_LANGUAGES}")',
    },
    "themes/__init__.py": {
        # Remove TYPE_CHECKING import
        "type_checking_pattern": r"\n    from bengal\.errors import BengalRenderingError, ErrorCode\n",
        "type_checking_replacement": "\n",
        # Remove runtime imports (there are 2)
        "import_pattern": r"from bengal\.errors import BengalRenderingError, ErrorCode\n",
        "import_replacement": "",
        # Replace error raises
        "error_pattern": r"raise BengalRenderingError\(\s*f\"Unknown syntax theme: \{name!r\}\. Available: \{available\}\",\s*code=ErrorCode\.R013,\s*suggestion=[^)]+\)",
        "error_replacement": 'raise LookupError(f"Unknown syntax theme: {name!r}. Available: {available}")',
    },
}


def transform_file(content: str, rel_path: str) -> str:
    """Apply all transformations to file content."""
    # Apply standard import transforms
    for pattern, replacement in IMPORT_TRANSFORMS:
        content = re.sub(pattern, replacement, content)

    # Apply file-specific error handling transforms
    rel_str = str(rel_path)
    for file_suffix, transforms in ERROR_FILES.items():
        if rel_str.endswith(file_suffix):
            for key in ["type_checking_pattern", "import_pattern", "error_pattern"]:
                if key in transforms:
                    replacement_key = key.replace("_pattern", "_replacement")
                    content = re.sub(
                        transforms[key],
                        transforms[replacement_key],
                        content,
                        flags=re.DOTALL,
                    )
    return content


def main() -> None:
    # 1. Create directory structure
    src_dir = ROSETTES_ROOT / "src" / "rosettes"
    test_dir = ROSETTES_ROOT / "tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # 2. Copy and transform source files
    source_src = BENGAL_ROOT / "bengal" / "rendering" / "rosettes"
    for py_file in source_src.rglob("*.py"):
        rel_path = py_file.relative_to(source_src)
        dest_path = src_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        content = py_file.read_text()
        content = transform_file(content, str(rel_path))
        dest_path.write_text(content)
        print(f"  ✓ {rel_path}")

    # 3. Copy py.typed marker
    shutil.copy(source_src / "py.typed", src_dir / "py.typed")
    print("  ✓ py.typed")

    # 4. Copy and transform tests
    source_tests = BENGAL_ROOT / "tests" / "unit" / "rendering" / "rosettes"
    for py_file in source_tests.rglob("*.py"):
        rel_path = py_file.relative_to(source_tests)
        dest_path = test_dir / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        content = py_file.read_text()
        content = transform_file(content, str(rel_path))
        dest_path.write_text(content)
        print(f"  ✓ tests/{rel_path}")

    # 5. Copy test fixtures (non-Python files, no transformation needed)
    fixtures_src = source_tests / "fixtures"
    if fixtures_src.exists():
        shutil.copytree(fixtures_src, test_dir / "fixtures", dirs_exist_ok=True)
        print("  ✓ tests/fixtures/ (copied as-is)")

    print(f"\n✅ Extracted rosettes to {ROSETTES_ROOT}")
    print("\nNext steps:")
    print("  1. cd rosettes && uv sync")
    print("  2. pytest")
    print("  3. pyright src/")


if __name__ == "__main__":
    main()
```

---

## Files Changed Summary

### Rosettes Repository (new)

| Path | Action | Notes |
|------|--------|-------|
| `pyproject.toml` | Create | Package metadata, no deps |
| `README.md` | Create | Feature docs, examples |
| `LICENSE` | Create | MIT license |
| `src/rosettes/**/*.py` | Copy + Transform | 73 files, import path changes |
| `tests/**/*.py` | Copy + Transform | 27 files |
| `tests/fixtures/**` | Copy | Non-Python fixture files |

### Bengal Repository (updates)

| Path | Action | Notes |
|------|--------|-------|
| `pyproject.toml` | Update | Add `rosettes>=0.3.0` dependency |
| `bengal/rendering/rosettes/` | Replace with shim | Deprecation wrapper |
| `tests/unit/rendering/rosettes/` | Delete | Tests move to rosettes repo |
| `bengal/rendering/highlighting/rosettes.py` | Update | External import |
| `bengal/rendering/highlighting/__init__.py` | Update | External import |
| `bengal/utils/metadata.py` | Update | External import |
| `bengal/rendering/parsers/patitas/renderers/html.py` | Update | External import |

---

## Related Files

### Bengal files importing rosettes (verified, will need updates)

**Core Bengal:**
```
bengal/rendering/highlighting/rosettes.py
bengal/rendering/highlighting/__init__.py
bengal/rendering/parsers/patitas/renderers/html.py
bengal/utils/metadata.py
```

**Scripts and Benchmarks:**
```
scripts/convert_lexers.py
scripts/benchmark_rosettes_vs_pygments.py
scripts/benchmark_parallel.py
scripts/regenerate_fixtures.py
benchmarks/lexer_benchmark.py
benchmarks/test_import_overhead.py
```

**Note**: `bengal/themes/tokens.py` and `bengal/output/icons.py` contain rosettes branding text (⌾⌾⌾) but no imports — no changes needed.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking Bengal builds | High | Phase 4-5 must be atomic; deprecation shim provides fallback |
| Import overhead increase | Medium | Rosettes already lazy-loads; measure before/after |
| Test fixture mismatches | Low | Copy fixtures alongside tests |
| Version drift | Low | Pin rosettes version in Bengal initially |
| Type checking breaks | Low | Verify pyright/mypy pass after removing TYPE_CHECKING import |
| External consumers break | Low | Deprecation shim with warning; remove after 1-2 releases |

---

## Success Criteria

1. ✅ `pip install rosettes` works
2. ✅ `from rosettes import highlight` works
3. ✅ Rosettes test suite passes (standalone)
4. ✅ Bengal test suite passes (with external rosettes)
5. ✅ No Bengal-specific code in rosettes (`grep -r "from bengal" rosettes/` returns empty)
6. ✅ Import overhead within 5% of current
7. ✅ Type checking passes in rosettes repo

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Prepare repo | 1 hour | None |
| Phase 2: Extract source | 2 hours | Phase 1 |
| Phase 3: Extract tests | 1 hour | Phase 2 |
| Phase 4: Update Bengal | 2 hours | Phase 3 |
| Phase 5: Validation | 1 hour | Phase 4 |
| **Total** | **~7 hours** | |

---

## Appendix: Language Support

Rosettes includes lexers for 55 languages:

**Core**: Python, JavaScript, TypeScript, JSON, YAML, TOML, Bash, HTML, CSS, Diff

**Systems**: C, C++, Rust, Go, Zig

**JVM**: Java, Kotlin, Scala, Groovy, Clojure

**Apple**: Swift

**Scripting**: Ruby, Perl, PHP, Lua, R, PowerShell

**Functional**: Haskell, Elixir

**Data/Query**: SQL, CSV, GraphQL

**Markup**: Markdown, XML

**Config**: INI, Nginx, Dockerfile, Makefile, HCL

**Schema**: Protobuf

**Modern**: Dart, Julia, Nim, Gleam, V

**AI/ML**: Mojo, Triton, CUDA, Stan

**Other**: PKL, CUE, Tree, Kida, Jinja, Plaintext
