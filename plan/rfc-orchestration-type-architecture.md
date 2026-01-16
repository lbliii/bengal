# RFC: Orchestration Package Type Architecture

**Status**: Draft  
**Created**: 2026-01-16  
**Author**: Claude Opus 4.5  
**Related**: `rfc-ty-type-hardening.md`, `rfc-protocol-consolidation.md`  
**Category**: Type System / Architecture / Orchestration

---

## Executive Summary

After fixing 54 type errors in `bengal/orchestration/`, **48 structural errors** remain that require architectural changes. These errors fall into 5 categories:

1. **Dynamic Site attributes** - Undeclared `_cache`, `_last_build_options` attributes (2 errors)
2. **Template engine type narrowing** - `TemplateEngine` vs `KidaTemplateEngine` (4 errors)
3. **hasattr pattern blindness** - ty can't narrow types after `hasattr()` checks (~20 errors)
4. **Undeclared orchestrator attributes** - `_provenance_filter` on `BuildOrchestrator` (4 errors)
5. **Protocol/implementation gaps** - Missing methods on protocols, optional handling (~18 errors)

**Impact**: These errors don't cause runtime failures (code uses `hasattr` guards) but prevent type safety guarantees and IDE support.

**Target**: Reduce orchestration package errors from 48 to <10 while maintaining backward compatibility.

---

## Goals & Non-Goals

### Goals

- Achieve <10 ty errors in orchestration package
- Maintain full backward compatibility (no runtime behavior changes)
- Improve IDE autocomplete and type inference
- Establish patterns for type-safe config access

### Non-Goals

- Changing the `Config` class architecture (covered in `rfc-config-architecture-v2.md`)
- Addressing mypy-specific errors (this RFC focuses on ty)
- Removing the pluggable template engine abstraction
- Modifying the `TemplateEngineProtocol` interface

---

## Problem Statement

### Current Error Distribution (48 total)

| Category | Count | Severity | Effort |
|----------|-------|----------|--------|
| hasattr pattern narrowing | ~20 | Low | High |
| Template engine types | 4 | Medium | Medium |
| Dynamic Site attributes | 2 | High | Low |
| Undeclared orchestrator attrs | 4 | High | Low |
| Other type mismatches | ~18 | Medium | Medium |

*Note: `Site._last_build_stats` already exists (line 196 of `bengal/core/site/core.py`), so only `_cache` and `_last_build_options` need to be added.*

### Root Cause Analysis

#### 1. Dynamic Site Attributes (2 errors)

**Location**: `bengal/orchestration/build/__init__.py:343-344`

```python
# Current code - assigns to undeclared attributes
self.site._last_build_options = options  # ty: invalid-assignment
self.site._cache = self.incremental.cache  # ty: invalid-assignment
```

**Root Cause**: `Site` class doesn't declare `_cache` and `_last_build_options` as typed fields.

*Note: `_last_build_stats` is already declared at `bengal/core/site/core.py:196`.*

**Evidence**:
```
error[invalid-assignment]: Object of type `BuildOptions` is not assignable 
to attribute `_last_build_options` on type `Unknown | Site`
```

---

#### 2. Template Engine Type Narrowing (4 errors)

**Location**: Multiple files using `warm_site_blocks`, `validate_templates`

```python
# TemplateEngine is the abstract type
engine: TemplateEngine = create_engine(self.site)

# But warm_site_blocks requires KidaTemplateEngine
self._block_cache.warm_site_blocks(engine, template_name, site_context)
# ty: Expected `KidaTemplateEngine`, found `TemplateEngine`
```

**Root Cause**: `create_engine()` returns the abstract `TemplateEngine` type, but the block cache and validation methods require the concrete `KidaTemplateEngine`.

**Evidence**:
```
error[invalid-argument-type]: Argument to bound method `warm_site_blocks` 
is incorrect: Expected `KidaTemplateEngine`, found `TemplateEngine`
```

---

#### 3. hasattr Pattern Blindness (22 errors)

**Location**: Entire orchestration package

```python
# Pattern used throughout codebase
config = self.site.config
if hasattr(config, "build"):
    return config.build.max_workers  # ty: object has no attribute max_workers
```

**Root Cause**: ty doesn't narrow types after `hasattr()` checks. The type checker sees `object` after hasattr, not the specific type.

**Evidence**:
```
error[unresolved-attribute]: Object of type `object` has no attribute `max_workers`
```

This pattern appears 6+ times for `config.build.max_workers` alone.

---

#### 4. Undeclared BuildOrchestrator Attributes (4 errors)

**Location**: `bengal/orchestration/build/provenance_filter.py:368`

```python
# Storing provenance filter for later use
orchestrator._provenance_filter = provenance_filter  # ty: unresolved attribute
```

**Root Cause**: `BuildOrchestrator` doesn't declare `_provenance_filter` as a class attribute.

**Evidence**:
```
error[unresolved-attribute]: Unresolved attribute `_provenance_filter` 
on type `BuildOrchestrator`
```

---

#### 5. Other Type Mismatches (18 errors)

These errors are categorized into three main groups requiring different fixes:

1. **Path Normalization** (5 errors): Mismatches between `str` and `pathlib.Path` in menu and asset building.
2. **Strict Optional Handling** (9 errors): Missing guards for `| None` types when passing to methods requiring concrete types (PageCore, FilterResult, BuildProfile).
3. **Collection Type Gaps** (4 errors): Mismatches in collection types (e.g., `set[str]` where `set[Path]` is expected) and initialization arguments.

---

## Proposed Solutions

### Solution 1: Declare Dynamic Site Attributes

**Approach**: Add typed attributes to `Site` class for build-time state.

**File**: `bengal/core/site/core.py`

```python
@dataclass
class Site:
    # ... existing fields (around line 196) ...
    
    # Build-time ephemeral state (not persisted)
    # These are set by BuildOrchestrator during builds
    _cache: BuildCache | None = field(default=None, repr=False, init=False)
    _last_build_options: BuildOptions | None = field(default=None, repr=False, init=False)
    # Note: _last_build_stats already exists at line 196
```

**Existing**: `_last_build_stats` is already declared:
```python
# bengal/core/site/core.py:196
_last_build_stats: dict[str, Any] | None = field(default=None, repr=False, init=False)
```

**Impact**: 
- Fixes 2 errors
- Makes build-time state explicit
- Improves IDE autocomplete

**Risk**: Low - only adds optional attributes with None defaults

---

### Solution 2: Template Engine Type Refinement

**Approach**: Use type guard for engine type narrowing.

**Context**: Bengal supports multiple template engines (kida, jinja2, mako, patitas) via the pluggable `TemplateEngineProtocol`. However, Kida-specific features like `warm_site_blocks` and `validate_templates` require type narrowing.

**Option A: Type Guard Function (Recommended)**

```python
# bengal/rendering/engines/__init__.py
from typing import TypeGuard

def is_kida_engine(engine: TemplateEngineProtocol) -> TypeGuard[KidaTemplateEngine]:
    """Check if engine is KidaTemplateEngine for Kida-specific features."""
    return isinstance(engine, KidaTemplateEngine)

# Usage
engine = create_engine(self.site)
if is_kida_engine(engine):
    self._block_cache.warm_site_blocks(engine, template_name, site_context)
```

**Option B: Conditional Cast**

```python
from typing import cast

engine = create_engine(self.site)
if isinstance(engine, KidaTemplateEngine):
    # Safe cast after isinstance check
    self._block_cache.warm_site_blocks(engine, template_name, site_context)
```

**Option C: Change create_engine Return Type**

```python
# NOT RECOMMENDED - breaks pluggable engine architecture
def create_engine(site: Site) -> KidaTemplateEngine:
    return KidaTemplateEngine(site)
```

**Recommended**: **Option A** (TypeGuard) - preserves pluggable architecture while providing type safety for Kida-specific features.

**Impact**:
- Fixes 4 errors
- Preserves multi-engine support (jinja2, mako, patitas)
- Enables Kida-specific optimizations with type safety

**Risk**: Low - TypeGuard is standard Python typing pattern

---

### Solution 3: Replace hasattr with Protocol Checks

**Approach**: Use TypeGuard or structural pattern matching for config access.

**Option A: Config Protocol with Type Guard**

```python
# bengal/config/protocols.py
from typing import Protocol, TypeGuard

class ConfigWithBuild(Protocol):
    @property
    def build(self) -> BuildSection: ...

def has_build_config(config: Config | dict) -> TypeGuard[ConfigWithBuild]:
    """Type guard for configs with build section."""
    return hasattr(config, "build")

# Usage
config = self.site.config
if has_build_config(config):
    return config.build.max_workers  # Now typed correctly
```

**Option B: Accessor Method with Fallback**

```python
# bengal/config/accessor.py
class Config:
    def get_max_workers(self, default: int | None = None) -> int | None:
        """Get max_workers with proper typing."""
        if hasattr(self, "build") and hasattr(self.build, "max_workers"):
            return self.build.max_workers
        return default

# Usage
config = self.site.config
if isinstance(config, Config):
    max_workers = config.get_max_workers()
```

**Option C: Explicit Type Narrowing with Assert**

```python
config = self.site.config
if hasattr(config, "build"):
    build = config.build
    assert hasattr(build, "max_workers")
    return build.max_workers  # Still not narrowed by ty
```

**Recommended**: Option A (TypeGuard) for type safety, Option B for ergonomics. **Centralizing guards in `bengal/config/guards.py` is recommended to prevent duplication.**

**Performance Note**: TypeGuard functions are essentially wrapper functions around `hasattr` or `isinstance`. The overhead is negligible (nanoseconds) compared to the orchestration I/O, but the type safety benefits are substantial for maintainability.

**Impact**:
- Fixes 22 errors (6 `max_workers` + similar patterns)
- Improves type safety throughout
- Better IDE support

**Risk**: Medium - requires refactoring all hasattr patterns

---

### Solution 4: Declare BuildOrchestrator Attributes

**Approach**: Add typed attributes for dynamic state.

**File**: `bengal/orchestration/build/__init__.py`

```python
class BuildOrchestrator:
    # ... existing code ...
    
    # Provenance tracking (set during incremental builds)
    _provenance_filter: ProvenanceFilter | None = None
```

**Impact**:
- Fixes 4 errors
- Makes incremental build state explicit

**Risk**: Low - only adds optional attribute

---

### Solution 5: Fix Remaining Type Mismatches

#### 5a: Path/str Normalization

**Location**: `bengal/orchestration/build/content.py:278`

```python
# Current
changed_page_paths: set[str]  # strings
menu_rebuilt = orchestrator.menu.build(
    changed_pages=changed_page_paths  # ty: Expected set[Path]
)

# Fix: Convert to Path
changed_page_paths: set[Path] = {Path(p) for p in changed_strings}
```

#### 5b: Optional Return Type Handling

**Location**: `bengal/orchestration/build/__init__.py:737`

```python
# Current - returns FilterResult | None
return phase_incremental_filter_provenance(...)

# Fix: Handle None case
result = phase_incremental_filter_provenance(...)
if result is None:
    raise BuildError("Provenance filtering failed")
return result
```

#### 5c: Optional Parameter Guards

**Location**: `bengal/orchestration/build/__init__.py:823`

```python
# Current
profile: BuildProfile | None
phase_render(..., profile=profile)  # ty: Expected BuildProfile

# Fix: Guard with assertion
assert profile is not None, "Profile required for rendering"
phase_render(..., profile=profile)
```

---

## Implementation Plan

### Phase 1: Quick Wins (1 hour)

1. **Declare Site attributes** - Add `_cache`, `_last_build_options` to `bengal/core/site/core.py`
   - Note: `_last_build_stats` already exists (line 196)
2. **Declare BuildOrchestrator attributes** - Add `_provenance_filter`
3. **Add assertions for None guards** - profile, PageCore, FilterResult

**Expected Reduction**: 8-10 errors

### Phase 2: Template Engine TypeGuard (30 min)

1. **Add `is_kida_engine()` TypeGuard** to `bengal/rendering/engines/__init__.py`
2. **Update callers** to use TypeGuard pattern for Kida-specific features

**Expected Reduction**: 4 errors

### Phase 3: Config Access Refactoring (2-3 hours)

1. **Create `bengal/config/guards.py`** with TypeGuard functions for common config patterns (build, search, etc.)
2. **Refactor hasattr patterns** in orchestration to use these TypeGuards
3. **Add accessor methods** to Config class in `bengal/config/accessor.py`

**Expected Reduction**: 22 errors

### Phase 4: Cleanup (1 hour)

1. **Fix Path/str mismatches** 
2. **Add remaining type guards**
3. **Document remaining intentional gaps**

**Expected Reduction**: ~5 errors

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Orchestration ty errors | 48 | <10 |
| Runtime test failures | 0 | 0 |
| IDE autocomplete coverage | Partial | Full |
| Type-safe config access | No | Yes |
| Pluggable engine architecture | Preserved | Preserved |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Runtime behavior changes | Full test suite after each phase |
| Circular imports from new types | Use `TYPE_CHECKING` blocks |
| Over-complicating config access | Start with simple accessor methods |
| Breaking backward compatibility | Keep hasattr patterns working |
| Breaking pluggable engine architecture | Use TypeGuard instead of changing return types |

---

## Alternatives Considered

### 1. Suppress All with `# type: ignore`

**Rejected**: Defeats purpose of type checking, hides real bugs.

### 2. Disable ty for Orchestration Package

**Rejected**: Orchestration is critical path - needs type safety.

### 3. Wait for ty Improvements

**Rejected**: ty may never support hasattr narrowing due to Python dynamism.

### 4. Use Any Everywhere

**Rejected**: Loses all type safety benefits.

### 5. Change `create_engine()` Return Type to `KidaTemplateEngine`

**Rejected**: Bengal supports multiple template engines (jinja2, mako, patitas). Changing the return type would break the pluggable architecture and limit user choice. TypeGuard provides type safety without sacrificing flexibility.

---

## Files Affected

### High-Impact Changes

| File | Changes | Errors Fixed |
|------|---------|--------------|
| `bengal/core/site/core.py` | Add `_cache`, `_last_build_options` | 2 |
| `bengal/orchestration/build/__init__.py` | Add `_provenance_filter`, guards | 8 |
| `bengal/rendering/engines/__init__.py` | Add `is_kida_engine()` TypeGuard | 4 |
| `bengal/config/accessor.py` | Add TypeGuard functions, accessor methods | ~20 |

### Medium-Impact Changes

| File | Changes | Errors Fixed |
|------|---------|--------------|
| `bengal/orchestration/build/content.py` | Path normalization | 1 |
| `bengal/orchestration/build/initialization.py` | PageCore guard | 2 |
| `bengal/orchestration/render/orchestrator.py` | TypeGuard usage | 2 |
| `bengal/orchestration/incremental/*.py` | TypeGuard usage | 6 |

---

## Appendix: Error Evidence

### Full Error List (48 errors, as of 2026-01-16)

*Run `uv run ty check bengal/orchestration/` to verify current count.*

**Sample errors by category:**

```
# hasattr pattern blindness (~20 errors)
6x  unresolved-attribute: object has no attribute `max_workers`
7x  call-non-callable: Object of type `object` is not callable
2x  unresolved-attribute: object has no attribute `record_build`
1x  unresolved-attribute: object has no attribute `save`

# Template engine types (4 errors)
2x  invalid-argument-type: warm_site_blocks() engine type
1x  invalid-assignment: TemplateEngine vs KidaTemplateEngine
1x  unresolved-attribute: TemplateEngine has no validate_templates

# Dynamic Site attributes (2 errors)
1x  invalid-assignment: BuildCache vs Site._cache
1x  invalid-assignment: BuildOptions vs Site._last_build_options

# Undeclared orchestrator attrs (4 errors)
1x  unresolved-attribute: _provenance_filter on BuildOrchestrator
+3  related hasattr guards for _provenance_filter

# Other type mismatches (~18 errors)
6x  invalid-argument-type: submit() argument mismatch
4x  invalid-argument-type: Path.__new__() argument mismatch
2x  possibly-missing-attribute: `add_error` may be missing
2x  invalid-return-type: FilterResult | None vs FilterResult
2x  invalid-argument-type: __init__() argument mismatch
2x  invalid-argument-type: cache argument type
1x  invalid-argument-type: phase_render profile argument
```

---

## References

- [ty Type Checker Documentation](https://docs.astral.sh/ty/)
- [Python TypeGuard PEP 647](https://peps.python.org/pep-0647/)
- Related RFC: `rfc-ty-type-hardening.md`
- Related RFC: `rfc-protocol-consolidation.md`
- Related RFC: `rfc-config-architecture-v2.md`
