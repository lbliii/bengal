# RFC: Module Coupling Reduction & Dependency Architecture

**Status**: Draft  
**Created**: 2026-01-14  
**Updated**: 2026-01-14  
**Priority**: Medium  
**Tracking**: `plan/rfc-module-coupling-reduction.md`

---

## Executive Summary

A dependency analysis of Bengal's 715 Python files identified high coupling in hub modules (`utils`, `errors`, `orchestration`, `core`) and 12 circular import patterns. This RFC proposes targeted refactoring to reduce coupling, eliminate circular dependencies, and improve encapsulation—without changing public APIs.

**Key Changes**:
- Split `utils/` into domain-aligned sub-packages
- Extract shared types to reduce `orchestration/` fan-out
- Resolve 12 circular import patterns
- Establish dependency direction rules

**Relationship to Other RFCs**:
- `rfc-code-health-improvements.md`: Focuses on file-level complexity (LOC, function count)
- **This RFC**: Focuses on module-level coupling and dependency architecture

**Dependencies**:
- Phase 3.2 (renderer cycles) requires `rfc-code-health-improvements.md` Phase 3 to be complete
- Phase 3.3 (errors cycle) is addressed by `rfc-code-health-improvements.md`

---

## Analysis Methodology

The coupling metrics in this RFC were generated using the following reproducible process:

```bash
# Generate coupling analysis report
uv run python scripts/analyze_imports.py --output=reports/coupling-analysis.json

# Detect circular import patterns
uv run python scripts/check_cycles.py --format=detailed

# Count package dependencies
uv run python -c "
from pathlib import Path
import ast
from collections import defaultdict

def analyze_imports(package_dir):
    deps = defaultdict(set)
    for py_file in Path(package_dir).rglob('*.py'):
        # ... import extraction logic
    return deps
"
```

**Analysis Date**: 2026-01-14  
**Files Analyzed**: 715 Python files in `bengal/`  
**Tool**: Custom import analysis script (to be added as `scripts/analyze_imports.py` in Phase 4)

---

## Problem Statement

### Coupling Analysis Results

| Module | Outgoing Deps | Incoming Deps | Concern |
|--------|---------------|---------------|---------|
| `utils` | 11 packages | **23 packages** | God utility module—knows too much, everyone depends on it |
| `errors` | 4 packages | **20 packages** | Error types scattered, imports rendering for display |
| `core` | 14 packages | **17 packages** | Core domain leaks upward into orchestration |
| `orchestration` | **19 packages** | 10 packages | Orchestration imports nearly everything |

### Circular Import Patterns (12 Detected)

```
# Within analysis/
bengal.analysis.knowledge_graph ↔ page_rank, path_analysis, community_detection, 
                                  link_suggestions, graph_analysis, graph_reporting

# Within rendering/
bengal.rendering.parsers.patitas.renderers.html ↔ blocks, directives

# Within errors/
bengal.errors.context ↔ bengal.errors.exceptions

# Within utils/
bengal.utils.logger ↔ bengal.utils.rich_console

# Within server/
bengal.server.live_reload ↔ bengal.server.request_handler

# Within core/
bengal.core.resources.processor ↔ bengal.core.resources.image
```

### Impact

| Issue | Symptom | Cost |
|-------|---------|------|
| High coupling | Changes ripple across unrelated modules | Slower development, more test failures |
| Circular imports | Complex import ordering, `TYPE_CHECKING` workarounds | Fragile initialization, IDE confusion |
| God modules | `utils` touched by 280 files | Merge conflicts, unclear ownership |
| Upward dependencies | `core` imports `orchestration`, `rendering` | Prevents clean layering |

---

## Proposed Architecture

### Target Dependency Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI Layer                               │
│  cli/, server/, debug/, services/                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestration Layer                          │
│  orchestration/, health/, analysis/, postprocess/                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Feature Layer                              │
│  rendering/, cache/, autodoc/, directives/, content_layer/       │
│  themes/, assets/, fonts/, icons/                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Core Layer                                │
│  core/, config/, discovery/, collections/, content_types/        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Foundation Layer                             │
│  protocols/, errors/, output/, utils/                            │
└─────────────────────────────────────────────────────────────────┘
```

**Rule**: Dependencies flow **downward only**. No layer may import from a higher layer.

### Complete Package-to-Layer Mapping

| Layer | Packages |
|-------|----------|
| **CLI** | `cli`, `server`, `debug`, `services` |
| **Orchestration** | `orchestration`, `health`, `analysis`, `postprocess` |
| **Feature** | `rendering`, `cache`, `autodoc`, `directives`, `content_layer`, `themes`, `assets`, `fonts`, `icons` |
| **Core** | `core`, `config`, `discovery`, `collections`, `content_types` |
| **Foundation** | `protocols`, `errors`, `output`, `utils` |

---

## Proposed Improvements

### 1. Split `utils/` into Domain-Aligned Sub-Packages

**Current State**: 42 Python files, 23 packages depend on it, imports 11 packages (including upward deps like `core`, `orchestration`, `cli`, `server`).

**Problem**: `utils` is a "junk drawer"—it contains unrelated utilities that create inappropriate coupling.

**Proposed Structure**:

```
utils/                          # Foundation utilities (no upward deps)
├── __init__.py                 # Minimal re-exports for compatibility
├── primitives/                 # Pure functions, no Bengal imports
│   ├── __init__.py
│   ├── hashing.py              # hash_str, hash_bytes, hash_dict
│   ├── text.py                 # slugify, truncate, strip_html
│   ├── dates.py                # date parsing, time_ago
│   ├── sentinel.py             # MISSING singleton
│   └── dotdict.py              # DotDict class
├── io/                         # File I/O utilities
│   ├── __init__.py
│   ├── file_io.py              # read_text_file, load_yaml
│   ├── atomic_write.py         # crash-safe writes
│   ├── file_lock.py            # cross-platform locking
│   └── json_compat.py          # JSON serialization
├── paths/                      # Path management
│   ├── __init__.py
│   ├── paths.py                # BengalPaths
│   ├── path_resolver.py        # PathResolver
│   ├── url_normalization.py    # URL validation
│   └── url_strategy.py         # URL computation
├── concurrency/                # Thread/async utilities
│   ├── __init__.py
│   ├── concurrent_locks.py     # PerKeyLockManager
│   ├── thread_local.py         # ThreadLocalCache
│   ├── async_compat.py         # uvloop integration
│   ├── retry.py                # backoff utilities
│   ├── gil.py                  # GIL utilities
│   └── workers.py              # worker pool management
├── observability/              # Logging, metrics, progress
│   ├── __init__.py
│   ├── logger.py               # structured logging
│   ├── rich_console.py         # console output
│   ├── progress.py             # ProgressReporter
│   ├── observability.py        # stats collection
│   ├── performance_collector.py # perf metrics
│   ├── performance_report.py   # perf reporting
│   └── profile.py              # build profiles
└── domain/                     # Bengal-specific utilities (moved later)
    ├── __init__.py
    ├── build_context.py        # → move to orchestration/
    ├── swizzle.py              # → move to themes/
    ├── version_diff.py         # → move to discovery/
    ├── metadata.py             # → move to rendering/
    ├── css_minifier.py         # → move to assets/
    └── js_bundler.py           # → move to assets/
```

**Target Module Verification** (all targets exist):

| Utility | Target | Target Exists |
|---------|--------|---------------|
| `build_context.py` | `orchestration/` | ✅ Yes |
| `swizzle.py` | `themes/` | ✅ Yes (has `config.py`, `tokens.py`) |
| `version_diff.py` | `discovery/` | ✅ Yes |
| `metadata.py` | `rendering/` | ✅ Yes |
| `css_minifier.py` | `assets/` | ✅ Yes (has `pipeline.py`, `manifest.py`) |
| `js_bundler.py` | `assets/` | ✅ Yes |

**Migration Strategy**:

```python
# Phase 1: Create sub-packages with re-exports
# utils/__init__.py maintains backward compatibility
from bengal.utils.primitives import hash_str, hash_bytes  # works
from bengal.utils.io import read_text_file                 # works
from bengal.utils import hash_str                          # still works (re-export)

# Phase 2: Deprecation warnings (optional)
# Phase 3: Move domain utilities to proper homes
```

**Benefits**:
- `primitives/` has zero Bengal imports → can be tested in isolation
- `io/` and `concurrency/` have minimal deps → clear contracts
- Domain utilities move to their logical owners → clearer ownership

---

### 2. Extract Shared Types to Foundation Layer

**Current State**: 
- `orchestration/` imports 19 packages—more than any other module
- `orchestration/types.py` contains 15 TypedDicts/Protocols used across modules
- `BuildPhase` enum already exists in `errors/context.py:96` (9 phases)

**Problem**: Shared types are scattered across `orchestration/types.py` and `errors/context.py`, forcing modules to import from higher layers.

**Proposed Change**: Consolidate shared types in `protocols/build.py`.

```python
# BEFORE: BuildPhase in errors (wrong layer), TypedDicts in orchestration
from bengal.errors.context import BuildPhase      # errors layer
from bengal.orchestration.types import RenderResult  # orchestration layer

# AFTER: Foundation layer types
from bengal.protocols.build import BuildPhase, RenderResult
```

**New File**: `bengal/protocols/build.py`

```python
"""Build-related protocols and types.

Consolidated shared types for build operations, enabling proper
dependency direction (Foundation → up) instead of scattered definitions.

Migrated from:
- bengal/errors/context.py: BuildPhase enum (9 phases)
- bengal/orchestration/types.py: TypedDicts for stats, results, context
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Protocol, TypedDict, runtime_checkable


class BuildPhase(Enum):
    """
    Build phase where an error occurred.
    
    Migrated from: bengal/errors/context.py:96
    Phases follow the Bengal build pipeline order.
    """
    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    PARSING = "parsing"
    RENDERING = "rendering"
    POSTPROCESSING = "postprocessing"
    ASSET_PROCESSING = "asset_processing"
    CACHE = "cache"
    SERVER = "server"
    OUTPUT = "output"


class RenderResult(TypedDict, total=False):
    """Result of rendering a single page."""
    page_path: str
    output_path: str
    success: bool
    duration_ms: float
    from_cache: bool
    error: str | None


class PhaseStats(TypedDict, total=False):
    """Statistics for a single build phase."""
    name: str
    duration_ms: float
    items_processed: int
    errors: int
    warnings: int


@runtime_checkable
class BuildStateProtocol(Protocol):
    """Protocol for build state access."""
    @property
    def phase(self) -> BuildPhase: ...
    @property
    def is_incremental(self) -> bool: ...
```

**Types to Migrate**:

| Type | Current Location | Action |
|------|------------------|--------|
| `BuildPhase` | `errors/context.py:96` | Move to `protocols/build.py` |
| `PhaseStats` | `orchestration/types.py` | Move to `protocols/build.py` |
| `PhaseTiming` | `orchestration/types.py` | Move to `protocols/build.py` |
| `RenderResult` | `orchestration/types.py` | Move to `protocols/build.py` |
| `RenderContext` | `orchestration/types.py` | Move to `protocols/build.py` |
| `BuildContextDict` | `orchestration/types.py` | Move to `protocols/build.py` |
| `BuildOptionsDict` | `orchestration/types.py` | Move to `protocols/build.py` |
| `CacheStats` | `orchestration/types.py` | Stay (cache-specific) |
| `AssetResult` | `orchestration/types.py` | Stay (asset-specific) |

**Migration**:

1. Create `bengal/protocols/build.py` with consolidated types
2. Update `errors/context.py` to import `BuildPhase` from protocols
3. Update `orchestration/types.py` to re-export from protocols
4. Update ~35 importers to use protocols
5. Reduce `orchestration/` outgoing deps from 19 → ~15

---

### 3. Resolve Circular Import Patterns

**Strategy**: For each cycle, apply one of:
- **Extract interface**: Move shared types to protocols
- **Dependency inversion**: Use protocols instead of concrete types
- **Merge modules**: If tightly coupled, combine them

#### 3.1 Analysis Module Cycles (6 cycles)

**Root Cause**: `knowledge_graph.py` is both a data model and orchestrator.

**Fix**: Extract `KnowledgeGraph` data class to separate module.

```
analysis/
├── models.py           # NEW: KnowledgeGraph dataclass, graph types
├── knowledge_graph.py  # Orchestration: build graph, run analysis
├── graph_analysis.py   # Imports models.KnowledgeGraph
├── page_rank.py        # Imports models.KnowledgeGraph
└── ...
```

#### 3.2 Renderer Cycles (html ↔ blocks, directives)

**Root Cause**: `html.py` dispatches to `blocks.py`, which calls back to `html.py` for nested rendering.

**Fix**: Already addressed in `rfc-code-health-improvements.md` Phase 3—composition pattern with explicit callbacks.

> ⚠️ **Dependency**: This cycle resolution requires `rfc-code-health-improvements.md` Phase 3 to be complete first. Do not attempt this fix independently.

```python
# blocks.py receives render function, doesn't import html.py
class BlockRenderer:
    def render(self, node: Node, sb: StringBuilder, 
               render_children: Callable[[Node, StringBuilder], None]) -> None:
        ...
```

#### 3.3 Errors Cycle (context ↔ exceptions)

**Root Cause**: `TemplateRenderError` needs `TemplateErrorContext`, and context needs exception types.

**Fix**: Merge into single module (already done in `rfc-code-health-improvements.md`).

```
rendering/errors/
├── __init__.py
├── types.py       # TemplateErrorContext, InclusionChain (data only)
├── exceptions.py  # TemplateRenderError imports types
└── display.py     # Formatting, imports both
```

#### 3.4 Utils Logger Cycle (logger ↔ rich_console)

**Current**:
```python
# logger.py imports rich_console for console output
# rich_console.py imports logger for logging configuration
```

**Fix**: Extract shared config to avoid cycle.

```python
# utils/observability/config.py (new)
LOG_LEVEL = ...
CONSOLE_WIDTH = ...

# logger.py imports config
# rich_console.py imports config
# No cycle
```

#### 3.5 Server Cycle (live_reload ↔ request_handler)

**Fix**: Use protocol for handler interface.

```python
# protocols/infrastructure.py (add)
class RequestHandlerProtocol(Protocol):
    def handle_request(self, path: str) -> Response: ...

# live_reload.py uses protocol, not concrete handler
```

#### 3.6 Core Resources Cycle (processor ↔ image)

**Fix**: Merge or use protocol—these are tightly coupled by design.

---

### 4. Establish Dependency Direction Linting

**New CI Check**: Enforce layer boundaries.

```python
# scripts/check_dependencies.py
LAYER_ORDER = [
    "protocols", "errors", "output", "utils",  # Foundation
    "core", "config", "discovery", "collections", "content_types",  # Core
    "rendering", "cache", "autodoc", "directives", "content_layer",  # Feature
    "orchestration", "health", "analysis", "postprocess",  # Orchestration
    "cli", "server", "debug", "services",  # CLI
]

def check_import(importer: str, imported: str) -> bool:
    """Return True if import direction is valid (down or same layer)."""
    importer_layer = get_layer(importer)
    imported_layer = get_layer(imported)
    return LAYER_ORDER.index(importer_layer) >= LAYER_ORDER.index(imported_layer)
```

**CI Integration**:
```yaml
# .github/workflows/lint.yml
- name: Check dependency directions
  run: uv run python scripts/check_dependencies.py
```

---

## Implementation Plan

### Phase 1: Foundation Cleanup (Low Risk)

| Task | Effort | Risk | Files Affected |
|------|--------|------|----------------|
| Split `utils/` into sub-packages | 4 hours | Low | 42 utils files |
| Add `__init__.py` re-exports | 1 hour | Low | Backward compatible |
| Move domain utils to proper homes | 2 hours | Low | ~15 files |

**Gate**: All existing imports still work via re-exports.

### Phase 2: Protocol Extraction (Low Risk)

| Task | Effort | Risk | Files Affected |
|------|--------|------|----------------|
| Create `protocols/build.py` | 1 hour | Low | New file |
| Move `BuildPhase` from `errors/context.py` | 30 min | Low | 1 file + re-export |
| Update `orchestration/types.py` | 30 min | Low | Re-export |
| Update importers | 3 hours | Low | ~35 files |

**Gate**: `uv run pytest tests/ -v` passes.

### Phase 3: Cycle Resolution (Medium Risk)

| Cycle | Fix | Effort | Risk | Dependency |
|-------|-----|--------|------|------------|
| analysis/* | Extract `models.py` | 2 hours | Low | None |
| rendering/* | Composition pattern | - | - | ⚠️ Requires `rfc-code-health` Phase 3 |
| errors/* | Merge modules | - | - | ⚠️ Addressed by `rfc-code-health` |
| utils/logger | Extract config | 1 hour | Low | None |
| server/* | Use protocol | 1 hour | Medium | None |
| core/resources | Merge or protocol | 1 hour | Low | None |

**Gate**: `python scripts/check_cycles.py` returns 0 cycles.

### Phase 4: Dependency Linting (Low Risk)

| Task | Effort | Risk |
|------|--------|------|
| Create `check_dependencies.py` | 2 hours | Low |
| Add to CI | 30 min | Low |
| Document layer rules | 1 hour | Low |

**Gate**: CI passes on main branch.

---

## Success Metrics

### Coupling Reduction

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| `utils` incoming deps | 23 packages | < 15 packages | Import analysis |
| `orchestration` outgoing deps | 19 packages | < 15 packages | Import analysis |
| Circular import patterns | 12 | 0 | `check_cycles.py` |

### Layer Violations

| Metric | Before | Target |
|--------|--------|--------|
| Upward layer imports | ~50 | 0 |
| Foundation → Feature imports | ~30 | 0 |

### Code Organization

| Metric | Before | Target |
|--------|--------|--------|
| `utils/` file count | 42 in flat dir | Organized sub-packages |
| Shared types in orchestration | 15 TypedDicts | 7 moved to protocols |
| `BuildPhase` location | `errors/context.py` | `protocols/build.py` |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import path breakage | Low | Medium | Re-exports in `__init__.py` |
| IDE autocomplete issues | Low | Low | Explicit re-exports |
| CI slowdown from dep check | Low | Low | Cache import analysis |
| Merge conflicts during migration | Medium | Low | Phase incrementally |

### Rollback Plan

Each phase is independently revertible:

```bash
# If Phase 1 breaks imports
git revert <phase-1-commits>

# Phases are additive—earlier phases don't depend on later ones
```

---

## Testing Strategy

### Phase 1 Validation

```bash
# Verify all imports still work
uv run python -c "from bengal.utils import hash_str, BengalPaths, read_text_file"

# Full test suite
uv run pytest tests/ -v
```

### Cycle Detection

```bash
# Run cycle checker (create in Phase 4)
uv run python scripts/check_cycles.py

# Expected output after Phase 3:
# "No circular import patterns detected"
```

### Layer Validation

```bash
# Run layer checker (create in Phase 4)
uv run python scripts/check_dependencies.py

# Expected output after Phase 4:
# "All imports follow layer rules"
```

---

## Dependencies

### Pre-Existing Infrastructure

| Component | Status | Used For |
|-----------|--------|----------|
| `TYPE_CHECKING` pattern | ✅ Already used | Cycle breaking |
| `protocols/` package | ✅ Exists | Type extraction target |
| CI workflow | ✅ Exists | Add dep check |

### New Scripts Needed

| Script | Purpose | Create In |
|--------|---------|-----------|
| `scripts/analyze_imports.py` | Generate coupling analysis reports | Phase 4 |
| `scripts/check_cycles.py` | Detect circular imports | Phase 3 |
| `scripts/check_dependencies.py` | Enforce layer rules | Phase 4 |

---

## Out of Scope

- File-level complexity (covered in `rfc-code-health-improvements.md`)
- Public API changes
- New features
- Performance optimization

---

## Execution Checklists

### Phase 1 Checklist
- [ ] Create `utils/primitives/` with pure functions
- [ ] Create `utils/io/` with file operations
- [ ] Create `utils/paths/` with path utilities
- [ ] Create `utils/concurrency/` with thread/async utils
- [ ] Create `utils/observability/` with logging/metrics
- [ ] Update `utils/__init__.py` with re-exports
- [ ] Verify: `from bengal.utils import hash_str` still works
- [ ] Run: `uv run pytest tests/ -v`
- [ ] Move `build_context.py` → `orchestration/`
- [ ] Move `swizzle.py` → `themes/`
- [ ] Move `css_minifier.py`, `js_bundler.py` → `assets/`
- [ ] Commit: `refactor(utils): split into domain-aligned sub-packages`

### Phase 2 Checklist
- [ ] Create `protocols/build.py` with consolidated types
- [ ] Move `BuildPhase` from `errors/context.py` to `protocols/build.py`
- [ ] Update `errors/context.py` to import `BuildPhase` from protocols
- [ ] Update `orchestration/types.py` to re-export from protocols
- [ ] Update ~35 importers to use `protocols.build`
- [ ] Run: `uv run pytest tests/ -v`
- [ ] Commit: `refactor(protocols): consolidate shared build types`

### Phase 3 Checklist
- [ ] Create `analysis/models.py` with KnowledgeGraph dataclass
- [ ] Update analysis modules to import from models
- [ ] Create `utils/observability/config.py` for logger/console
- [ ] Add `RequestHandlerProtocol` to protocols
- [ ] Verify: 0 cycles in `check_cycles.py`
- [ ] Commit: `refactor: resolve circular import patterns`

### Phase 4 Checklist
- [ ] Create `scripts/analyze_imports.py` for coupling analysis
- [ ] Create `scripts/check_dependencies.py` for layer enforcement
- [ ] Create `scripts/check_cycles.py` for cycle detection
- [ ] Add all checks to `.github/workflows/lint.yml`
- [ ] Document layer rules in `CONTRIBUTING.md`
- [ ] Commit: `ci: add dependency direction linting`

---

## Appendix: Full Coupling Analysis

<details>
<summary>Outgoing Dependencies by Module</summary>

```
orchestration: imports 19 packages → ['analysis', 'assets', 'autodoc', 'cache', 'cli', 
    'collections', 'config', 'content_types', 'core', 'discovery', 'errors', 'fonts', 
    'health', 'output', 'postprocess', 'protocols', 'rendering', 'themes', 'utils']
cli: imports 18 packages → ['analysis', 'assets', 'cache', 'collections', 'config', 
    'content_layer', 'core', 'debug', 'discovery', 'errors', 'health', 'orchestration', 
    'output', 'rendering', 'server', 'services', 'themes', 'utils']
core: imports 14 packages → ['assets', 'cache', 'collections', 'config', 'discovery', 
    'errors', 'health', 'icons', 'orchestration', 'protocols', 'rendering', 'server', 
    'themes', 'utils']
rendering: imports 13 packages → ['assets', 'autodoc', 'cache', 'config', 'content_types', 
    'core', 'directives', 'errors', 'icons', 'orchestration', 'postprocess', 'protocols', 'utils']
utils: imports 11 packages → ['analysis', 'cache', 'cli', 'config', 'core', 'errors', 
    'orchestration', 'output', 'protocols', 'rendering', 'server']
```

</details>

<details>
<summary>Incoming Dependencies by Module</summary>

```
utils: used by 23 packages ← ['analysis', 'assets', 'autodoc', 'cache', 'cli', 
    'collections', 'config', 'content_layer', 'content_types', 'core', 'debug', 
    'directives', 'discovery', 'errors', 'fonts', 'health', 'icons', 'orchestration', 
    'output', 'postprocess', 'protocols', 'rendering', 'server', 'themes']
errors: used by 20 packages ← ['analysis', 'assets', 'autodoc', 'cache', 'cli', 
    'collections', 'config', 'content_layer', 'core', 'debug', 'directives', 'discovery', 
    'fonts', 'health', 'orchestration', 'output', 'postprocess', 'rendering', 'server', 'themes']
core: used by 17 packages ← ['analysis', 'assets', 'autodoc', 'cache', 'cli', 
    'content_types', 'debug', 'directives', 'discovery', 'health', 'icons', 
    'orchestration', 'postprocess', 'protocols', 'rendering', 'server', 'utils']
rendering: used by 14 packages ← ['autodoc', 'cli', 'content_types', 'core', 'debug', 
    'directives', 'errors', 'health', 'orchestration', 'postprocess', 'protocols', 
    'server', 'services', 'utils']
```

</details>

<details>
<summary>Detected Circular Patterns (Detail)</summary>

```
bengal.analysis.page_rank ↔ bengal.analysis.knowledge_graph
bengal.analysis.path_analysis ↔ bengal.analysis.knowledge_graph
bengal.analysis.knowledge_graph ↔ bengal.analysis.community_detection
bengal.analysis.knowledge_graph ↔ bengal.analysis.link_suggestions
bengal.analysis.knowledge_graph ↔ bengal.analysis.graph_analysis
bengal.analysis.knowledge_graph ↔ bengal.analysis.graph_reporting
bengal.core.resources.processor ↔ bengal.core.resources.image
bengal.server.live_reload ↔ bengal.server.request_handler
bengal.utils.logger ↔ bengal.utils.rich_console
bengal.rendering.parsers.patitas.renderers.html ↔ bengal.rendering.parsers.patitas.renderers.directives
bengal.rendering.parsers.patitas.renderers.html ↔ bengal.rendering.parsers.patitas.renderers.blocks
bengal.errors.context ↔ bengal.errors.exceptions
```

</details>
