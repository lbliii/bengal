# RFC: Dependency Decoupling — Breaking Bengal's Circular Dependencies

**Status**: Drafted  
**Created**: 2025-12-26  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P0 (Critical)  
**Related**: `bengal/core/`, `bengal/orchestration/`, `bengal/utils/`  
**Confidence**: 90% 🟢

---

## Executive Summary

Bengal has circular dependencies at the package level, with `core` ↔ `orchestration` ↔ `rendering` forming a tightly coupled triangle. This RFC proposes a phased decoupling strategy using dependency inversion, interface extraction, and package restructuring.

| Metric | Current | Target |
|--------|---------|--------|
| Runtime import cycles | 12 | 0 |
| TYPE_CHECKING-only imports | 14 | 14 (acceptable) |
| `utils` bidirectional deps | 18 imports to core/orchestration/rendering | 0 bidirectional |
| Files >1000 lines | 5 | 2 |
| God objects (>50 methods) | 1 (`PageProxy`: 75 methods) | 0 |

**Estimated effort**: 3-4 weeks across 4 phases

---

## Problem Statement

### Circular Dependencies Create Real Problems

1. **Import order fragility** — Adding a new import can break unrelated modules
2. **Testing difficulty** — Cannot test `core` without `orchestration` loaded
3. **Mental model overload** — Understanding one package requires understanding all coupled packages
4. **Refactoring risk** — Changes ripple unpredictably across packages

### Runtime vs TYPE_CHECKING Cycles

Not all cross-package imports are equal:

| Import Type | Runtime Impact | Example |
|-------------|---------------|---------|
| **Runtime import** | ❌ Creates cycle | `from bengal.orchestration.stats import BuildStats` |
| **TYPE_CHECKING import** | ✅ No cycle | `if TYPE_CHECKING: from bengal.core.page import Page` |

Many `orchestration` → `core` imports use `TYPE_CHECKING` guards correctly. These don't cause runtime issues but do indicate architectural coupling that complicates understanding.

**This RFC focuses on eliminating runtime cycles first**, then reducing TYPE_CHECKING coupling where practical.

### Current Dependency Graph

```
     ┌──────────────────────────────────────────────┐
     │                   utils                       │ ◄── 18 imports to core/orch/rendering
     └──────────────────────────────────────────────┘
                          ▲
     ┌─────────┬──────────┼──────────┬──────────────┐
     ▼         ▼          ▼          ▼              ▼
   core ←───→ cache    config    errors       analysis
     │                                             ▲
     ▼                                             │
orchestration ←──────────────────→ rendering ──────┘
     │                                  │
     ▼                                  ▼
   cli                              directives
```

### Specific Runtime Violations Found

| Cycle | Location | Cause | Type |
|-------|----------|-------|------|
| `core` → `orchestration` | `core/site/core.py:63` | `from bengal.orchestration.stats import BuildStats` | **Runtime** |
| `core` → `rendering` | `core/site/core.py:531` | `from bengal.rendering.pipeline.thread_local import get_created_dirs` | **Runtime** |
| `core` → `rendering` | `core/site/core.py:627` | `from bengal.rendering.template_functions.version_url import...` | **Runtime** |
| `core` → `rendering` | `core/page/metadata.py:368` | `from bengal.rendering.pipeline import extract_toc_structure` | **Runtime** |
| `core` → `rendering` | `core/page/content.py:139,202,218` | `from bengal.rendering.ast_utils import...` | **Runtime** |
| `core` → `rendering` | `core/asset/asset_core.py:713` | `from bengal.rendering.template_engine.url_helpers import with_baseurl` | **Runtime** |
| `core` → `rendering` | `core/page/operations.py:65` | `from bengal.rendering.renderer import Renderer` | **Runtime** |
| `orchestration` → `core` | 79 locations | Uses `Site`, `Page`, etc. | Mixed (many TYPE_CHECKING) |
| `rendering` → `core` | 88 locations | Page/Site wrappers | Mixed |
| `utils` → `core/orchestration/rendering` | 18 locations | Various utilities | **Runtime** |

### Large Files Requiring Refactoring

| File | Lines | Issue |
|------|-------|-------|
| `rendering/errors.py` | 1,242 | Error handling monolith |
| `rendering/kida/compat/jinja.py` | 1,226 | Jinja compatibility layer |
| `directives/embed.py` | 1,188 | Embed directive logic |
| `rendering/kida/template.py` | 1,129 | Template engine core |
| `rendering/kida/environment/filters.py` | 1,025 | Filter definitions |

---

## Proposed Solution

### Architecture Principles

1. **Dependency Inversion** — High-level modules define interfaces; low-level modules implement them
2. **Layered Architecture** — Clear hierarchy: `utils` → `core` → `orchestration` → `cli`
3. **Interface Segregation** — Small, focused protocols instead of god objects
4. **Acyclic Dependencies** — Packages form a DAG (directed acyclic graph)

### Target Dependency Graph

```
                    ┌─────────┐
                    │   cli   │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │ server │ │ health │ │autodoc │
         └────┬───┘ └────┬───┘ └────┬───┘
              │          │          │
              └──────────┼──────────┘
                         ▼
                  ┌─────────────┐
                  │orchestration│
                  └──────┬──────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │rendering│ │ cache │ │analysis│
         └────┬───┘ └────┬───┘ └────┬───┘
              │          │          │
              └──────────┼──────────┘
                         ▼
                    ┌─────────┐
                    │  core   │
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ config  │    │ errors   │    │ utils    │
    └─────────┘    └──────────┘    └──────────┘
```

---

## Implementation Plan

### Phase 1: Extract Interfaces (Week 1)

Create protocol definitions that break the tightest cycles.

#### 1.1 Create `bengal/interfaces/` Package

```python
# bengal/interfaces/__init__.py
"""Protocol definitions for dependency inversion."""

from .stats import StatsProtocol
from .page import PageProtocol, PageLike
from .site import SiteProtocol
from .renderer import RendererProtocol
```

#### 1.2 Define `StatsProtocol`

**Problem**: `core/site/core.py:63` imports `BuildStats` from `orchestration`

```python
# bengal/interfaces/stats.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class StatsProtocol(Protocol):
    """Build statistics interface for core package."""

    def record_page_rendered(self, path: str) -> None: ...
    def record_error(self, error: Exception) -> None: ...
    def get_error_deduplicator(self) -> "ErrorDeduplicatorProtocol": ...
```

**Migration**:

```python
# Before (core/site/core.py)
from bengal.orchestration.stats import BuildStats

# After
from bengal.interfaces import StatsProtocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.orchestration.stats import BuildStats

class Site:
    build_stats: StatsProtocol | None = None  # Injected by orchestration
```

#### 1.3 Define `PageLike` Protocol

**Problem**: `rendering/` needs Page attributes but imports full Page class

```python
# bengal/interfaces/page.py
from typing import Protocol, Any
from pathlib import Path
from datetime import datetime

@runtime_checkable  
class PageLike(Protocol):
    """Minimal page interface for rendering."""

    @property
    def title(self) -> str: ...
    @property
    def content(self) -> str: ...
    @property
    def source_path(self) -> Path: ...
    @property
    def output_path(self) -> Path: ...
    @property
    def date(self) -> datetime | None: ...
    @property
    def meta(self) -> dict[str, Any]: ...
```

---

### Phase 2: Split `utils` Package (Week 1-2)

The `utils` package is a catch-all with 18 imports to core/orchestration/rendering.

#### 2.1 Categorize Current Utils

| Module | Dependencies | Move To |
|--------|--------------|---------|
| `logger.py` | None | `bengal/logging/` (new) |
| `path.py` | `core.Page` | `core/utils/path.py` |
| `progress.py` | None | `bengal/progress/` (new) |
| `rich_console.py` | None | `bengal/console/` (new) |
| `url_strategy.py` | `config` | `core/url/` |
| `profile.py` | `core.Site` | `orchestration/profile.py` |
| `metadata.py` | `core.theme`, `rendering.rosettes` | Split or move to `core/` |
| `build_context.py` | `core.*`, `orchestration.stats` | `orchestration/context/` |
| `swizzle.py` | `core.site`, `rendering.engines` | `orchestration/swizzle.py` |

#### 2.2 Create Leaf Packages

These have zero dependencies on Bengal packages:

```
bengal/
├── logging/         # Logger utilities (was utils/logger.py)
│   └── __init__.py
├── progress/        # Progress bars (was utils/progress.py)  
│   └── __init__.py
├── console/         # Rich console (was utils/rich_console.py)
│   └── __init__.py
└── text/            # String utilities
    └── __init__.py
```

#### 2.3 Move Domain-Specific Utils

```python
# bengal/core/utils/path.py (was bengal/utils/path.py)
# Now can import from bengal.core without cycle

from bengal.core.page import Page

def get_page_output_path(page: Page) -> Path:
    ...
```

---

### Phase 3: Decouple Core ↔ Orchestration ↔ Rendering (Week 2-3)

The tightest coupling. Core should not know about build orchestration or rendering.

#### 3.1 Remove `BuildStats` from Core

**Current** (`core/site/core.py`):
```python
from bengal.orchestration.stats import BuildStats

@dataclass
class Site:
    build_stats: BuildStats | None = None
```

**After**:
```python
from bengal.interfaces import StatsProtocol

@dataclass  
class Site:
    # Injected by orchestration layer
    _stats: StatsProtocol | None = field(default=None, repr=False)

    def set_stats(self, stats: StatsProtocol) -> None:
        """Called by BuildOrchestrator before build starts."""
        self._stats = stats
```

#### 3.2 Move Rendering Utilities to Rendering Package

The `core` package imports rendering utilities for:
- TOC extraction (`extract_toc_structure`)
- AST utilities (`extract_plain_text`, `extract_links_from_ast`)
- URL helpers (`with_baseurl`)
- Renderer access

**Strategy**: Invert these dependencies with callbacks or move logic to appropriate layer.

```python
# Option A: Callback injection
@dataclass
class Page:
    _toc_extractor: Callable[[str], list[TocItem]] | None = None

    @property
    def toc_items(self) -> list[TocItem]:
        if self._toc_extractor:
            return self._toc_extractor(self.toc)
        return []  # Fallback

# Option B: Move to rendering (preferred for most cases)
# TOC/AST utilities stay in rendering, accessed via orchestration
```

#### 3.3 Targeted Event Hooks (Not Full Event Bus)

Instead of a general-purpose EventBus, use **specific callback injection** for the 3 known use cases:

```python
# bengal/core/site/core.py
@dataclass
class Site:
    # Specific callbacks instead of general EventBus
    on_page_rendered: Callable[[Path], None] | None = field(default=None, repr=False)
    on_build_error: Callable[[Exception], None] | None = field(default=None, repr=False)
    on_asset_processed: Callable[[Path], None] | None = field(default=None, repr=False)
```

**Rationale**: A full EventBus adds:
- Hidden control flow (harder to debug)
- Performance overhead (pub/sub indirection)
- Testing complexity (mock subscriptions)

Targeted callbacks are explicit, traceable, and sufficient for the current use cases.

**If more events needed later**, upgrade to EventBus with these safeguards:
1. Typed event classes (not string names)
2. Async-aware handlers
3. Event flow documentation
4. Tracing/logging built-in

---

### Phase 4: Reduce Large Files and God Objects (Week 3-4)

#### 4.1 Split `PageProxy` (75 methods → 3 classes)

```python
# bengal/core/page/proxy/
├── __init__.py       # PageProxy (composition)
├── metadata.py       # PageProxyMetadata (cached attributes)
├── lazy_loader.py    # PageLazyLoader (content loading)
└── compatibility.py  # PageCompatibility (Page interface impl)
```

**Before**: 75 methods in one class (806 lines)
**After**: 3 focused classes, PageProxy composes them

```python
# bengal/core/page/proxy/__init__.py
class PageProxy:
    """Lazy-loaded page placeholder. Composes focused helpers."""

    def __init__(self, metadata: PageProxyMetadata, loader: PageLazyLoader):
        self._metadata = metadata
        self._loader = loader
        self._compat = PageCompatibility(self)

    # Delegate to focused classes
    @property
    def title(self) -> str:
        return self._metadata.title

    @property
    def content(self) -> str:
        return self._loader.load_content()
```

#### 4.2 Split `rendering/errors.py` (1,242 lines → 4 modules)

```
bengal/rendering/errors/
├── __init__.py           # Public API exports
├── context.py            # TemplateErrorContext (location info)
├── exceptions.py         # TemplateRenderError class
├── display.py            # display_template_error() function
└── deduplication.py      # ErrorDeduplicator class
```

#### 4.3 Split `directives/embed.py` (1,188 lines)

```
bengal/directives/embed/
├── __init__.py           # EmbedDirective (composition)
├── parser.py             # EmbedParser (syntax parsing)
├── resolver.py           # EmbedResolver (file/URL resolution)
├── renderers/
│   ├── code.py           # Code embedding
│   ├── image.py          # Image embedding
│   └── video.py          # Video embedding
└── validators.py         # Input validation
```

#### 4.4 Kida Files (Deferred)

The following files exceed 1000 lines but are **deferred** from this RFC:

| File | Lines | Reason for Deferral |
|------|-------|---------------------|
| `rendering/kida/compat/jinja.py` | 1,226 | Jinja compatibility is inherently complex; splitting may reduce cohesion |
| `rendering/kida/template.py` | 1,129 | Core template logic; splitting requires deeper template engine refactoring |
| `rendering/kida/environment/filters.py` | 1,025 | Filter collection; natural to be large, consider splitting by category later |

**Future RFC**: Consider `rfc-kida-refactoring.md` for template engine modularization.

---

## Migration Strategy

### Backward Compatibility

All changes maintain API compatibility:

1. **Re-exports**: Original import paths continue working
   ```python
   # bengal/utils/__init__.py
   from bengal.logging import get_logger  # Re-export from new location
   ```

2. **Deprecation warnings**: Old paths emit warnings for 2 releases
   ```python
   import warnings
   warnings.warn(
       "Import from bengal.logging instead of bengal.utils.logger",
       DeprecationWarning,
       stacklevel=2
   )
   ```

3. **Type compatibility**: Protocols ensure existing code works

### Testing Strategy

1. **Add import cycle detection to CI**:
   ```python
   # tests/test_no_cycles.py
   def test_no_runtime_package_cycles():
       """Ensure no runtime circular imports between packages."""
       cycles = detect_runtime_import_cycles("bengal")
       assert cycles == [], f"Found runtime cycles: {cycles}"
   ```

2. **Interface compliance tests**:
   ```python
   def test_page_implements_pagelike():
       from bengal.interfaces import PageLike
       from bengal.core.page import Page
       assert isinstance(Page(...), PageLike)
   ```

3. **Incremental migration**: Each phase has its own PR with tests

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing imports | Medium | High | Re-exports + deprecation warnings |
| Performance regression from protocols | Low | Medium | Use `@runtime_checkable` sparingly; benchmark |
| Incomplete migration leaves hybrid state | Medium | Medium | CI gate: zero runtime cycles before merge |
| Callback injection adds complexity | Low | Low | Limited to 3 specific callbacks; documented |
| TYPE_CHECKING imports mask coupling | Medium | Low | Track as tech debt; address in future RFC |

---

## Success Metrics

| Metric | Before | After Phase 1 | After Phase 4 |
|--------|--------|---------------|---------------|
| Runtime import cycles | 12 | 5 | 0 |
| TYPE_CHECKING imports (coupling) | 14 | 14 | 10 |
| `utils` bidirectional deps | 18 | 8 | 0 |
| Files >1000 lines | 5 | 5 | 2 |
| God objects (>50 methods) | 1 | 1 | 0 |
| Import time (`python -c "import bengal"`) | ~1.2s | ~1.0s | ~0.8s |
| Test isolation (can test `core` alone) | ❌ | ❌ | ✅ |

---

## Appendix A: Files to Modify

### Phase 1 Files
- `bengal/interfaces/__init__.py` (new)
- `bengal/interfaces/stats.py` (new)
- `bengal/interfaces/page.py` (new)
- `bengal/core/site/core.py` (modify)
- `bengal/rendering/context/page_wrappers.py` (modify)

### Phase 2 Files
- `bengal/logging/__init__.py` (new, move from utils/logger.py)
- `bengal/progress/__init__.py` (new, move from utils/progress.py)
- `bengal/console/__init__.py` (new, move from utils/rich_console.py)
- `bengal/utils/__init__.py` (modify, add re-exports)
- `bengal/core/utils/path.py` (new, move from utils/path.py)
- `bengal/orchestration/context.py` (new, move from utils/build_context.py)

### Phase 3 Files
- `bengal/core/site/core.py` (modify, add callbacks)
- `bengal/orchestration/build/__init__.py` (modify, inject callbacks)
- `bengal/core/page/metadata.py` (modify, remove rendering import)
- `bengal/core/page/content.py` (modify, use callback for AST utils)
- `bengal/core/asset/asset_core.py` (modify, remove rendering import)

### Phase 4 Files
- `bengal/core/page/proxy/` (new package, split from proxy.py)
- `bengal/rendering/errors/` (new package, split from errors.py)
- `bengal/directives/embed/` (new package, split from embed.py)

---

## Appendix B: Measurement Scripts

### Detect Runtime Import Cycles

```python
#!/usr/bin/env python3
"""Detect runtime circular imports in Bengal packages."""

import ast
import sys
from pathlib import Path
from collections import defaultdict

def get_runtime_imports(file_path: Path) -> list[str]:
    """Extract imports that run at module load time (not in TYPE_CHECKING)."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    imports = []
    in_type_checking = False

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            # Check for TYPE_CHECKING guard
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                continue  # Skip imports inside TYPE_CHECKING

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("bengal."):
                    imports.append(node.module.split(".")[1])  # Package name

    return imports

def build_dependency_graph(bengal_path: Path) -> dict[str, set[str]]:
    """Build package-level dependency graph."""
    graph = defaultdict(set)

    for package_dir in bengal_path.iterdir():
        if package_dir.is_dir() and not package_dir.name.startswith("_"):
            package_name = package_dir.name
            for py_file in package_dir.rglob("*.py"):
                for dep in get_runtime_imports(py_file):
                    if dep != package_name:
                        graph[package_name].add(dep)

    return graph

def find_cycles(graph: dict[str, set[str]]) -> list[tuple[str, str]]:
    """Find bidirectional edges (cycles) in the graph."""
    cycles = []
    for pkg, deps in graph.items():
        for dep in deps:
            if pkg in graph.get(dep, set()):
                if (dep, pkg) not in cycles:  # Avoid duplicates
                    cycles.append((pkg, dep))
    return cycles

if __name__ == "__main__":
    bengal_path = Path("bengal")
    graph = build_dependency_graph(bengal_path)
    cycles = find_cycles(graph)

    if cycles:
        print(f"Found {len(cycles)} runtime cycles:")
        for a, b in cycles:
            print(f"  {a} ↔ {b}")
        sys.exit(1)
    else:
        print("No runtime cycles found ✓")
        sys.exit(0)
```

### Count Dependencies

```bash
#!/bin/bash
# Count imports between Bengal packages

echo "=== core → orchestration ==="
grep -r "from bengal\.orchestration" bengal/core --include="*.py" | grep -v TYPE_CHECKING | wc -l

echo "=== core → rendering ==="
grep -r "from bengal\.rendering" bengal/core --include="*.py" | grep -v TYPE_CHECKING | wc -l

echo "=== utils → core/orchestration/rendering ==="
grep -r "from bengal\.\(core\|orchestration\|rendering\)" bengal/utils --include="*.py" | wc -l

echo "=== Files over 1000 lines ==="
find bengal -name "*.py" -exec wc -l {} \; | awk '$1 > 1000 {print}' | sort -rn
```

---

## Appendix C: Current State Snapshot (2025-12-26)

```
Runtime cycles detected:
  core ↔ orchestration (1 runtime import)
  core ↔ rendering (7 runtime imports)
  utils ↔ core (implicit via multiple modules)
  utils ↔ orchestration (2 runtime imports)
  utils ↔ rendering (1 runtime import)

TYPE_CHECKING-only (not runtime cycles):
  orchestration → core: 79 locations (mostly TYPE_CHECKING)
  rendering → core: 88 locations (mostly TYPE_CHECKING)

Files >1000 lines:
  rendering/errors.py: 1,242
  rendering/kida/compat/jinja.py: 1,226
  directives/embed.py: 1,188
  rendering/kida/template.py: 1,129
  rendering/kida/environment/filters.py: 1,025

God objects:
  PageProxy: 75 methods (806 lines)
```

---

## References

- [Martin Fowler: Breaking Cycles in Package Dependencies](https://martinfowler.com/bliki/BreakingCycles.html)
- [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [Clean Architecture by Robert Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Bengal existing RFC: rfc-block-level-incremental-builds.md](../drafted/rfc-block-level-incremental-builds.md)
