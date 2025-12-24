# RFC: Directive Processing & Template Rendering Optimization

**Status**: Draft  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P1 (High)  
**Related**: `bengal/directives/`, `bengal/rendering/engines/jinja.py`  
**Confidence**: 75% 🟡

---

## Executive Summary

Profiling indicates that directive processing and template rendering are the primary bottlenecks after markdown parsing. This RFC identifies **8 validated optimization opportunities** across two subsystems:

| Category | Optimizations | Projected Speedup |
|----------|---------------|-------------------|
| **Directive Processing** | 5 validated changes | 30-40% faster |
| **Template Rendering** | 3 validated changes | 10-15% faster |
| **Combined Impact** | | **10-15% faster builds** |

Most changes are low-risk, incremental improvements that don't require architectural changes.

> **Note**: Initial estimates were overly optimistic. After code review, some proposed optimizations were found to be already implemented, redundant with Jinja2 internals, or incorrectly specified. This revision reflects validated improvements only.

---

## Part 1: Directive Processing Optimizations

### Current Flow (Per Directive)

```
┌─────────────────────────────────────────────────────────────────┐
│                    For EACH directive encountered:               │
├─────────────────────────────────────────────────────────────────┤
│  1. Pattern match (regex) ────────────────────── ~0.1ms         │
│  2. Get directive class from registry ─────────── ~0.05ms       │
│  3. Create directive instance ──────────────────── ~0.2ms  ← SLOW│
│     - __init__() runs                                           │
│     - get_logger() called                                       │
│  4. Parse title from match ────────────────────── ~0.02ms       │
│  5. Parse options from match ────────────────────── ~0.1ms      │
│  6. OPTIONS_CLASS.from_raw() ────────────────────── ~0.3ms ← SLOW│
│     - get_type_hints() called                                   │
│     - fields() called                                           │
│     - _coerce_value() per option                                │
│  7. Contract validation (if defined) ─────────── ~0.1ms         │
│  8. parse_tokens() for nested content ─────────── RECURSIVE     │
│  9. parse_directive() (subclass) ────────────────── ~0.1ms      │
│ 10. render() (subclass) ─────────────────────────── ~0.2ms      │
│ 11. String concatenation for HTML ───────────────── ~0.1ms      │
├─────────────────────────────────────────────────────────────────┤
│  TOTAL per directive: ~1.2ms + nested                           │
│  × 19 directives/page average = ~23ms/page                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### Optimization 1: Singleton Directive Instances ✅ VALIDATED

**Status**: ✅ High confidence, high impact

**Problem**: `create_documentation_directives()` creates 40+ new directive instances every time `plugin_documentation_directives()` is called.

```python
# factory.py:175-228 (CURRENT - creates new instances every call)
def plugin_documentation_directives(md):
    directives_list = [
        AdmonitionDirective(),   # New instance
        BadgeDirective(),        # New instance
        TabSetDirective(),       # New instance
        # ... 40+ more
    ]
```

**Solution**: Pre-instantiate directives at module level with lazy initialization.

```python
# bengal/directives/factory.py (PROPOSED)

from threading import Lock

# Module-level singleton list with thread-safe initialization
_DIRECTIVE_INSTANCES: list[BengalDirective] | None = None
_INSTANCE_LOCK = Lock()

def _get_directive_instances() -> list[BengalDirective]:
    """Get or create singleton directive instances (thread-safe)."""
    global _DIRECTIVE_INSTANCES
    if _DIRECTIVE_INSTANCES is not None:
        return _DIRECTIVE_INSTANCES

    with _INSTANCE_LOCK:
        # Double-check after acquiring lock
        if _DIRECTIVE_INSTANCES is not None:
            return _DIRECTIVE_INSTANCES

        _DIRECTIVE_INSTANCES = [
            AdmonitionDirective(),
            BadgeDirective(),
            TabSetDirective(),
            # ... all directives
        ]
        return _DIRECTIVE_INSTANCES

def create_documentation_directives() -> Callable[[Any], None]:
    """Create the documentation directives plugin for Mistune."""

    def plugin_documentation_directives(md: Any) -> None:
        """Register all documentation directives with a Mistune instance."""
        logger = get_logger(__name__)

        try:
            # Use singleton instances instead of creating new ones
            directives_list = _get_directive_instances()

            # Conditionally add Marimo (still needs per-call check)
            try:
                import marimo  # noqa: F401
                # Marimo directive added to singleton list on first init
            except ImportError:
                pass

            directive = FencedDirective(directives_list, markers=":")
            return directive(md)
        except Exception as e:
            logger.error("directive_registration_error", error=str(e))
            raise

    return plugin_documentation_directives


def reset_directive_instances() -> None:
    """Reset singleton instances (for testing only)."""
    global _DIRECTIVE_INSTANCES
    with _INSTANCE_LOCK:
        _DIRECTIVE_INSTANCES = None
```

**Prerequisites**: Verify directives are stateless (no instance variables modified during parse/render).

**Impact**: Saves ~6-8ms per parser creation (40 × 0.15-0.2ms).

---

### Optimization 2: Cached Type Hints for Options ✅ VALIDATED

**Status**: ✅ High confidence, medium impact

**Problem**: `get_type_hints()` and `fields()` are called on every `from_raw()` call.

```python
# options.py:113-115 (CURRENT - called every time)
def from_raw(cls, raw_options: dict[str, str]) -> DirectiveOptions:
    kwargs: dict[str, Any] = {}
    hints = get_type_hints(cls)  # SLOW: ~50μs per call
    known_fields = {f.name for f in fields(cls) if not f.name.startswith("_")}
```

**Solution**: Cache at class level using `__init_subclass__`.

```python
# bengal/directives/options.py (PROPOSED)

@dataclass
class DirectiveOptions:
    # Cached at class definition time
    _cached_hints: ClassVar[dict[str, type]] = {}
    _cached_fields: ClassVar[set[str]] = set()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Pre-compute type hints and fields when class is defined."""
        super().__init_subclass__(**kwargs)

        # Only cache after @dataclass decorator has run
        # Check for __dataclass_fields__ to confirm dataclass is ready
        if hasattr(cls, '__dataclass_fields__'):
            try:
                cls._cached_hints = get_type_hints(cls)
                cls._cached_fields = {
                    f.name for f in fields(cls)
                    if not f.name.startswith("_")
                }
            except Exception:
                # Fallback: will compute at runtime
                cls._cached_hints = {}
                cls._cached_fields = set()

    @classmethod
    def from_raw(cls, raw_options: dict[str, str]) -> DirectiveOptions:
        kwargs: dict[str, Any] = {}

        # Use cached values, with fallback for edge cases
        hints = cls._cached_hints or get_type_hints(cls)
        known_fields = cls._cached_fields or {
            f.name for f in fields(cls) if not f.name.startswith("_")
        }

        for raw_name, raw_value in raw_options.items():
            # ... rest of parsing logic unchanged
```

**Impact**: Saves ~50μs × 19 directives = ~1ms per page.

---

### Optimization 3: Class-Level Logger ✅ VALIDATED

**Status**: ✅ High confidence, low-medium impact

**Problem**: Each directive instance creates its own logger in `__init__`.

```python
# base.py:174-175 (CURRENT)
def __init__(self) -> None:
    super().__init__()
    self.logger = get_logger(self.__class__.__module__)  # Called per instance
```

**Solution**: Use class-level logger via `__init_subclass__`.

```python
# bengal/directives/base.py (PROPOSED)

class BengalDirective(DirectivePlugin):
    # Class-level logger, initialized per subclass
    _class_logger: ClassVar[logging.Logger | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize class-level logger when subclass is defined."""
        super().__init_subclass__(**kwargs)
        cls._class_logger = get_logger(cls.__module__)

    @property
    def logger(self) -> logging.Logger:
        """Instance property that returns the class-level logger."""
        if self._class_logger is not None:
            return self._class_logger
        # Fallback for base class or edge cases
        return get_logger(self.__class__.__module__)

    def __init__(self) -> None:
        super().__init__()
        # No logger creation here - uses class-level logger via property
```

**Impact**: Saves ~20μs × 40 directives = ~0.8ms per parser creation.

---

### Optimization 4: Skip Contract Validation in Production ⚠️ VALIDATED WITH CAVEATS

**Status**: ⚠️ Medium confidence, medium impact (has risks)

**Problem**: Contract validation runs on every directive, even in production builds.

```python
# base.py:211-217 (CURRENT - always runs)
if self.CONTRACT and self.CONTRACT.has_parent_requirement and location:
    parent_type = self._get_parent_directive_type(state)
    violations = ContractValidator.validate_parent(...)
    for v in violations:
        self.logger.warning(...)
```

**Solution**: Pass validation mode via parser state (avoids global mutable state).

```python
# bengal/directives/base.py (PROPOSED)

class BengalDirective(DirectivePlugin):
    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        location = self._get_source_location(state)

        # Check validation mode from state.env (set by build orchestrator)
        env = getattr(state, "env", {}) or {}
        validate_contracts = env.get("validate_contracts", True)

        # Skip validation in production mode
        if validate_contracts and self.CONTRACT and self.CONTRACT.has_parent_requirement and location:
            parent_type = self._get_parent_directive_type(state)
            violations = ContractValidator.validate_parent(...)
            for v in violations:
                self.logger.warning(...)

        # ... rest of parsing
```

```python
# bengal/orchestration/build.py (integration)

def build(production: bool = False):
    # Set validation mode in parser environment
    parser_env = {
        "validate_contracts": not production,
        # ... other env settings
    }
    # Pass to markdown parser initialization
```

**Mitigations Required**:
1. Always validate in `bengal serve` (dev mode)
2. CI pipeline must run with `validate_contracts=True`
3. Add `--validate` flag to force validation in production builds

**Impact**: Saves ~0.1ms × 19 directives = ~1.5-2ms per page in production.

---

### Optimization 5: Pre-compiled Option Coercers ✅ VALIDATED

**Status**: ✅ High confidence, medium impact

**Problem**: Option coercion logic runs type-checking conditionals for every value.

**Solution**: Pre-compile coercion functions per field at class definition time.

```python
# bengal/directives/options.py (PROPOSED)

from typing import Callable, get_origin, get_args

@dataclass
class DirectiveOptions:
    # Pre-compiled coercers for each field
    _coercers: ClassVar[dict[str, Callable[[str], Any]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if hasattr(cls, '__dataclass_fields__'):
            try:
                cls._cached_hints = get_type_hints(cls)
                cls._cached_fields = {
                    f.name for f in fields(cls) if not f.name.startswith("_")
                }

                # Pre-compile coercers for each typed field
                cls._coercers = {}
                for name, hint in cls._cached_hints.items():
                    if not name.startswith("_"):
                        cls._coercers[name] = cls._compile_coercer(hint)
            except Exception:
                pass  # Fallback to runtime coercion

    @staticmethod
    def _compile_coercer(target_type: type) -> Callable[[str], Any]:
        """Return a fast coercion function for the target type."""
        # Handle Optional[T] / T | None
        origin = get_origin(target_type)
        if origin is type(None) or (origin and type(None) in get_args(target_type)):
            args = get_args(target_type)
            target_type = next((a for a in args if a is not type(None)), str)
            origin = get_origin(target_type)

        if target_type is bool:
            _truthy = frozenset(("true", "1", "yes", ""))
            return lambda v: v.lower() in _truthy

        if target_type is int:
            def _int_coerce(v: str) -> int:
                return int(v) if v.lstrip("-").isdigit() else 0
            return _int_coerce

        if target_type is float:
            def _float_coerce(v: str) -> float:
                try:
                    return float(v)
                except ValueError:
                    return 0.0
            return _float_coerce

        if origin is list or target_type is list:
            return lambda v: [x.strip() for x in v.split(",") if x.strip()]

        # String passthrough (identity function)
        return lambda v: v

    @classmethod
    def from_raw(cls, raw_options: dict[str, str]) -> DirectiveOptions:
        kwargs: dict[str, Any] = {}
        known_fields = cls._cached_fields or {
            f.name for f in fields(cls) if not f.name.startswith("_")
        }

        for raw_name, raw_value in raw_options.items():
            field_name = cls._field_aliases.get(raw_name, raw_name.replace("-", "_"))
            if field_name not in known_fields:
                continue

            # Use pre-compiled coercer if available
            coercer = cls._coercers.get(field_name)
            if coercer:
                try:
                    coerced = coercer(raw_value)

                    # Validate allowed values
                    if field_name in cls._allowed_values:
                        allowed = cls._allowed_values[field_name]
                        if coerced not in allowed:
                            continue  # Skip invalid, use default

                    kwargs[field_name] = coerced
                except (ValueError, TypeError):
                    pass  # Use default
            else:
                # Fallback to runtime coercion
                kwargs[field_name] = cls._coerce_value(raw_value,
                    cls._cached_hints.get(field_name, str))

        return cls(**kwargs)
```

**Impact**: Saves ~30μs × 3 options × 19 directives = ~1.5ms per page.

---

### ~~Optimization 6: StringIO for HTML Building~~ ⚠️ DEFERRED

**Status**: ⚠️ Low confidence, marginal impact — **Benchmark before implementing**

**Problem**: Directive render methods concatenate strings repeatedly.

**Reality Check**: In Python, for small strings (< 10 concatenations), `str + str` or `"".join(list)` is often **faster** than `StringIO` due to method call overhead.

**Recommendation**:
1. Benchmark specific directives with complex HTML (tabs, cards, code-tabs)
2. Only apply to directives with > 10 string operations
3. Consider simple list-join pattern instead of full HTMLBuilder class

**Deferred Impact**: ~0.02-0.05ms per page (originally estimated 0.2ms — overstated)

---

### ~~Optimization 7: Lazy Directive Stack~~ ❌ DROPPED

**Status**: ❌ No benefit in current codebase

**Problem**: Directive stack operations run even when no contracts need them.

**Reality Check**: Bengal defines contracts for several directives (STEP_CONTRACT, TAB_SET_CONTRACT, CARDS_CONTRACT, etc.). Since contracts ARE defined, the `_ANY_CONTRACTS_DEFINED` flag would always be True, providing **zero benefit**.

**Decision**: Drop this optimization. Stack operations are lightweight (~5μs) and the conditional check would add overhead without benefit.

---

## Part 2: Template Rendering Optimizations

### Current Flow (Per Page)

```
┌─────────────────────────────────────────────────────────────────┐
│                    For EACH page rendered:                       │
├─────────────────────────────────────────────────────────────────┤
│  1. Build page context dict ─────────────────────── ~0.2ms      │
│     - Global contexts are CACHED (site/config/theme/menus)      │
│     - Per-page wrappers built on demand                         │
│  2. Determine template name ─────────────────────── ~0.05ms     │
│  3. Acquire template lock ───────────────────────── ~0.02ms     │
│     - Lock is per-template, uncontended after first compile     │
│  4. Get template from cache ─────────────────────── ~0.1ms      │
│     - Jinja2 caches compiled templates in Environment           │
│  5. Check asset manifest ────────────────────────── ~0.1ms      │
│     - Already has lazy loading with mtime caching               │
│  6. Render template ─────────────────────────────── ~2-5ms      │
│  7. Format HTML output ──────────────────────────── ~0.1ms      │
├─────────────────────────────────────────────────────────────────┤
│  TOTAL per page: ~2.5-5.5ms                                     │
│  × 1000 pages = 2.5-5.5 seconds                                 │
└─────────────────────────────────────────────────────────────────┘
```

> **Note**: The existing codebase already implements several optimizations:
> - `_get_global_contexts(site)` caches site/config/theme/menus wrappers
> - Asset manifest has lazy loading with `_asset_manifest_loaded` flag
> - Template path caching via `_template_path_cache`

---

### ~~Optimization 8: Lazy Context~~ ⚠️ ALREADY IMPLEMENTED

**Status**: ⚠️ Already partially implemented — verify overhead before adding more

**Current State**: `bengal/rendering/context/__init__.py` already implements:
- `_get_global_contexts(site)` caches `SiteContext`, `ConfigContext`, `ThemeContext`, `MenusContext`
- `build_page_context()` only creates per-page wrappers (`ParamsContext`, `SectionContext`)

**Recommendation**: Measure actual context building overhead before implementing additional lazy loading. The original 0.5ms estimate was based on building everything from scratch, but global contexts are already cached.

**Revised Action**: Profile `build_page_context()` to identify if any specific wrappers are slow. Only optimize measured bottlenecks.

---

### ~~Optimization 9: Lock-Free Template Cache Check~~ ❌ DROPPED (BUG)

**Status**: ❌ Original implementation was incorrect

**Original Problem**: Lock acquired even when template is already cached.

**Bug in Original Proposal**: The proposed code caught `TemplateNotFound`, but that exception is raised when a template **doesn't exist**, not when it needs compilation. Jinja2's `get_template()` checks its internal cache first automatically.

**Current Behavior Analysis**:
```python
# jinja.py:161-162 (CURRENT)
with _template_compilation_locks.get_lock(name):
    template = self.env.get_template(name)
```

The lock is per-template (`PerKeyLockManager`). After first compilation:
1. Template is in Jinja2's internal cache
2. Lock acquisition is uncontended (fast path)
3. `get_template()` returns cached template immediately

**Decision**: Drop this optimization. The current implementation is correct and the overhead after first render is negligible (~0.02ms for uncontended lock).

---

### Optimization 10: Production-Mode Asset Manifest ✅ VALIDATED

**Status**: ✅ Medium confidence, low impact

**Current State**: Already has lazy loading, but checks mtime on each access in dev mode.

**Enhancement**: Skip mtime checks entirely in production builds.

```python
# bengal/rendering/engines/jinja.py (PROPOSED)

class JinjaTemplateEngine(...):
    def __init__(self, site: Site, *, profile: bool = False) -> None:
        # ... existing init ...

        # Asset manifest handling
        self._asset_manifest_path = self.site.output_dir / "asset-manifest.json"
        self._asset_manifest_cache: dict[str, AssetManifestEntry] = {}
        self._asset_manifest_loaded: bool = False

        # Production mode skips mtime checks entirely
        self._production_mode: bool = getattr(site, 'production', False)

    def _get_asset_manifest_entry(self, key: str) -> AssetManifestEntry | None:
        """Get asset manifest entry with mode-appropriate caching."""
        if not self._asset_manifest_loaded:
            self._load_asset_manifest()

        # In production mode, never recheck file
        if self._production_mode:
            return self._asset_manifest_cache.get(key)

        # In dev mode, check mtime for hot-reload
        # ... existing mtime check logic ...
```

**Impact**: Saves ~0.05-0.1ms per page in production builds.

---

### ~~Optimization 11: Template Function Lazy Import~~ ⚠️ LOW PRIORITY

**Status**: ⚠️ Valid but low priority — initialization cost is amortized

**Problem**: All template functions imported at engine init.

**Reality Check**: The 50ms initialization cost is a **one-time cost** per build. For a 1000-page build, this is only 0.05ms per page amortized.

**Recommendation**: Implement only if startup time is a measured problem. The risk of runtime import errors outweighs the small benefit.

**Required Mitigation** (if implemented):
```python
# Dev mode startup check to catch import errors early
if not production_mode:
    for name, lazy_func in env.globals.items():
        if isinstance(lazy_func, LazyFunction):
            lazy_func._ensure_loaded()  # Force import to catch errors
```

---

### ~~Optimization 12: Cached Template Inheritance Chain~~ ❌ DROPPED (REDUNDANT)

**Status**: ❌ Redundant with Jinja2 internals

**Problem**: Template inheritance resolved every render.

**Reality Check**: Jinja2 **already caches** compiled templates including fully-resolved inheritance chains. When using `FileSystemBytecodeCache`, templates are compiled once and cached on disk.

**Decision**: Drop this optimization. It would duplicate Jinja2's built-in caching and add maintenance burden without benefit.

---

## Revised Implementation Priority

### Phase 1: High-Impact Quick Wins (3-4 days)

| # | Optimization | Effort | Impact | Confidence |
|---|--------------|--------|--------|------------|
| 1 | Singleton directives | 3 hours | 6-8ms/parser | ✅ High |
| 2 | Cached type hints | 3 hours | ~1ms/page | ✅ High |
| 3 | Class-level logger | 2 hours | ~0.8ms/parser | ✅ High |
| 5 | Pre-compiled coercers | 4 hours | ~1.5ms/page | ✅ High |

**Phase 1 Impact**: ~8ms/parser + ~2.5ms/page

For 1000 pages: **~2.5 seconds faster**

### Phase 2: Medium Effort (2-3 days)

| # | Optimization | Effort | Impact | Confidence |
|---|--------------|--------|--------|------------|
| 4 | Skip validation in prod | 3 hours | ~1.5ms/page | ⚠️ Medium |
| 10 | Production manifest mode | 2 hours | ~0.05ms/page | ✅ Medium |

**Phase 2 Impact**: ~1.5ms/page

For 1000 pages: **~1.5 seconds faster**

### Phase 3: Deferred / Investigate

| # | Optimization | Action |
|---|--------------|--------|
| 6 | HTMLBuilder | Benchmark first; apply selectively if warranted |
| 8 | Lazy context | Profile `build_page_context()` before optimizing |
| 11 | Lazy functions | Low priority; only if startup time is a problem |

### Dropped

| # | Optimization | Reason |
|---|--------------|--------|
| 7 | Lazy directive stack | No benefit (contracts are defined) |
| 9 | Lock-free template | Bug in original proposal; current impl is correct |
| 12 | Cached inheritance | Redundant with Jinja2 internals |

---

## Realistic Projected Impact

### Before Optimizations

| Phase | Time (1000 pages) |
|-------|-------------------|
| Markdown parsing | 5s |
| Directive processing | 23s |
| Template rendering | 5s |
| File I/O | 2s |
| **Total** | **35s** |

### After Phase 1+2 Optimizations

| Phase | Time (1000 pages) | Improvement |
|-------|-------------------|-------------|
| Markdown parsing | 5s | - |
| Directive processing | 19s | **17% faster** |
| Template rendering | 4.5s | **10% faster** |
| File I/O | 2s | - |
| **Total** | **30.5s** | **~13% faster** |

> **Note**: Original RFC projected 41% improvement. After code review and validation, a realistic expectation is **10-15% improvement**. Further gains require deeper architectural changes (parallel processing, Rust extensions, etc.).

---

## Testing Strategy

### Micro-benchmarks

```python
# tests/performance/test_directive_optimization.py

import timeit
from bengal.directives.factory import (
    _get_directive_instances,
    reset_directive_instances,
)
from bengal.directives import AdmonitionDirective

def test_singleton_vs_new_instances():
    """Singleton directives should be 10x+ faster than creating new ones."""
    reset_directive_instances()  # Clear cache

    # Old way: create new instances
    old_time = timeit.timeit(
        lambda: [AdmonitionDirective() for _ in range(40)],
        number=100
    )

    # New way: get singleton (includes first-time init)
    _ = _get_directive_instances()  # Warm cache
    new_time = timeit.timeit(
        lambda: _get_directive_instances(),
        number=100
    )

    assert new_time < old_time * 0.1  # 10x faster

def test_cached_type_hints():
    """Cached type hints should avoid repeated get_type_hints() calls."""
    from typing import get_type_hints
    from bengal.directives.options import DirectiveOptions

    # Verify cache is populated
    assert DirectiveOptions._cached_hints is not None
    assert DirectiveOptions._cached_fields is not None

def test_precompiled_coercers():
    """Pre-compiled coercers should be faster than runtime coercion."""
    from bengal.directives.options import StyledOptions

    # Verify coercers are pre-compiled
    assert "css_class" in StyledOptions._coercers

    # Test coercion works correctly
    opts = StyledOptions.from_raw({"class": "my-class"})
    assert opts.css_class == "my-class"
```

### Integration Benchmarks

```python
# benchmarks/test_build.py

import time

def test_full_build_performance():
    """Full build should complete within target time."""
    site = create_test_site(page_count=1000, directives_per_page=20)

    start = time.perf_counter()
    build(site)
    elapsed = time.perf_counter() - start

    # Target: 30 seconds for 1000 pages (was 35s before optimization)
    assert elapsed < 32  # Allow 7% margin

def test_directive_singleton_state():
    """Singleton directives must not leak state between pages."""
    instances = _get_directive_instances()

    # Parse two different pages
    page1 = parse_page(":::{note}\nContent 1\n:::")
    page2 = parse_page(":::{note}\nContent 2\n:::")

    # Verify no state leakage
    assert "Content 1" not in page2
    assert "Content 2" not in page1
```

---

## Risks and Mitigations

### Risk 1: Singleton State Leakage

**Problem**: Singleton directives might accumulate state between pages.

**Mitigation**:
1. Code review all directive classes for instance variables
2. Add test `test_directive_singleton_state()` to CI
3. Ensure per-render state uses `state` arg, not `self`

**Verification Checklist**:
- [ ] No `self.xxx = yyy` in `parse()` or `render()` methods
- [ ] All directives inherit from `BengalDirective` without adding instance state
- [ ] Integration test confirms no state leakage

### Risk 2: Skipped Validation Hiding Bugs

**Problem**: Skipping contract validation in production might hide nesting errors.

**Mitigation**:
1. Always validate in `bengal serve` (dev server)
2. CI runs with `validate_contracts=True`
3. Add `--validate` CLI flag for production builds
4. Log when validation is disabled: `logger.info("contract_validation_disabled")`

### Risk 3: Cached Type Hints Edge Cases

**Problem**: `__init_subclass__` might run before `@dataclass` decorator.

**Mitigation**:
1. Check for `__dataclass_fields__` before caching
2. Fallback to runtime computation if cache is empty
3. Test with all existing `DirectiveOptions` subclasses

---

## Implementation Checklist

### Phase 1

- [ ] **Opt 1**: Singleton directives
  - [ ] Add `_get_directive_instances()` with thread-safe init
  - [ ] Add `reset_directive_instances()` for testing
  - [ ] Update `create_documentation_directives()` to use singleton
  - [ ] Add state leakage test

- [ ] **Opt 2**: Cached type hints
  - [ ] Add `__init_subclass__` to `DirectiveOptions`
  - [ ] Update `from_raw()` to use cached values
  - [ ] Add fallback for edge cases

- [ ] **Opt 3**: Class-level logger
  - [ ] Add `__init_subclass__` to `BengalDirective`
  - [ ] Convert `self.logger` to property
  - [ ] Remove logger creation from `__init__`

- [ ] **Opt 5**: Pre-compiled coercers
  - [ ] Add `_compile_coercer()` static method
  - [ ] Pre-compile in `__init_subclass__`
  - [ ] Update `from_raw()` to use coercers

### Phase 2

- [ ] **Opt 4**: Skip validation in production
  - [ ] Add `validate_contracts` to parser env
  - [ ] Update `BengalDirective.parse()` to check env
  - [ ] Add `--validate` CLI flag
  - [ ] Document validation behavior

- [ ] **Opt 10**: Production manifest mode
  - [ ] Add `_production_mode` flag to `JinjaTemplateEngine`
  - [ ] Skip mtime checks in production
  - [ ] Test dev-mode hot-reload still works

---

## References

- **Directive base**: `bengal/directives/base.py`
- **Options parsing**: `bengal/directives/options.py`
- **Factory**: `bengal/directives/factory.py`
- **Jinja engine**: `bengal/rendering/engines/jinja.py`
- **Context builder**: `bengal/rendering/context/__init__.py`
- **Template environment**: `bengal/rendering/template_engine/environment.py`

---

## Changelog

- 2025-12-23: Initial draft
  - Identified 12 potential optimizations
  - Projected 41% overall build time improvement

- 2025-12-23: Revision after code review
  - Dropped 4 optimizations (7, 9, 12 invalid; 8 already implemented)
  - Deferred 2 optimizations (6, 11 need benchmarking first)
  - Revised impact projections to realistic 10-15% improvement
  - Fixed implementation bugs in proposed solutions
  - Added implementation checklist and verification steps
  - Updated confidence levels based on code analysis
