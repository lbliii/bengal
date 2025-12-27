# RFC: Dependency Decoupling — Breaking Bengal's Circular Dependencies

**Status**: Drafted  
**Created**: 2025-12-26  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P0 (Critical)  
**Related**: `bengal/core/`, `bengal/orchestration/`, `bengal/utils/`  
**Confidence**: 85% 🟢

---

## Executive Summary

Bengal has **26 circular dependencies** at the package level, with `core` ↔ `orchestration` ↔ `rendering` forming a tightly coupled triangle. This RFC proposes a phased decoupling strategy using dependency inversion, interface extraction, and package restructuring.

| Metric | Current | Target |
|--------|---------|--------|
| Package-level cycles | 26 | 0 |
| `utils` dependencies | 10+ bidirectional | 0 bidirectional |
| Files >1000 lines | 7 | 3 |
| God objects (>50 methods) | 3 | 0 |

**Estimated effort**: 3-4 weeks across 4 phases

---

## Problem Statement

### Circular Dependencies Create Real Problems

1. **Import order fragility** — Adding a new import can break unrelated modules
2. **Testing difficulty** — Cannot test `core` without `orchestration` loaded
3. **Mental model overload** — Understanding one package requires understanding all coupled packages
4. **Refactoring risk** — Changes ripple unpredictably across packages

### Current Dependency Graph

```
     ┌──────────────────────────────────────────────┐
     │                   utils                       │ ◄── 10+ bidirectional
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

### Specific Violations Found

| Cycle | Location | Cause |
|-------|----------|-------|
| `core` → `orchestration` | `core/site/core.py:63` | Imports `BuildStats` |
| `orchestration` → `core` | `orchestration/build/__init__.py` | Uses `Site`, `Page` |
| `core` → `rendering` | `core/page/proxy.py` | Template awareness |
| `rendering` → `core` | `rendering/context/` | Page/Site wrappers |
| `utils` → `core` | `utils/path.py` | Page path utilities |
| `core` → `utils` | Throughout | Logger, helpers |

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

**Problem**: `core/site/core.py` imports `BuildStats` from `orchestration`

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

The `utils` package is a catch-all with bidirectional dependencies to 10+ packages.

#### 2.1 Categorize Current Utils

| Module | Dependencies | Move To |
|--------|--------------|---------|
| `logger.py` | None | `bengal/logging/` (new) |
| `path.py` | `core.Page` | `core/utils/path.py` |
| `progress.py` | None | `bengal/progress/` (new) |
| `rich_console.py` | None | `bengal/console/` (new) |
| `url_strategy.py` | `config` | `core/url/` |
| `profile.py` | `core.Site` | `orchestration/profile.py` |

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

### Phase 3: Decouple Core ↔ Orchestration (Week 2-3)

The tightest coupling. Core should not know about build orchestration.

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

#### 3.2 Invert Render Context Creation

**Current**: `core/page/proxy.py` creates render contexts
**After**: `orchestration/` provides context factory

```python
# bengal/interfaces/context.py
class ContextFactoryProtocol(Protocol):
    def create_page_context(self, page: PageLike) -> dict[str, Any]: ...
    def create_site_context(self, site: SiteProtocol) -> dict[str, Any]: ...
```

#### 3.3 Event-Based Communication

Replace direct calls with events for loose coupling:

```python
# bengal/core/events.py
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class Event:
    name: str
    data: dict[str, Any]

class EventBus:
    """Decoupled communication between packages."""

    _handlers: dict[str, list[Callable]] = {}

    @classmethod
    def subscribe(cls, event_name: str, handler: Callable) -> None:
        cls._handlers.setdefault(event_name, []).append(handler)

    @classmethod  
    def emit(cls, event: Event) -> None:
        for handler in cls._handlers.get(event.name, []):
            handler(event)

# Usage in core (no import from orchestration)
EventBus.emit(Event("page.rendered", {"path": page.output_path}))

# Usage in orchestration (subscribes during init)
EventBus.subscribe("page.rendered", build_stats.record_page)
```

---

### Phase 4: Reduce God Objects (Week 3-4)

#### 4.1 Split `PageProxy` (74 methods → 3 classes)

```python
# bengal/core/page/proxy/
├── __init__.py       # PageProxy (composition)
├── metadata.py       # PageProxyMetadata (cached attributes)
├── lazy_loader.py    # PageLazyLoader (content loading)
└── compatibility.py  # PageCompatibility (Page interface impl)
```

**Before**: 74 methods in one class
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

#### 4.2 Split `rendering/errors.py` (1242 lines → 4 modules)

```
bengal/rendering/errors/
├── __init__.py           # Public API exports
├── context.py            # TemplateErrorContext (location info)
├── exceptions.py         # TemplateRenderError class
├── display.py            # display_template_error() function
└── deduplication.py      # ErrorDeduplicator class
```

#### 4.3 Split `directives/embed.py` (1188 lines)

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
   def test_no_package_cycles():
       cycles = detect_import_cycles("bengal")
       assert cycles == [], f"Found cycles: {cycles}"
   ```

2. **Interface compliance tests**:
   ```python
   def test_page_implements_pagelike():
       assert isinstance(Page(...), PageLike)
   ```

3. **Incremental migration**: Each phase has its own PR with tests

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing imports | Medium | High | Re-exports + deprecation warnings |
| Performance regression from protocols | Low | Medium | Use `@runtime_checkable` sparingly |
| Incomplete migration leaves hybrid state | Medium | Medium | CI gate: zero cycles before merge |
| Event bus adds indirection complexity | Medium | Low | Document event flow, add tracing |

---

## Success Metrics

| Metric | Before | After Phase 1 | After Phase 4 |
|--------|--------|---------------|---------------|
| Package-level cycles | 26 | 15 | 0 |
| `utils` bidirectional deps | 10 | 5 | 0 |
| Files >1000 lines | 7 | 7 | 3 |
| God objects (>50 methods) | 3 | 3 | 0 |
| Import time (`python -c "import bengal"`) | ~1.2s | ~1.0s | ~0.8s |
| Test isolation (can test `core` alone) | ❌ | ❌ | ✅ |

---

## Appendix: Files to Modify

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

### Phase 3 Files
- `bengal/core/events.py` (new)
- `bengal/interfaces/context.py` (new)
- `bengal/orchestration/build/__init__.py` (modify)
- `bengal/core/site/core.py` (modify)

### Phase 4 Files
- `bengal/core/page/proxy/` (new package, split from proxy.py)
- `bengal/rendering/errors/` (new package, split from errors.py)
- `bengal/directives/embed/` (new package, split from embed.py)

---

## References

- [Martin Fowler: Breaking Cycles in Package Dependencies](https://martinfowler.com/bliki/BreakingCycles.html)
- [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [Clean Architecture by Robert Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Bengal existing RFC: rfc-block-level-incremental-builds.md](../drafted/rfc-block-level-incremental-builds.md)
