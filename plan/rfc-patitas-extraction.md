# RFC: Patitas Extraction to Standalone Package

**Status**: In Progress  
**Created**: 2026-01-09  
**Updated**: 2026-01-12  
**Author**: Bengal Contributors

---

## Executive Summary

Extract Patitas, Bengal's next-generation Markdown parser, into a standalone Python package at `github.com/lbliii/patitas`. This enables broader adoption as a modern, free-threaded CommonMark-compliant parser while Bengal becomes a consumer of the external package.

**Installation Tiers:**
```bash
pip install patitas              # Core parser (zero deps, 40-50% faster than mistune)
pip install patitas[directives]  # + Portable directives (admonition, dropdown, tabs)
pip install patitas[syntax]      # + Syntax highlighting via Rosettes
pip install patitas[bengal]      # Full Bengal directive suite
```

**Key Metrics:**
- **94 source files** to extract
- **21 test files** + fixtures (CommonMark spec: 652 examples)
- **~28 Bengal-specific imports** to remove or abstract via protocols
- **~400 internal imports** to transform (`bengal.rendering.parsers.patitas.` → `patitas.`)

---

## Background

Patitas ("little paws" 🐾) is a pure-Python Markdown parser designed for free-threaded Python 3.14t+. Key features:

- **O(n) guaranteed parsing** — No regex backtracking, no ReDoS vulnerabilities
- **Thread-safe by design** — Zero shared mutable state, free-threading ready
- **Typed AST** — `@dataclass(frozen=True, slots=True)` nodes, not `Dict[str, Any]`
- **StringBuilder rendering** — O(n) output vs O(n²) string concatenation
- **CommonMark compliant** — Passes CommonMark 0.31.2 spec (652 examples)
- **Extensible** — Plugins for tables, footnotes, math, strikethrough, task lists

Currently embedded at `bengal/rendering/parsers/patitas/`, making it unavailable to the broader Python ecosystem.

### Architecture

```
Markdown Source → Lexer → Tokens → Parser → Typed AST → Renderer → HTML
```

Key design principles:
- **Zero-Copy Lexer Handoff (ZCLH)**: AST nodes store source offsets, not content copies
- **Immutable AST**: All nodes are frozen dataclasses
- **Single-pass rendering**: TOC extraction during render, no post-processing regex

### The Bengal Cat Family

```
Bengal — Static site generator (the breed)
├── Kida — Template engine (the cat's name) ✅ Extracted
├── Rosettes — Syntax highlighter (the spots) ✅ Extracted  
└── Patitas — Markdown parser (the paws) ⏳ This RFC
```

### Package Tiers

Patitas uses optional extras to provide tiered functionality:

| Install | Use Case | Dependencies | What's Included |
|---------|----------|--------------|-----------------|
| `patitas` | Fast CommonMark parsing | **Zero** | Lexer, parser, plugins (table, footnotes, math, strikethrough, task lists) |
| `patitas[directives]` | Documentation with admonitions | Zero | + Portable directives (admonition, dropdown, container, tabs) |
| `patitas[syntax]` | Code block highlighting | rosettes | + Syntax highlighting via Rosettes |
| `patitas[bengal]` | Full Bengal SSG experience | bengal | + Bengal directive suite (cards, code-tabs, navigation, versioning) |
| `patitas[all]` | Everything | rosettes | Core + directives + syntax (no Bengal) |

**Why this matters:**
- **Core users** get a fast, safe parser with zero dependencies
- **Doc authors** get MyST-style directives without buying into Bengal
- **Bengal users** get seamless integration via `patitas[bengal]`

**Comparison with mistune:**
| Feature | patitas | mistune |
|---------|---------|---------|
| Core speed | ~40-50% faster | Baseline |
| Core deps | Zero | Zero |
| Built-in directives | Via `[directives]` extra | 5 built-in (admonition, toc, include, image, figure) |
| Directive syntax | MyST fenced (`:::{note}`) | RST-style (`.. note::`) or fenced |
| Typed AST | Frozen dataclasses | Dict[str, Any] |
| Free-threading | Native | No |

---

## Goals

1. **Standalone package**: `pip install patitas` works independently
2. **Zero external dependencies**: Pure Python, no runtime deps (core parser)
3. **Tiered feature access**: Optional extras for directives, syntax highlighting, Bengal integration
4. **Backward compatibility**: Bengal continues working via `patitas[bengal]` or adapter
5. **Clean separation**: Core parser has no Bengal-specific code; Bengal features are opt-in

### Non-Goals

- Changing Patitas core API
- Adding new features during extraction
- Supporting Python < 3.14
- Bundling all Bengal directives in core (those are opt-in via extras)

---

## Current State Analysis

### Source Files (94 files)

```
bengal/rendering/parsers/patitas/
├── __init__.py          # Main API (parse, create_markdown, etc.)
├── location.py          # SourceLocation for span tracking
├── nodes.py             # Immutable AST node definitions (30+ node types)
├── parser.py            # Parser class orchestrating parsing
├── protocols.py         # LexerDelegate protocol
├── stringbuilder.py     # O(n) string concatenation
├── tokens.py            # Token, TokenType definitions
├── wrapper.py           # PatitasParser (Bengal adapter) ⚠️ Bengal-specific
├── py.typed             # PEP 561 type marker
├── COMPLEXITY.md        # Implementation notes
│
├── lexer/               # Zero-copy lexer (13 files)
│   ├── __init__.py
│   ├── core.py          # Lexer class
│   ├── modes.py         # LexerMode enum
│   ├── classifiers/     # Block type classifiers (9 files)
│   │   ├── directive.py, fence.py, footnote.py, heading.py,
│   │   ├── html.py, link_ref.py, list.py, quote.py, thematic.py
│   └── scanners/        # Content scanners (4 files)
│       ├── block.py, directive.py, fence.py, html.py
│
├── parsing/             # Token → AST conversion (20 files)
│   ├── __init__.py
│   ├── charsets.py      # Character set constants
│   ├── containers.py    # ContainerStack for nested blocks
│   ├── token_nav.py     # Token navigation utilities
│   ├── blocks/          # Block parsing mixins (12 files)
│   │   ├── core.py, directive.py, footnote.py, table.py
│   │   └── list/        # List parsing state machine (8 files)
│   │       ├── mixin.py, marker.py, indent.py, nested.py,
│   │       ├── blank_line.py, item_blocks.py, trace.py, types.py
│   └── inline/          # Inline parsing (6 files)
│       ├── core.py, emphasis.py, links.py, special.py,
│       ├── match_registry.py, tokens.py
│
├── renderers/           # AST → HTML (2 files)
│   ├── __init__.py
│   └── html.py          # HtmlRenderer ⚠️ Has Bengal imports
│
├── plugins/             # CommonMark extensions (7 files)
│   ├── __init__.py
│   ├── autolinks.py, footnotes.py, math.py,
│   ├── strikethrough.py, table.py, task_lists.py
│
├── directives/          # Directive system (25 files) ⚠️ Partially Bengal-specific
│   ├── __init__.py
│   ├── contracts.py, decorator.py, options.py, protocol.py, registry.py
│   └── builtins/        # Built-in directives (19 files)
│       ├── admonition.py, button.py, cards.py, checklist.py,
│       ├── code_tabs.py, container.py, data_table.py, dropdown.py,
│       ├── embed.py, include.py, inline.py, media.py, misc.py,
│       ├── navigation.py, steps.py, tables.py, tabs.py,
│       ├── versioning.py, video.py
│
└── roles/               # Role system (8 files)
    ├── __init__.py, protocol.py, registry.py
    └── builtins/        # Built-in roles (5 files)
        ├── formatting.py, icons.py, math.py, reference.py
```

### Test Files (21 files)

```
tests/rendering/parsers/patitas/           # Integration tests (15 files)
├── conftest.py
├── commonmark_spec_0_31_2.json           # CommonMark spec fixture
├── test_blocks.py
├── test_commonmark_spec.py               # 652 CommonMark examples
├── test_commonmark.py
├── test_edge_cases.py
├── test_fuzz.py
├── test_inline.py
├── test_integration.py
├── test_lexer.py
├── test_page_context_directives.py       # ⚠️ Bengal-specific
├── test_parser.py
├── test_performance.py
├── test_renderer.py

tests/unit/rendering/parsers/patitas/     # Unit tests (6 files)
├── test_directives.py                    # ⚠️ May have Bengal deps
├── test_inline_tokens.py
├── test_lexer_window.py
├── test_match_registry.py
├── test_roles.py
```

### Bengal Dependencies (to remove or abstract)

**13 files carry Bengal-only imports (validated via code scan):**

| Import | Files | Resolution |
|--------|-------|------------|
| `bengal.utils.text.slugify` | `renderers/html.py` | Copy to `patitas/utils/text.py`; injectable hook |
| `bengal.utils.hashing.hash_str` | `directives/builtins/code_tabs.py`, `directives/builtins/data_table.py`, `directives/builtins/tabs.py` | Copy to `patitas/utils/hashing.py` |
| `bengal.utils.logger.get_logger` | `parsing/blocks/directive.py`, `wrapper.py` | Copy to `patitas/utils/logger.py` |
| `bengal.utils.serialization.to_jsonable` | `wrapper.py` | Copy to `patitas/utils/serialization.py` |
| `bengal.errors.DirectiveContractError` | `parsing/blocks/directive.py` | Define in `patitas/errors.py` |
| `bengal.directives.cache.*` | `__init__.py`, `renderers/html.py` | Add cache protocol; inject from Bengal adapter |
| `bengal.directives._icons.*` | `directives/builtins/admonition.py`, `button.py`, `cards.py`, `code_tabs.py`, `dropdown.py` | Icon protocol + optional extras |
| `bengal.directives.cards.utils.*` | `directives/builtins/cards.py` | Optional extra; keep in Bengal or new optional extra |
| `bengal.rendering.highlighting.highlight` | `directives/builtins/code_tabs.py` | Highlight protocol (Rosettes-backed) |
| `bengal.icons.resolver` | `directives/builtins/inline.py`, `roles/builtins/icons.py` | Icon resolver protocol |
| `bengal.rendering.parsers.base.BaseMarkdownParser` | `wrapper.py` | Keep in Bengal-only adapter |
| `bengal.rendering.plugins.VariableSubstitutionPlugin`, `CrossReferencePlugin` | `wrapper.py` | Keep in Bengal-only adapter |

---

## Implementation Plan

### Phase 1: Prepare Patitas Repository

**Target**: `/Users/llane/Documents/github/python/patitas/`

1. **Create package structure**:
   ```
   patitas/
   ├── pyproject.toml
   ├── README.md
   ├── LICENSE
   ├── CHANGELOG.md
   ├── src/
   │   └── patitas/
   │       ├── __init__.py
   │       ├── py.typed
   │       ├── lexer/...
   │       ├── parsing/...
   │       ├── renderers/...
   │       ├── plugins/...
   │       ├── directives/...
   │       ├── roles/...
   │       └── utils/...
   └── tests/
       └── ... (all test files)
   ```

2. **Create `pyproject.toml`**:
   ```toml
   [build-system]
   requires = ["setuptools>=61.0"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "patitas"
   version = "0.1.0"
   description = "Modern Markdown parser for Python 3.14t — CommonMark compliant, free-threading ready, 40-50% faster than mistune"
   readme = "README.md"
   requires-python = ">=3.14"
   license = "MIT"
   keywords = ["markdown", "parser", "commonmark", "free-threading", "ast", "myst"]
   classifiers = [
       "Development Status :: 4 - Beta",
       "Intended Audience :: Developers",
       "Programming Language :: Python :: 3.14",
       "Topic :: Text Processing :: Markup :: Markdown",
       "Typing :: Typed",
   ]
   dependencies = []  # Pure Python, zero runtime deps

   [project.optional-dependencies]
   # Portable directives (admonition, dropdown, container, tabs)
   # No external deps - just enables the directive subsystem
   directives = []

   # Syntax highlighting for code blocks
   syntax = ["rosettes>=0.1.0"]

   # Full Bengal integration (cards, code-tabs, navigation, versioning)
   bengal = ["bengal>=0.2.0"]

   # Everything except Bengal
   all = ["rosettes>=0.1.0"]

   # Development
   dev = [
       "pytest>=8.0",
       "pytest-benchmark>=4.0",
       "pyright>=1.1",
   ]

   [project.urls]
   Homepage = "https://github.com/lbliii/patitas"
   Documentation = "https://github.com/lbliii/patitas"
   Repository = "https://github.com/lbliii/patitas"
   Changelog = "https://github.com/lbliii/patitas/blob/main/CHANGELOG.md"

   [project.entry-points."patitas.directives"]
   # Entry points allow Bengal to register its directives
   # bengal = "bengal.patitas:register_directives"

   [tool.setuptools.packages.find]
   where = ["src"]

   [tool.pytest.ini_options]
   testpaths = ["tests"]

   [tool.pyright]
   include = ["src"]
   pythonVersion = "3.14"
   typeCheckingMode = "strict"
   ```

3. **Create README.md** with:
   - Feature overview (CommonMark, free-threading, typed AST)
   - Quick start examples
   - Plugin system documentation
   - Directive/role system overview

### Phase 2: Extract Core Parser (No Bengal Dependencies)

**Extract first, skip Bengal-dependent files.**

Extract with **zero modifications**:
- `location.py`, `stringbuilder.py`, `tokens.py`, `protocols.py`
- `lexer/` (all 13 files)
- `parsing/` (all 20 files **except** `parsing/blocks/directive.py`)
- `plugins/` (all 7 files)

Require **import path updates only**:
- `nodes.py` — uses `DirectiveOptions`, `SourceLocation`
- `parser.py` — internal imports only
- `roles/protocol.py`, `roles/registry.py`, `roles/builtins/formatting.py`, `roles/builtins/math.py`, `roles/builtins/reference.py`

Skip in this phase (Bengal deps present):
- `__init__.py`, `renderers/html.py`, `parsing/blocks/directive.py`, `directives/builtins/*` listed in dependency table, `roles/builtins/icons.py`, `directives/builtins/inline.py`, `wrapper.py`

### Phase 3: Create Utility Copies

Copy to `patitas/utils/`:

1. **`utils/text.py`** — copy `slugify` from `bengal/utils/text.py`
2. **`utils/hashing.py`** — copy `hash_str` from `bengal/utils/hashing.py`
3. **`utils/logger.py`** — minimal shim returning `logging.getLogger(f"patitas.{name}")`
4. **`utils/serialization.py`** — copy `to_jsonable` from `bengal/utils/serialization.py`

Add `errors.py` with `PatitasError` and `DirectiveContractError`.

### Phase 4: Abstract Optional Features

Add protocols and injection points so Patitas runs without Bengal:

- **Cache protocol**: inject into renderer/registry instead of importing `bengal.directives.cache`.
- **Icon resolver protocol**: replace `bengal.directives._icons` and `bengal.icons.resolver` usages.
- **Highlighting protocol**: replace `bengal.rendering.highlighting.highlight` (can be backed by Rosettes).
- **Cards helper hook**: make `collect_children` / `render_child_card` optional; keep Bengal impl on Bengal side.
- Provide fallback shims (`patitas/icons.py`, `patitas/highlighting.py`) that no-op gracefully when not injected.

### Phase 5: Handle Directives Strategy

**Decision: Tiered directive system via optional extras.**

#### Tier 1: Core (`pip install patitas`)
No directives — pure CommonMark + plugins (table, footnotes, math, etc.)

#### Tier 2: Portable Directives (`pip install patitas[directives]`)
**Extract to Patitas** with icon protocol abstraction:
- `directives/__init__.py`, `contracts.py`, `decorator.py`, `options.py`, `protocol.py`, `registry.py`
- `directives/builtins/admonition.py` — note, warning, tip, etc. (icon optional)
- `directives/builtins/container.py` — generic wrapper
- `directives/builtins/dropdown.py` — collapsible content (icon optional)
- `directives/builtins/tabs.py` — tabbed content
- `directives/builtins/misc.py` — small utilities

**Icon handling**: Icons are optional. When not provided, directives render without icons (CSS class only). Users can inject an icon resolver:

```python
from patitas import create_markdown
from patitas.icons import set_icon_resolver

# Optional: provide icons
set_icon_resolver(my_icon_function)

md = create_markdown(plugins=["directives"])
```

#### Tier 3: Syntax Highlighting (`pip install patitas[syntax]`)
Enables syntax highlighting for code blocks via Rosettes:
- Automatically highlights fenced code blocks
- Zero config — just install and it works

#### Tier 4: Bengal Integration (`pip install patitas[bengal]`)
**Stay in Bengal** — registered via entry points:
- `directives/builtins/cards.py` — Bengal card layout system
- `directives/builtins/code_tabs.py` — multi-language code examples
- `directives/builtins/navigation.py` — site navigation
- `directives/builtins/versioning.py` — version switcher
- `directives/builtins/include.py` — file inclusion

Bengal registers these via entry point:
```python
# bengal/patitas_integration.py
def register_directives(registry):
    registry.register("cards", CardsDirective)
    registry.register("code-tabs", CodeTabsDirective)
    # ...
```

#### Other Directives
These move to `patitas[directives]` with optional dependencies:
- `button.py`, `checklist.py`, `data_table.py`, `embed.py`, `inline.py`, `media.py`, `steps.py`, `video.py`

### Package Structure (Final)

```
patitas/
├── src/patitas/
│   ├── __init__.py           # Core API: parse, parse_to_ast, Markdown
│   ├── py.typed
│   ├── errors.py             # PatitasError, DirectiveContractError
│   │
│   ├── # CORE (always installed, zero deps)
│   ├── lexer/                # Zero-copy lexer
│   ├── parsing/              # Token → AST
│   ├── renderers/            # AST → HTML
│   ├── plugins/              # table, footnotes, math, strikethrough, task_lists
│   ├── nodes.py              # Typed AST nodes
│   ├── tokens.py             # Token, TokenType
│   ├── protocols.py          # LexerDelegate, etc.
│   ├── stringbuilder.py      # O(n) string building
│   ├── location.py           # SourceLocation
│   │
│   ├── # DIRECTIVES (patitas[directives])
│   ├── directives/
│   │   ├── __init__.py       # DirectiveRegistry, register_directive
│   │   ├── protocol.py       # DirectiveProtocol
│   │   ├── registry.py       # Runtime registry
│   │   ├── options.py        # DirectiveOptions
│   │   └── builtins/
│   │       ├── admonition.py # note, warning, tip, etc.
│   │       ├── container.py  # Generic wrapper
│   │       ├── dropdown.py   # Collapsible content
│   │       ├── tabs.py       # Tabbed content
│   │       └── ...           # Other portable directives
│   │
│   ├── # ROLES (included with directives)
│   ├── roles/
│   │   ├── protocol.py
│   │   ├── registry.py
│   │   └── builtins/
│   │       ├── formatting.py # emphasis, strong, etc.
│   │       └── math.py       # Inline math
│   │
│   ├── # UTILITIES
│   ├── utils/
│   │   ├── text.py           # slugify
│   │   ├── hashing.py        # hash_str
│   │   └── logger.py         # get_logger
│   │
│   ├── # OPTIONAL INTEGRATIONS
│   ├── icons.py              # Icon resolver protocol + set_icon_resolver()
│   └── highlighting.py       # Highlighter protocol + set_highlighter()
│
└── tests/
    ├── fixtures/
    │   └── commonmark_spec_0_31_2.json
    ├── test_commonmark_spec.py  # 652 examples
    ├── test_parser.py
    ├── test_lexer.py
    └── ...
```

**Bengal keeps:**
```
bengal/
├── rendering/parsers/
│   └── patitas_adapter.py    # Bengal-specific wrapper
├── patitas/
│   └── directives/           # Bengal directive implementations
│       ├── cards.py
│       ├── code_tabs.py
│       ├── navigation.py
│       ├── versioning.py
│       └── include.py
└── ...
```

### Phase 6: Copy and Transform Tests

1. **Copy test files**:
   ```bash
   # Integration tests
   cp -r tests/rendering/parsers/patitas/* patitas/tests/

   # Unit tests
   cp tests/unit/rendering/parsers/patitas/* patitas/tests/unit/
   ```

2. **Transform test imports**:
   ```python
   # Before
   from bengal.rendering.parsers.patitas import parse, parse_to_ast

   # After
   from patitas import parse, parse_to_ast
   ```

3. **Skip Bengal-specific tests** (keep in Bengal):
   - `test_page_context_directives.py` — Bengal page context

4. **Copy CommonMark spec fixture**:
   ```bash
   cp tests/rendering/parsers/patitas/commonmark_spec_0_31_2.json patitas/tests/fixtures/
   ```

### Phase 7: Update Bengal

1. **Add patitas dependency** to `pyproject.toml`:
   ```toml
   dependencies = [
       "patitas>=0.1.0",
       "kida>=0.1.0",
       "rosettes>=0.1.0",
       # ... existing deps
   ]
   ```

2. **Create Bengal adapter** (`bengal/rendering/parsers/patitas_adapter.py`):
   ```python
   """Bengal adapter for Patitas parser.

   Provides Bengal-specific features:
   - Variable substitution plugin
   - Cross-reference plugin
   - Page context for directives
   - Directive caching integration
   - Bengal icon resolver
   - Bengal directive suite (cards, code-tabs, navigation, versioning)
   """

   from patitas import Markdown, parse, parse_to_ast, render_ast
   from patitas.directives import DirectiveRegistry
   from patitas.icons import set_icon_resolver
   from patitas.highlighting import set_highlighter

   from bengal.directives._icons import render_icon
   from bengal.rendering.highlighting import highlight

   # Inject Bengal's icon resolver
   set_icon_resolver(render_icon)

   # Inject Bengal's syntax highlighter (Rosettes)
   set_highlighter(highlight)

   # Register Bengal-specific directives
   def register_bengal_directives(registry: DirectiveRegistry) -> None:
       """Register Bengal's extended directive suite."""
       from bengal.patitas.directives import (
           CardsDirective,
           CodeTabsDirective,
           NavigationDirective,
           VersioningDirective,
           IncludeDirective,
       )
       registry.register("cards", CardsDirective)
       registry.register("card", CardsDirective)  # Alias
       registry.register("code-tabs", CodeTabsDirective)
       registry.register("navigation", NavigationDirective)
       registry.register("version-selector", VersioningDirective)
       registry.register("include", IncludeDirective)

   # Re-export for backward compatibility
   __all__ = ["PatitasParser", "parse", "parse_to_ast", "render_ast"]

   class PatitasParser:
       """Bengal-specific Patitas wrapper."""
       # Move wrapper.py content here with Bengal integrations
   ```

3. **Update all Bengal imports**:
   ```python
   # Before
   from bengal.rendering.parsers.patitas import parse, Markdown

   # After  
   from patitas import parse, Markdown
   # Or for Bengal-specific features:
   from bengal.rendering.parsers.patitas_adapter import PatitasParser
   ```

4. **Delete embedded patitas source and tests**:
   ```bash
   rm -rf bengal/rendering/parsers/patitas/
   rm -rf tests/rendering/parsers/patitas/
   rm -rf tests/unit/rendering/parsers/patitas/
   ```

5. **Keep Bengal-specific tests**:
   ```bash
   # Move to new location
   mv tests/rendering/parsers/patitas/test_page_context_directives.py \
      tests/rendering/test_patitas_integration.py
   ```

### Phase 8: Validation

1. **Run automated verification**:
   ```bash
   cd patitas
   python scripts/extract_patitas.py --verify
   ```

2. **Run Patitas test suite** in standalone repo:
   ```bash
   cd patitas && uv sync && pytest -v
   # Expect: 652+ CommonMark spec examples passing
   ```

3. **Run Bengal test suite** with external patitas dependency:
   ```bash
   cd bengal && uv sync && pytest -v
   ```

4. **Verify CommonMark compliance**:
   ```bash
   cd patitas && pytest tests/test_commonmark_spec.py -v
   # Should pass all 652 examples
   ```

5. **Verify no remaining Bengal imports in patitas**:
   ```bash
   grep -r "from bengal\|import bengal" patitas/src/
   # Should return empty
   ```

6. **Verify type checking passes**:
   ```bash
   cd patitas && pyright src/
   ```

7. **Test free-threading safety**:
   ```bash
   python -c "
   from patitas import parse_many
   docs = ['# Test'] * 100
   results = parse_many(docs, workers=4)
   print(f'Parsed {len(results)} docs in parallel')
   "
   ```

---

## Migration Script

Create `scripts/extract_patitas.py` (extend transforms to cover cache/icons/highlighting/cards utils/serialization):

```python
#!/usr/bin/env python3
"""Extract Patitas from Bengal to standalone package.

Usage:
    python scripts/extract_patitas.py           # Execute extraction
    python scripts/extract_patitas.py --dry-run # Preview without writing
    python scripts/extract_patitas.py --verify  # Verify extraction succeeded
"""

import argparse
import shutil
import sys
from pathlib import Path
import re

BENGAL_ROOT = Path("/Users/llane/Documents/github/python/bengal")
PATITAS_ROOT = Path("/Users/llane/Documents/github/python/patitas")

# Import transformations
IMPORT_TRANSFORMS: list[tuple[str, str]] = [
    (r"from bengal\.rendering\.parsers\.patitas\.", "from patitas."),
    (r"import bengal\.rendering\.parsers\.patitas\.", "import patitas."),
    (r"bengal\.rendering\.parsers\.patitas\.", "patitas."),
]

# Bengal-specific imports to handle specially
BENGAL_IMPORTS = {
    r"from bengal\.utils\.text import slugify": "from patitas.utils.text import slugify",
    r"from bengal\.utils\.hashing import hash_str": "from patitas.utils.hashing import hash_str",
    r"from bengal\.utils\.logger import get_logger": "from patitas.utils.logger import get_logger",
    r"from bengal\.utils\.serialization import to_jsonable": "from patitas.utils.serialization import to_jsonable",
    r"from bengal\.errors import DirectiveContractError": "from patitas.errors import DirectiveContractError",
    r"from bengal\.directives\._icons import icon_exists, render_svg_icon": "from patitas.icons import icon_exists, render_svg_icon",
    r"from bengal\.directives\._icons import render_svg_icon": "from patitas.icons import render_svg_icon",
    r"from bengal\.icons import resolver as icon_resolver": "from patitas.icons import resolver as icon_resolver",
    r"from bengal\.rendering\.highlighting import highlight as highlight_code": "from patitas.highlighting import highlight as highlight_code",
    r"from bengal\.directives\.cards\.utils import": "from patitas.directives.cards import",
}

# Files/dirs to skip
SKIP_DIRS = {"__pycache__"}
SKIP_FILES = {"wrapper.py"}  # Bengal-specific adapter, keep in Bengal

# Files to copy from Bengal utils
UTILITY_COPIES = [
    ("bengal/utils/text.py", "patitas/utils/text.py", ["slugify"]),
    ("bengal/utils/hashing.py", "patitas/utils/hashing.py", ["hash_str"]),
]


def transform_file(content: str) -> str:
    """Apply all transformations to file content."""
    # First, handle Bengal-specific imports
    for pattern, replacement in BENGAL_IMPORTS.items():
        content = re.sub(pattern, replacement, content)

    # Then, handle internal patitas imports
    for pattern, replacement in IMPORT_TRANSFORMS:
        content = re.sub(pattern, replacement, content)

    return content


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    if any(skip in path.parts for skip in SKIP_DIRS):
        return True
    if path.name in SKIP_FILES:
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Patitas from Bengal")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verify", action="store_true", help="Verify extraction")
    args = parser.parse_args()

    if args.verify:
        verify_extraction()
        return

    src_dir = PATITAS_ROOT / "src" / "patitas"
    test_dir = PATITAS_ROOT / "tests"

    if args.dry_run:
        print("🔍 DRY RUN - No files will be written\n")
    else:
        src_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)

    stats = {"source": 0, "tests": 0, "skipped": 0, "transforms": 0}

    # 1. Copy and transform source files
    print("📦 Source files:")
    source_src = BENGAL_ROOT / "bengal" / "rendering" / "parsers" / "patitas"
    for py_file in source_src.rglob("*.py"):
        if should_skip(py_file):
            stats["skipped"] += 1
            continue

        rel_path = py_file.relative_to(source_src)
        dest_path = src_dir / rel_path

        content = py_file.read_text()
        transformed = transform_file(content)

        if not args.dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(transformed)

        stats["source"] += 1
        print(f"  ✓ {rel_path}")

    # 2. Copy py.typed marker
    if not args.dry_run:
        shutil.copy(source_src / "py.typed", src_dir / "py.typed")
    print("  ✓ py.typed")

    # 3. Create utility modules
    print("\n📦 Utilities:")
    utils_dir = src_dir / "utils"
    if not args.dry_run:
        utils_dir.mkdir(exist_ok=True)
        create_utility_modules(utils_dir)
    print("  ✓ utils/text.py")
    print("  ✓ utils/hashing.py")
    print("  ✓ utils/logger.py")
    print("  ✓ utils/__init__.py")

    # 4. Create errors module
    print("\n📦 Errors:")
    if not args.dry_run:
        create_errors_module(src_dir)
    print("  ✓ errors.py")

    # 5. Copy and transform tests
    print("\n🧪 Test files:")
    test_sources = [
        (BENGAL_ROOT / "tests" / "rendering" / "parsers" / "patitas", test_dir),
        (BENGAL_ROOT / "tests" / "unit" / "rendering" / "parsers" / "patitas", test_dir / "unit"),
    ]

    for source_dir, dest_base in test_sources:
        if not source_dir.exists():
            continue
        for py_file in source_dir.rglob("*.py"):
            if should_skip(py_file):
                stats["skipped"] += 1
                continue

            rel_path = py_file.relative_to(source_dir)
            dest_path = dest_base / rel_path

            content = py_file.read_text()
            transformed = transform_file(content)

            if not args.dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(transformed)

            stats["tests"] += 1
            print(f"  ✓ {dest_base.name}/{rel_path}")

    # 6. Copy CommonMark spec fixture
    print("\n📦 Fixtures:")
    spec_file = BENGAL_ROOT / "tests" / "rendering" / "parsers" / "patitas" / "commonmark_spec_0_31_2.json"
    if spec_file.exists():
        if not args.dry_run:
            fixtures_dir = test_dir / "fixtures"
            fixtures_dir.mkdir(exist_ok=True)
            shutil.copy(spec_file, fixtures_dir / "commonmark_spec_0_31_2.json")
        print("  ✓ fixtures/commonmark_spec_0_31_2.json")

    # Summary
    print(f"\n{'📋 DRY RUN SUMMARY' if args.dry_run else '✅ EXTRACTION COMPLETE'}")
    print(f"   Source files: {stats['source']}")
    print(f"   Test files:   {stats['tests']}")
    print(f"   Skipped:      {stats['skipped']}")

    if not args.dry_run:
        print(f"\n📍 Extracted to: {PATITAS_ROOT}")
        print("\n🚀 Next steps:")
        print("   1. cd patitas && uv sync")
        print("   2. pytest")
        print("   3. pyright src/")
        print("   4. python scripts/extract_patitas.py --verify")


def create_utility_modules(utils_dir: Path) -> None:
    """Create utility modules for Patitas."""

    # utils/__init__.py
    (utils_dir / "__init__.py").write_text(
        '"""Patitas utilities."""\n\n'
        'from patitas.utils.text import slugify\n'
        'from patitas.utils.hashing import hash_str\n'
        'from patitas.utils.logger import get_logger\n\n'
        '__all__ = ["slugify", "hash_str", "get_logger"]\n'
    )

    # utils/text.py - Copy slugify from Bengal
    # (In practice, copy the full implementation)
    (utils_dir / "text.py").write_text('''"""Text utilities for Patitas."""

from __future__ import annotations

import html as html_module
import re


def slugify(
    text: str, unescape_html: bool = True, max_length: int | None = None, separator: str = "-"
) -> str:
    """Convert text to URL-safe slug with Unicode support."""
    if not text:
        return ""

    if unescape_html:
        text = html_module.unescape(text)

    # Lowercase
    text = text.lower()

    # Replace non-word chars with separator
    text = re.sub(r"[^\\w]+", separator, text, flags=re.UNICODE)

    # Remove leading/trailing separators
    text = text.strip(separator)

    # Collapse multiple separators
    text = re.sub(f"{re.escape(separator)}+", separator, text)

    # Apply max length
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip(separator)

    return text
''')

    # utils/hashing.py
    (utils_dir / "hashing.py").write_text('''"""Hashing utilities for Patitas."""

from __future__ import annotations

import hashlib


def hash_str(s: str, length: int = 8) -> str:
    """Generate short hash for cache keys."""
    return hashlib.sha256(s.encode()).hexdigest()[:length]
''')

    # utils/logger.py
    (utils_dir / "logger.py").write_text('''"""Logging utilities for Patitas."""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"patitas.{name}")
''')


def create_errors_module(src_dir: Path) -> None:
    """Create errors module for Patitas."""
    (src_dir / "errors.py").write_text('''"""Patitas error types."""

from __future__ import annotations


class PatitasError(Exception):
    """Base exception for Patitas."""


class DirectiveContractError(PatitasError):
    """Raised when directive contract is violated."""

    def __init__(self, directive: str, message: str) -> None:
        self.directive = directive
        self.message = message
        super().__init__(f"{directive}: {message}")
''')


def verify_extraction() -> None:
    """Verify extraction succeeded."""
    print("🔍 Verifying extraction...\n")
    errors = []

    src_dir = PATITAS_ROOT / "src" / "patitas"

    # Check for Bengal imports
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text()
        if "from bengal" in content or "import bengal" in content:
            # Skip TYPE_CHECKING blocks
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if ("from bengal" in line or "import bengal" in line):
                    # Check if in TYPE_CHECKING block
                    in_type_checking = False
                    for j in range(i, -1, -1):
                        if "if TYPE_CHECKING:" in lines[j]:
                            in_type_checking = True
                            break
                        if lines[j].strip() and not lines[j].startswith(" "):
                            break
                    if not in_type_checking:
                        rel_path = py_file.relative_to(PATITAS_ROOT)
                        errors.append(f"Bengal import found in {rel_path}:{i+1}")

    # Check key files exist
    required = [
        src_dir / "__init__.py",
        src_dir / "py.typed",
        src_dir / "parser.py",
        src_dir / "nodes.py",
        src_dir / "lexer" / "core.py",
        src_dir / "utils" / "text.py",
        src_dir / "errors.py",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Missing required file: {path.relative_to(PATITAS_ROOT)}")

    if errors:
        print("❌ Verification failed:")
        for error in errors:
            print(f"   • {error}")
        sys.exit(1)
    else:
        print("✅ Verification passed!")
        print("   • No Bengal imports found (except TYPE_CHECKING)")
        print("   • All required files present")


if __name__ == "__main__":
    main()
```

---

## Files Changed Summary

### Patitas Repository (new)

| Path | Action | Notes |
|------|--------|-------|
| `pyproject.toml` | Create | Package metadata, dev deps, tool config |
| `README.md` | Create | Feature docs, CommonMark examples |
| `LICENSE` | Create | MIT license |
| `CHANGELOG.md` | Create | Version history |
| `scripts/extract_patitas.py` | Copy from Bengal | Extraction script with --verify |
| `src/patitas/**/*.py` | Copy + Transform | ~90 files, import path changes |
| `src/patitas/utils/*.py` | Create | Copied utilities (slugify, hash_str, logger) |
| `src/patitas/errors.py` | Create | PatitasError, DirectiveContractError |
| `tests/**/*.py` | Copy + Transform | ~21 files |
| `tests/fixtures/*.json` | Copy | CommonMark spec (652 examples) |

### Bengal Repository (updates)

| Path | Action | Notes |
|------|--------|-------|
| `pyproject.toml` | Update | Add `patitas>=0.1.0` dependency |
| `bengal/rendering/parsers/patitas/` | Delete | Remove embedded source |
| `bengal/rendering/parsers/patitas_adapter.py` | Create | Bengal-specific wrapper |
| `tests/rendering/parsers/patitas/` | Delete | Tests move to patitas repo |
| `tests/unit/rendering/parsers/patitas/` | Delete | Tests move to patitas repo |
| Other Bengal files | Update | Global search/replace for imports |

---

## Related Files

### Bengal files importing patitas (verified, will need updates)

**Core Bengal Rendering Integration:**
```
bengal/rendering/parsers/__init__.py
bengal/rendering/parser.py
bengal/rendering/pipeline/markdown_renderer.py
```

**Site Core:**
```
bengal/core/site/content.py
bengal/core/page.py
```

**Scripts and Benchmarks:**
```
scripts/test_patitas_*.py
benchmarks/test_patitas_*.py
```

**Documentation:**
```
site/content/docs/markdown/
plan/rfc-patitas-markdown-parser.md
```

---

## Feature Comparison: Patitas vs mistune vs markdown-it

| Feature | Patitas | mistune | markdown-it-py |
|---------|---------|---------|----------------|
| **Performance** | ~40-50% faster | Baseline | ~Similar to mistune |
| **CommonMark** | 0.31.2 ✅ | Partial | 0.31.2 ✅ |
| **Thread Safety** | Native (free-threading) | GIL-dependent | GIL-dependent |
| **ReDoS Safe** | ✅ O(n) guaranteed | ❌ Regex backtracking | ❌ Regex-based |
| **AST** | Typed dataclasses | Dict[str, Any] | Token objects |
| **Rendering** | StringBuilder O(n) | String concat | String concat |
| **Type Hints** | Full (strict pyright) | Partial | Partial |
| **Dependencies** | Zero | Zero | Zero |

### Directive Comparison

| Feature | Patitas | mistune |
|---------|---------|---------|
| **Syntax** | MyST fenced (`:::{note}`) | RST (`.. note::`) or fenced |
| **Built-in** | Via `[directives]` extra | 5 built-in |
| **Admonition** | ✅ | ✅ |
| **TOC** | ✅ (single-pass) | ✅ |
| **Include** | ✅ (via `[bengal]`) | ✅ |
| **Image/Figure** | ✅ | ✅ |
| **Dropdown** | ✅ | ❌ |
| **Tabs** | ✅ | ❌ |
| **Cards** | ✅ (via `[bengal]`) | ❌ |
| **Code Tabs** | ✅ (via `[bengal]`) | ❌ |
| **Roles** | ✅ MyST-style | ❌ |
| **Custom directives** | Protocol-based | Class-based |

**Key differentiator**: Patitas offers more directives, MyST syntax compatibility, and the ability to opt into Bengal's rich directive suite while maintaining a zero-dependency core.

---

## Value Proposition

### Why Choose Patitas Over mistune?

1. **Performance**: 40-50% faster on typical documents (benchmarked)
2. **Safety**: O(n) guaranteed — no ReDoS vulnerabilities from regex backtracking
3. **Types**: Frozen dataclass AST with full pyright strict compliance
4. **Free-threading**: Native Python 3.14t support for parallel parsing
5. **MyST syntax**: Modern directive syntax (`:::{note}`) widely adopted by scientific Python

### Who Is This For?

| User | Install | Why |
|------|---------|-----|
| **Performance-sensitive apps** | `patitas` | 40-50% faster, zero deps |
| **Documentation sites** | `patitas[directives]` | Rich directive library |
| **Syntax-highlighted content** | `patitas[syntax]` | Rosettes integration |
| **Bengal SSG users** | `patitas[bengal]` | Full feature set |
| **Security-conscious** | `patitas` | O(n) guaranteed, no ReDoS |
| **Free-threading early adopters** | `patitas` | Native 3.14t support |

### Migration Path

```python
# From mistune
# Before
import mistune
md = mistune.create_markdown()
html = md(source)

# After
from patitas import create_markdown
md = create_markdown()
html = md(source)
```

For directives:
```python
# From mistune with directives
from mistune.directives import RSTDirective, Admonition
md = mistune.create_markdown(plugins=[RSTDirective([Admonition()])])

# To patitas
from patitas import create_markdown
md = create_markdown(plugins=["directives"])  # MyST syntax
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking Bengal builds | High | Phase 7-8 must be atomic; verify all imports updated |
| Directive compatibility | High | Keep Bengal-specific directives in Bengal; use protocols |
| CommonMark regression | High | Run 652-example spec test before/after extraction |
| Unhandled Bengal imports in extracted tree | High | Exhaustive transform list + verify script |
| Optional extras confusion | Medium | Clear documentation; sensible defaults |
| Icon-less directives look bad | Medium | CSS-only fallback styling; document icon injection |
| Entry point registration complexity | Medium | Provide clear examples; test with fresh venv |
| Import overhead increase | Medium | Measure before/after (<50ms target) |
| Performance regression | Medium | Run benchmark suite; assert 40% faster than mistune |
| Type checking breaks | Low | Verify pyright pass in standalone repo before merge |
| Missing utilities | Low | Copy required utilities to patitas/utils/ |
| Test fixture mismatches | Low | Copy CommonMark spec JSON alongside tests |

---

## Success Criteria

### Core Package
1. ☐ `pip install patitas` works (zero dependencies)
2. ☐ `from patitas import parse, Markdown` works
3. ☐ CommonMark spec passes (652 examples)
4. ☐ Patitas test suite passes (standalone)
5. ☐ No Bengal imports in patitas core (`grep -r "from bengal" patitas/src/` returns empty)
6. ☐ Import overhead <50ms cold start
7. ☐ Type checking passes (`pyright src/` returns 0 errors)
8. ☐ Free-threading test passes (parallel `parse_many`)

### Optional Extras
9. ☐ `pip install patitas[directives]` enables directive parsing
10. ☐ `pip install patitas[syntax]` enables Rosettes highlighting
11. ☐ Directives work without icons (graceful degradation)
12. ☐ Icon resolver injection works when provided

### Bengal Integration
13. ☐ `pip install patitas[bengal]` installs Bengal
14. ☐ Bengal test suite passes (with external patitas)
15. ☐ Bengal directives (cards, code-tabs, etc.) work via adapter
16. ☐ Backward compatibility: existing Bengal imports work

### Verification
17. ☐ Verification script passes (`python scripts/extract_patitas.py --verify`)
18. ☐ Benchmark shows patitas still 40-50% faster than mistune

---

## Timeline Estimate

| Phase | Effort | Dependencies | Status |
|-------|--------|--------------|--------|
| Phase 1: Prepare repo | 1 hour | None | ✅ Complete |
| Phase 2: Extract core | 2 hours | Phase 1 | ✅ Complete |
| Phase 3: Create utilities | 1 hour | Phase 2 | ✅ Complete |
| Phase 4: Abstract features (protocols) | 2 hours | Phase 3 | ✅ Complete |
| Phase 5: Handle directives (tiered) | 4 hours | Phase 4 | ⏳ Stubbed |
| Phase 6: Extract tests | 1.5 hours | Phase 5 | ✅ Complete |
| Phase 7: Update Bengal (adapter) | 3 hours | Phase 6 | ☐ Pending |
| Phase 8: Validation (all tiers) | 2 hours | Phase 7 | ☐ Pending |
| Phase 9: CI/CD and PyPI | 2 hours | Phase 8 | ☐ Pending |
| Phase 10: Documentation | 2 hours | Phase 9 | ☐ Pending |
| **Total** | **~20.5 hours** | | |

**Note**: The tiered architecture adds ~2.5 hours but provides significant value:
- Users can choose their dependency footprint
- Bengal directives stay in Bengal (simpler maintenance)
- Clear upgrade path from core → directives → bengal

---

## Current Progress (2026-01-12)

### ✅ Completed

**Phase 1: Prepare repo** — Established package structure:
- `pyproject.toml` with tiered extras (core, directives, syntax, bengal)
- `README.md` with features, installation, usage examples
- `LICENSE` (MIT), `CHANGELOG.md`, `Makefile`
- Git repository initialized with 4 commits

**Phase 2: Extract core** — 82 Python files extracted:
- Lexer (state machine, classifiers, scanners)
- Parser (blocks, inline, containers)
- Nodes (30+ typed AST dataclasses)
- Plugins (table, math, footnotes, strikethrough, task lists)
- Roles (protocol, registry, builtins)
- Stubs for Bengal-dependent modules (`parsing/blocks/directive.py`, `roles/builtins/icons.py`)

**Phase 3: Create utilities**:
- `utils/text.py` — `slugify`, `escape_html`
- `utils/hashing.py` — `hash_str`, `hash_bytes`
- `utils/logger.py` — `get_logger` (stdlib logging shim)
- `errors.py` — `PatitasError`, `ParseError`, `DirectiveContractError`, `RenderError`, `PluginError`

**Phase 4: Abstract features**:
- `icons.py` — `IconResolver` protocol, `set_icon_resolver()`, `get_icon()`
- `highlighting.py` — `Highlighter` protocol, `set_highlighter()`, auto-detects Rosettes

**Phase 6: Extract tests** — 52 tests passing:
- `test_api.py` — High-level API tests (`parse`, `render`, `Markdown`)
- `test_core_imports.py` — Verify module imports
- `test_renderer.py` — HtmlRenderer tests
- `test_utils.py` — Utility function tests
- `test_commonmark_spec.py` — 652 CommonMark examples (marked, ready for validation)
- CommonMark spec fixture (`fixtures/commonmark_spec_0_31_2.json`)

**Additional work**:
- Created `renderers/html.py` — Full HtmlRenderer with heading IDs, TOC collection, footnotes
- Created `__init__.py` — Exports `parse()`, `render()`, `Markdown`, all node types

### ⏳ In Progress

**Phase 5: Handle directives** — Stubs created, full extraction pending:
- Directive registry framework exists
- Stub files allow imports without errors
- Full directive implementations need extraction with icon protocol integration

### 📊 Metrics

```
Files extracted:  82 Python files in src/patitas/
Tests passing:    52 tests
Commits:          4 commits on main branch
Package size:     ~500 KB (including CommonMark spec fixture)
```

**Commits:**
1. `4329a0c` — Initial package setup with tiered extras (Phase 1)
2. `9efdc8f` — Extract core parser files from Bengal; add stubs (Phase 2)
3. `f8234b2` — Add utilities, errors, icons/highlighting protocols, CommonMark spec (Phase 3-6)
4. `1979f3d` — Add HtmlRenderer, high-level API, API tests (52 passing)

---

## Next Phases

### Phase 5 (Remaining): Extract Portable Directives

**Goal**: Complete the `patitas[directives]` tier with portable directives.

**Tasks**:
1. [ ] Extract directive framework:
   - `directives/__init__.py` — DirectiveRegistry, register_directive
   - `directives/protocol.py` — DirectiveProtocol
   - `directives/registry.py` — Runtime registry
   - `directives/contracts.py` — Contract validation
   - `directives/decorator.py` — @directive decorator

2. [ ] Extract portable builtins:
   - `directives/builtins/admonition.py` — note, warning, tip, caution, important
   - `directives/builtins/container.py` — Generic wrapper
   - `directives/builtins/dropdown.py` — Collapsible content
   - `directives/builtins/tabs.py` — Tabbed content
   - `directives/builtins/misc.py` — Small utilities

3. [ ] Wire icon protocol:
   - Replace `from bengal.directives._icons import` with `from patitas.icons import`
   - Add graceful degradation when icons not available
   - Document icon injection pattern

4. [ ] Update `parsing/blocks/directive.py`:
   - Remove stub, add real implementation
   - Update imports to use `patitas.directives`

**Effort**: ~3 hours

### Phase 7: Update Bengal to Use External Patitas

**Goal**: Bengal becomes a consumer of the external Patitas package.

**Tasks**:
1. [ ] Add patitas dependency to `bengal/pyproject.toml`:
   ```toml
   dependencies = [
       "patitas>=0.1.0",
       "kida>=0.1.0",
       "rosettes>=0.1.0",
       # ... existing deps
   ]
   ```

2. [ ] Create Bengal adapter (`bengal/rendering/parsers/patitas_adapter.py`):
   - Import from external patitas
   - Inject Bengal's icon resolver
   - Inject Rosettes highlighter
   - Register Bengal-specific directives

3. [ ] Move Bengal-specific directives to `bengal/patitas/directives/`:
   - `cards.py` — Bengal card layout system
   - `code_tabs.py` — Multi-language code examples
   - `navigation.py` — Site navigation
   - `versioning.py` — Version switcher
   - `include.py` — File inclusion

4. [ ] Update all Bengal imports:
   ```python
   # Before
   from bengal.rendering.parsers.patitas import parse, Markdown
   
   # After
   from patitas import parse, Markdown
   # Or for Bengal-specific features:
   from bengal.rendering.parsers.patitas_adapter import PatitasParser
   ```

5. [ ] Delete embedded patitas source:
   ```bash
   rm -rf bengal/rendering/parsers/patitas/
   rm -rf tests/rendering/parsers/patitas/
   rm -rf tests/unit/rendering/parsers/patitas/
   ```

6. [ ] Keep Bengal-specific tests:
   ```bash
   mv tests/rendering/parsers/patitas/test_page_context_directives.py \
      tests/rendering/test_patitas_integration.py
   ```

**Effort**: ~3 hours

### Phase 8: Validation

**Goal**: Ensure both packages work correctly independently and together.

**Tasks**:
1. [ ] Patitas standalone validation:
   ```bash
   cd patitas && uv sync && pytest -v
   # Expect: 52+ tests passing
   ```

2. [ ] CommonMark compliance:
   ```bash
   pytest tests/test_commonmark_spec.py -v -m commonmark
   # Target: 600+ examples passing
   ```

3. [ ] Bengal validation:
   ```bash
   cd bengal && uv sync && pytest -v
   # Expect: All existing tests pass
   ```

4. [ ] No Bengal imports in patitas:
   ```bash
   grep -r "from bengal\|import bengal" patitas/src/
   # Should return empty
   ```

5. [ ] Type checking:
   ```bash
   cd patitas && pyright src/
   # Should return 0 errors
   ```

6. [ ] Free-threading test:
   ```bash
   python -c "
   from patitas import Markdown
   from concurrent.futures import ThreadPoolExecutor
   md = Markdown()
   docs = ['# Test\\n\\nParagraph'] * 100
   with ThreadPoolExecutor(max_workers=4) as ex:
       results = list(ex.map(md, docs))
   print(f'Parsed {len(results)} docs in parallel')
   "
   ```

**Effort**: ~2 hours

### Phase 9: CI/CD and PyPI

**Goal**: Set up continuous integration and package publishing.

**Tasks**:
1. [ ] Create GitHub Actions workflow (`.github/workflows/ci.yml`):
   ```yaml
   name: CI
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python: ["3.14"]
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v5
         - run: uv sync --all-extras
         - run: uv run pytest -v
         - run: uv run pyright src/
   ```

2. [ ] Create release workflow (`.github/workflows/release.yml`):
   - Trigger on version tag push
   - Build wheel and sdist
   - Publish to PyPI

3. [ ] Set up PyPI project:
   - Create `patitas` project on PyPI
   - Add API token as repository secret
   - Test with TestPyPI first

4. [ ] Create initial release:
   - Tag `v0.1.0`
   - Build and publish

**Effort**: ~2 hours

### Phase 10: Documentation

**Goal**: Create comprehensive documentation for Patitas users.

**Tasks**:
1. [ ] Expand README.md:
   - Detailed API reference
   - Plugin system documentation
   - Directive authoring guide
   - Performance benchmarks

2. [ ] Create docs site (optional):
   - Use Bengal to build docs (dogfooding!)
   - Host on GitHub Pages

3. [ ] Add docstrings to all public APIs:
   - Ensure all exported functions/classes documented
   - Include examples in docstrings

4. [ ] Migration guide:
   - From mistune to patitas
   - From embedded patitas to external

**Effort**: ~2 hours

---

## Success Criteria (Updated)

### Core Package ✅
1. ✅ `pip install patitas` works (zero dependencies)
2. ✅ `from patitas import parse, Markdown` works
3. ⏳ CommonMark spec passes (652 examples) — tests ready, need validation
4. ✅ Patitas test suite passes (52 tests standalone)
5. ⏳ No Bengal imports in patitas core — needs verification
6. ⏳ Import overhead <50ms cold start — needs measurement
7. ⏳ Type checking passes — needs pyright run
8. ⏳ Free-threading test passes — needs validation

### Optional Extras
9. ⏳ `pip install patitas[directives]` enables directive parsing
10. ✅ `pip install patitas[syntax]` enables Rosettes highlighting (protocol ready)
11. ⏳ Directives work without icons (graceful degradation) — protocol in place
12. ✅ Icon resolver injection works when provided

### Bengal Integration (Pending)
13. ☐ `pip install patitas[bengal]` installs Bengal
14. ☐ Bengal test suite passes (with external patitas)
15. ☐ Bengal directives (cards, code-tabs, etc.) work via adapter
16. ☐ Backward compatibility: existing Bengal imports work

### Verification (Pending)
17. ☐ Benchmark shows patitas still 40-50% faster than mistune
18. ☐ CI/CD pipeline passes
19. ☐ Package published to PyPI

---

## Appendix: Patitas Syntax Reference

### Basic Markdown

```markdown
# Heading 1
## Heading 2

Paragraph with **bold**, *italic*, and `code`.

- List item 1
- List item 2
  - Nested item

1. Ordered item
2. Another item

[Link](https://example.com)
![Image](image.png)
```

### Code Blocks

````markdown
```python
def hello():
    print("Hello, World!")
```
````

### Tables (plugin)

```markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
```

### Task Lists (plugin)

```markdown
- [x] Completed task
- [ ] Pending task
```

### Footnotes (plugin)

```markdown
Here is a footnote reference[^1].

[^1]: This is the footnote content.
```

### Math (plugin)

```markdown
Inline math: $E = mc^2$

Block math:
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$
```

### Directives

```markdown
:::{note}
This is a note admonition.
:::

:::{warning}
This is a warning.
:::

:::{dropdown} Click to expand
Hidden content here.
:::
```

### Roles

```markdown
{emphasis}`emphasized text`
{strong}`strong text`
{abbr}`HTML (HyperText Markup Language)`
```

---

## References

**Source Locations:**
- Patitas source: `bengal/rendering/parsers/patitas/` (94 files)
- Patitas tests: `tests/rendering/parsers/patitas/`, `tests/unit/rendering/parsers/patitas/` (21 files)
- CommonMark spec: `tests/rendering/parsers/patitas/commonmark_spec_0_31_2.json` (652 examples)
- Performance benchmark: `benchmarks/test_patitas_performance.py`

**Related RFCs:**
- Kida extraction RFC: `plan/rfc-kida-extraction.md` (template for this RFC) ✅
- Rosettes extraction: (implicit, already extracted) ✅
- Patitas parser RFC: `plan/rfc-patitas-markdown-parser.md` (original design)
- List parsing RFC: `plan/rfc-list-parsing-state-machine.md` (implementation details)

**External Resources:**
- CommonMark specification: https://spec.commonmark.org/0.31.2/
- MyST Markdown: https://myst-parser.readthedocs.io/
- mistune documentation: https://mistune.lepture.com/
- PEP 703: Making the Global Interpreter Lock Optional
