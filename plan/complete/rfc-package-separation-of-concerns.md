# RFC: Package Separation of Concerns

**Status**: Implemented ✅  
**Created**: 2026-01-15  
**Evaluated**: 2026-01-15  
**Implemented**: 2026-01-15  
**Author**: gpt-5.2-codex  
**Confidence**: 89% 🟢  
**Category**: Orchestration / Rendering / Content / Health

---

## Executive Summary

Several packages combine distinct responsibilities under single namespaces. This RFC proposes direct refactoring to separate concerns into focused subpackages with clear ownership boundaries.

**Approach**: Clean restructuring - move files to correct locations and update all imports in a single atomic refactor. No shims, no deprecation paths, no transitional facades.

---

## Problem Statement

### Current State

Several top-level packages aggregate multiple responsibilities.

**Evidence**:
- `bengal/content/__init__.py:1-41` - Content combines discovery and remote sources
- `bengal/content/discovery/__init__.py:7-16` - Discovery includes versioning adapters
- `bengal/analysis/__init__.py:8-32` - Analysis combines graph, links, and performance modules
- `bengal/rendering/pipeline/core.py:66-107` - Rendering pipeline contains directive cache policy
- `bengal/health/__init__.py:4-41` - Health groups validators with remediation (autofix)
- `bengal/utils/__init__.py:2-34` - Utils has leftover standalone modules

### Pain Points

1. **Mixed responsibilities** - harder to reason about ownership
2. **Policy in wrong layer** - directive cache config lives in rendering pipeline
3. **Remediation mixed with validation** - autofix is operational, not validation

### Impact

- Higher cognitive cost navigating packages
- Blurred API boundaries increase coupling
- Cannot enforce model/orchestrator split at package level

---

## Goals and Non-Goals

### Goals

1. Separate concerns into focused subpackages
2. Move policy/config to owning subsystems
3. Enable `::arch` validation at subpackage level

### Non-Goals

1. No backward compatibility shims
2. No deprecation warnings or transitional paths
3. No public API preservation for internal restructuring

---

## Refactoring Plan

### 1. Content Package: Extract Versioning

**Current**:
```
bengal/content/discovery/
├── git_version_adapter.py
└── version_resolver.py
```

**After**:
```
bengal/content/
├── discovery/        # Local content/asset discovery only
├── sources/          # Remote sources (existing)
└── versioning/       # NEW
    ├── __init__.py
    ├── git_adapter.py
    └── resolver.py
```

**Changes**:
- Move `git_version_adapter.py` → `versioning/git_adapter.py`
- Move `version_resolver.py` → `versioning/resolver.py`
- Update imports across codebase

---

### 2. Analysis Package: Group by Concern

**Current**: 15 flat modules in `bengal/analysis/`

**After**:
```
bengal/analysis/
├── __init__.py
├── graph/
│   ├── __init__.py
│   ├── builder.py
│   ├── analyzer.py
│   ├── metrics.py
│   ├── visualizer.py
│   ├── reporter.py
│   ├── knowledge_graph.py
│   ├── community_detection.py
│   └── page_rank.py
├── links/
│   ├── __init__.py
│   ├── suggestions.py
│   ├── patterns.py
│   └── types.py
└── performance/
    ├── __init__.py
    ├── advisor.py
    └── path_analysis.py
```

**Changes**:
- Group graph-related modules under `graph/`
- Group link modules under `links/`
- Group performance modules under `performance/`
- Update imports across codebase

---

### 3. Rendering: Extract Directive Cache Policy

**Current**: `bengal/rendering/pipeline/core.py:66-107`
```python
def _configure_directive_cache_for_versions(site: Site) -> None:
    """Auto-enable directive cache for versioned sites."""
    from bengal.directives.cache import configure_cache
    # ... policy logic
```

**After**: Move to `bengal/directives/cache.py`
```python
def configure_for_site(site: Site) -> None:
    """Auto-enable directive cache for versioned sites."""
    # ... policy logic (unchanged)
```

**Changes**:
- Move function to `bengal/directives/cache.py`
- Update `RenderingPipeline.__init__` to call `directives.cache.configure_for_site(site)`

---

### 4. Health: Separate Remediation

**Current**:
```
bengal/health/
├── autofix.py        # 978 lines - remediation subsystem
├── linkcheck/        # standalone link checking
└── validators/       # validation checks
```

**After**:
```
bengal/health/
├── validators/       # validation only
├── linkcheck/        # link checking (unchanged)
└── remediation/      # NEW
    ├── __init__.py
    └── autofix.py
```

**Changes**:
- Move `autofix.py` → `remediation/autofix.py`
- Update imports across codebase

---

### 5. Utils: Clean Up Stragglers

**Current**:
```
bengal/utils/
├── primitives/
├── io/
├── paths/
├── concurrency/
├── observability/
├── lru_cache.py      # standalone
└── pagination.py     # standalone
```

**After**:
```
bengal/utils/
├── primitives/
│   └── lru_cache.py  # moved here
├── io/
├── paths/
├── concurrency/
├── observability/
└── pagination/       # NEW
    ├── __init__.py
    └── paginator.py
```

**Changes**:
- Move `lru_cache.py` → `primitives/lru_cache.py`
- Move `pagination.py` → `pagination/paginator.py`
- Update imports across codebase

---

## Architecture Impact

| Subsystem | Files Moved | Import Updates |
|-----------|-------------|----------------|
| `content/` | 2 | ~10-15 |
| `analysis/` | 12 | ~20-30 |
| `rendering/` | 1 function | ~3-5 |
| `health/` | 1 | ~5-10 |
| `utils/` | 2 | ~10-15 |
| **Total** | ~17 | ~50-75 |

---

## Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Versioning location | `bengal.content.versioning` | Cohesive with content discovery |
| Linkcheck location | `bengal.health.linkcheck` | Already correct, no change |
| Arch enforcement | Follow-up RFC | Separate scope |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Mass import breakage | Single PR with all changes; grep-based verification |
| Merge conflicts | Coordinate timing; rebase before merge |
| Missed imports | `make test` + `mypy` catch all |

---

## Implementation

### Phase 1: File Moves (3-4 hours)

```bash
# Content versioning
git mv bengal/content/discovery/git_version_adapter.py bengal/content/versioning/git_adapter.py
git mv bengal/content/discovery/version_resolver.py bengal/content/versioning/resolver.py

# Health remediation  
mkdir -p bengal/health/remediation
git mv bengal/health/autofix.py bengal/health/remediation/

# Utils cleanup
git mv bengal/utils/lru_cache.py bengal/utils/primitives/
mkdir -p bengal/utils/pagination
git mv bengal/utils/pagination.py bengal/utils/pagination/paginator.py
```

### Phase 2: Analysis Restructure (2-3 hours)

Create subpackage structure for `bengal/analysis/` with graph, links, performance groupings.

### Phase 3: Import Updates (2-3 hours)

```bash
# Find and update all imports
rg "from bengal.content.discovery import.*GitVersionAdapter" --files-with-matches
rg "from bengal.health import.*AutoFixer" --files-with-matches
# ... systematic updates
```

### Phase 4: Directive Cache Move (1 hour)

- Extract `_configure_directive_cache_for_versions` from `rendering/pipeline/core.py`
- Add to `bengal/directives/cache.py`
- Update caller in `RenderingPipeline.__init__`

**Total Effort**: 8-12 hours

---

## Validation

```bash
make lint      # No new errors
make test      # All pass
mypy bengal/   # Type check clean
```

---

## Commits

```bash
git add -A && git commit -m "content: extract versioning to dedicated subpackage"
git add -A && git commit -m "analysis: reorganize into graph/links/performance subpackages"
git add -A && git commit -m "health: move autofix to remediation subpackage"
git add -A && git commit -m "utils: move lru_cache to primitives, create pagination subpackage"
git add -A && git commit -m "rendering: extract directive cache policy to directives package"
```

---

## References

- **Evidence** (verified 2026-01-15):
  - `bengal/content/__init__.py:1-41`
  - `bengal/content/discovery/__init__.py:7-16`
  - `bengal/analysis/__init__.py:8-32`
  - `bengal/rendering/pipeline/core.py:66-107`
  - `bengal/health/__init__.py:4-41`
  - `bengal/utils/__init__.py:2-34`

- **Related**:
  - `::arch` - Architecture validation
  - Future: `rfc-arch-boundary-enforcement`
