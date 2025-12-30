# RFC: Code Quality Improvements

**Status**: Draft  
**Created**: 2025-12-30  
**Updated**: 2025-12-30  
**Author**: AI Assistant  
**Priority**: Medium  
**Affects**: `bengal/content_types/`, `bengal/rendering/`, `bengal/core/`, `bengal/orchestration/`

---

## Executive Summary

This RFC addresses code quality issues identified outside of caching systems. The focus is on reducing code duplication, improving abstractions, and establishing cleaner patterns for common operations.

**Key Issues**:
1. `template_exists` helper duplicated 5 times despite being a protocol method
2. Engine-specific checks scattered across 4+ locations instead of using feature detection
3. Direct config access (227+ calls) without type safety
4. Direct metadata access (265+ calls) without internal/user key separation
5. Duplicated template cascade logic across content type strategies

**Proposed Solutions**: Centralize common patterns, use protocol methods, add feature detection capabilities.

**Recommended Approach**: Implement in phases, starting with low-risk quick wins (Fixes 1 and 5).

---

## Problem Statement

### Issue 1: Duplicated `template_exists` Helper

The same helper function is copy-pasted in 5 locations:

| File | Line |
|------|------|
| `content_types/base.py` | 223 |
| `content_types/strategies.py` | 120 |
| `content_types/strategies.py` | 225 |
| `content_types/strategies.py` | 327 |
| `content_types/strategies.py` | 426 |

**Each copy is nearly identical**:
```python
def template_exists(name: str) -> bool:
    if template_engine is None:
        return False
    try:
        template_engine.env.get_template(name)
        return True
    except Exception as e:
        logger.debug(
            "template_check_failed",
            template=name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False
```

**Problem**: `template_exists()` is already defined on `TemplateEngineProtocol`:

```python
# rendering/engines/protocol.py:139
def template_exists(self, name: str) -> bool:
    """Check if a template exists."""
    ...
```

**Root Cause**: The inline helpers don't use the protocol method because:
1. They handle `template_engine is None` case
2. They add debug logging on failure
3. Original author may not have known about protocol method

**Note**: Both `KidaTemplateEngine` and `JinjaTemplateEngine` already implement this protocol method correctly.

---

### Issue 2: Scattered Engine-Specific Checks

Manual engine type checks appear in 4+ files:

| File | Line | Default | Comment |
|------|------|---------|---------|
| `orchestration/render.py` | 173-174 | `"jinja2"` | Block caching |
| `orchestration/build/rendering.py` | 318-319 | `"jinja2"` | Block caching |
| `server/build_trigger.py` | 735-736 | `"kida"` | Block-level detection |
| `orchestration/incremental/template_detector.py` | 393-394 | `"kida"` | Template introspection |

**Example patterns**:
```python
# orchestration/render.py:173-174
template_engine = self.site.config.get("template_engine", "jinja2")
if template_engine != "kida":
    return

# server/build_trigger.py:735-736
engine_type = self.site.config.get("template_engine", "kida")
if engine_type != "kida":
    return False  # Only Kida supports block-level detection

# orchestration/incremental/template_detector.py:393-394
engine_type = self.site.config.get("template_engine", "kida")
return engine_type == "kida"
```

**Problems**:
1. Magic strings (`"kida"`, `"jinja2"`) scattered across codebase
2. Feature availability tied to engine name, not capability query
3. Default engine inconsistent (`"jinja2"` vs `"kida"` in different places)
4. Adding a new engine requires finding and updating all these checks
5. No clear documentation of which features require which engine

---

### Issue 3: Direct Config Access Everywhere

**227+ calls** to `site.config.get()` across 90 files.

Examples:
```python
# Common pattern - repeated everywhere
max_workers = self.site.config.get("max_workers")
template_engine = site.config.get("template_engine", "kida")
autodoc_config = self.site.config.get("autodoc", {})
build_config = site.config.get("build", {}) or {}
```

**Problems**:
1. No type safety - returns `Any`
2. Default values inconsistent across call sites
3. No IDE completion for valid config keys
4. Typos in config keys fail silently

**Note**: Full typed config is a larger refactor. This RFC proposes a minimal foundation; comprehensive typing deferred to future RFC.

---

### Issue 4: Direct Metadata Access

**265+ calls** to `.metadata.get()` across 81 files.

Examples:
```python
# Accessing page frontmatter - no type safety
page.metadata.get("date")
page.metadata.get("_generated")
page.metadata.get("template")
section.metadata.get("content_type")
```

**Problems**:
1. Same as config access - no type safety
2. Internal keys (prefixed `_`) accessed alongside user keys
3. No distinction between user frontmatter and internal state

---

### Issue 5: Duplicated Content Type Logic

Content type strategies duplicate similar patterns:

1. **Template cascade logic** - each strategy has similar `get_template()` with fallback chains
2. **Section detection** - each strategy checks similar patterns for auto-detection
3. **Sorting logic** - some overlap between strategies

---

## Code Verification

| Claim | Status | Evidence |
|-------|--------|----------|
| `template_exists` duplicated 5 times | ✅ Verified | `base.py:223`, `strategies.py:120,225,327,426` |
| Protocol has `template_exists` method | ✅ Verified | `rendering/engines/protocol.py:139` |
| Kida implements protocol method | ✅ Verified | `rendering/engines/kida.py:384` |
| Jinja implements protocol method | ✅ Verified | `rendering/engines/jinja.py:225` |
| Engine checks scattered (4+ locations) | ✅ Verified | `render.py`, `rendering.py`, `build_trigger.py`, `template_detector.py` |
| Default engine inconsistent | ✅ Verified | `"jinja2"` in render.py, `"kida"` in build_trigger.py |
| 227+ config.get() calls | ✅ Verified | grep count across 90 files |
| 265+ metadata.get() calls | ✅ Verified | grep count across 81 files |

---

## Proposed Solutions

### Fix 1: Use Protocol Method for Template Existence

**Remove inline helpers, use protocol method with null-safe wrapper**:

```python
# rendering/engines/utils.py (NEW)
import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

logger = structlog.get_logger()

def safe_template_exists(
    template_engine: "TemplateEngineProtocol | None",
    name: str,
    *,
    log_failures: bool = False,
) -> bool:
    """
    Check if template exists with null-safety and optional logging.

    Centralizes the common pattern of checking template existence
    with graceful handling of missing engine.

    Args:
        template_engine: Template engine (may be None)
        name: Template name to check
        log_failures: If True, log debug message when template not found

    Returns:
        True if template exists, False otherwise

    Example:
        if safe_template_exists(engine, "blog/home.html"):
            return "blog/home.html"
    """
    if template_engine is None:
        return False

    result = template_engine.template_exists(name)

    if not result and log_failures:
        logger.debug(
            "template_check_failed",
            template=name,
            engine=type(template_engine).__name__,
        )

    return result
```

**Migration**:
```python
# Before (duplicated in 5 places)
def template_exists(name: str) -> bool:
    if template_engine is None:
        return False
    try:
        template_engine.env.get_template(name)
        return True
    except Exception:
        return False

# After (single import)
from bengal.rendering.engines.utils import safe_template_exists

if safe_template_exists(template_engine, "blog/home.html"):
    return "blog/home.html"
```

**Why this approach**:
- Preserves null-safety behavior from inline helpers
- Optional logging maintains debug capability without overhead
- Delegates to protocol method (already tested in both engines)
- Single source of truth

---

### Fix 2: Engine Feature Detection

**Add capabilities to engine protocol**:

```python
# rendering/engines/protocol.py (ENHANCED)
from enum import Flag, auto

class EngineCapability(Flag):
    """
    Capabilities that template engines may support.

    Using Flag enum allows:
    - Composable capabilities (BLOCK_CACHING | INTROSPECTION)
    - Single property on engine (vs multiple can_* methods)
    - Easy extensibility (add new capabilities without API change)
    - Type-safe capability checks

    Alternative considered: Individual `can_cache_blocks()`, `can_introspect()`
    methods. Rejected because:
    - Requires protocol changes for each new capability
    - More verbose engine implementations
    - Harder to query "what can this engine do?"
    """
    NONE = 0
    BLOCK_CACHING = auto()          # Can cache rendered blocks
    BLOCK_LEVEL_DETECTION = auto()  # Can detect block-level changes
    INTROSPECTION = auto()          # Can analyze template structure
    PIPELINE_OPERATORS = auto()     # Supports |> operator
    PATTERN_MATCHING = auto()       # Supports match/case in templates

class TemplateEngineProtocol(Protocol):
    # ... existing methods ...

    @property
    def capabilities(self) -> EngineCapability:
        """Return engine capabilities for feature detection."""
        ...

    def has_capability(self, cap: EngineCapability) -> bool:
        """Check if engine has a specific capability."""
        return cap in self.capabilities
```

**Implementation for Kida**:
```python
# rendering/engines/kida.py
class KidaTemplateEngine:
    @property
    def capabilities(self) -> EngineCapability:
        return (
            EngineCapability.BLOCK_CACHING |
            EngineCapability.BLOCK_LEVEL_DETECTION |
            EngineCapability.INTROSPECTION |
            EngineCapability.PIPELINE_OPERATORS |
            EngineCapability.PATTERN_MATCHING
        )
```

**Implementation for Jinja2**:
```python
# rendering/engines/jinja.py
class JinjaTemplateEngine:
    @property
    def capabilities(self) -> EngineCapability:
        return EngineCapability.NONE  # No special capabilities
```

**Migration**:
```python
# Before (magic string comparison)
engine_type = self.site.config.get("template_engine", "kida")
if engine_type != "kida":
    return False

# After (capability check)
from bengal.rendering.engines.protocol import EngineCapability

if not engine.has_capability(EngineCapability.BLOCK_LEVEL_DETECTION):
    return False
```

**Migration table**:

| Current Check | Capability |
|---------------|------------|
| Block caching conditional | `BLOCK_CACHING` |
| Block-level change detection | `BLOCK_LEVEL_DETECTION` |
| Template introspection | `INTROSPECTION` |

---

### Fix 3: Metadata Access Conventions

**Formalize the `_` prefix convention**:

```python
# core/page/metadata.py (ENHANCED)
from typing import Any

class PageMetadataMixin:
    """Mixin providing metadata access with internal/user separation."""

    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get user-defined frontmatter value.

        Does NOT return internal keys (prefixed with `_`).
        Use for accessing author-provided frontmatter.
        """
        if key.startswith("_"):
            return default
        return self.metadata.get(key, default)

    def get_internal_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get internal metadata value.

        Only returns keys prefixed with `_`.
        Auto-prefixes key if not already prefixed.
        """
        if not key.startswith("_"):
            key = f"_{key}"
        return self.metadata.get(key, default)

    # Convenience properties for common internal keys
    @property
    def is_generated(self) -> bool:
        """Whether page was dynamically generated."""
        return bool(self.metadata.get("_generated"))

    @property
    def assigned_template(self) -> str | None:
        """Template explicitly assigned to this page."""
        return self.metadata.get("template")

    @property
    def content_type_name(self) -> str | None:
        """Content type assigned to this page."""
        return self.metadata.get("content_type")
```

**Note**: Direct `.metadata` access remains supported for backward compatibility. New code should prefer the typed accessors.

---

### Fix 4: Content Type Template Cascade

**Extract common template cascade logic**:

```python
# content_types/templates.py (NEW)
import structlog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

logger = structlog.get_logger()

def resolve_template_cascade(
    candidates: list[str],
    template_engine: "TemplateEngineProtocol | None",
    fallback: str = "single.html",
) -> str:
    """
    Resolve template from cascade of candidates.

    Tries each candidate in order, returning first that exists.
    Falls back to specified default if none exist.

    Args:
        candidates: Template names to try in order
        template_engine: Engine for existence checks
        fallback: Default template if none found

    Returns:
        First existing template or fallback

    Example:
        template = resolve_template_cascade(
            ["blog/home.html", "home.html", "index.html"],
            engine,
            fallback="index.html"
        )
    """
    if template_engine is None:
        logger.debug("template_cascade_no_engine", fallback=fallback)
        return fallback

    for candidate in candidates:
        if template_engine.template_exists(candidate):
            logger.debug(
                "template_cascade_resolved",
                template=candidate,
                candidates_tried=candidates[:candidates.index(candidate) + 1],
            )
            return candidate

    logger.debug(
        "template_cascade_fallback",
        candidates=candidates,
        fallback=fallback,
    )
    return fallback
```

**Usage in strategies**:
```python
# Before (inline in each strategy)
if template_exists("blog/home.html"):
    return "blog/home.html"
if template_exists("home.html"):
    return "home.html"
return "index.html"

# After
from bengal.content_types.templates import resolve_template_cascade

return resolve_template_cascade(
    ["blog/home.html", "home.html"],
    template_engine,
    fallback="index.html"
)
```

---

### Fix 5: Typed Config (Future RFC)

**Scope for this RFC**: Define the pattern only. Full implementation deferred.

The typed config solution requires migrating 227+ call sites. This RFC establishes the pattern; a dedicated RFC will handle comprehensive implementation.

**Pattern to establish**:
```python
# config/typed.py (PATTERN ONLY)
from dataclasses import dataclass, field
from typing import Any

@dataclass
class BuildConfig:
    """Typed access to build configuration."""
    max_workers: int | None = None
    parallel: bool = True
    incremental: bool | None = None

@dataclass
class TypedSiteConfig:
    """Typed access to site configuration."""
    title: str = ""
    baseurl: str = "/"
    template_engine: str = "kida"
    build: BuildConfig = field(default_factory=BuildConfig)

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "TypedSiteConfig":
        """Create typed config from raw dict."""
        # Implementation details in future RFC
        ...
```

**This RFC delivers**: Documentation of the pattern and `BuildConfig` dataclass only.
**Future RFC delivers**: Full `TypedSiteConfig`, Site integration, migration plan.

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 days)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Add `safe_template_exists()` | `rendering/engines/utils.py` | Low | Reduces duplication |
| Remove 5 inline helpers | `content_types/*.py` | Low | Cleaner code |
| Add `resolve_template_cascade()` | `content_types/templates.py` | Low | Better abstraction |
| Add tests for new utilities | `tests/unit/rendering/` | Low | Regression safety |

### Phase 2: Feature Detection (3-4 days)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Add `EngineCapability` enum | `rendering/engines/protocol.py` | Low | Enables detection |
| Implement in KidaTemplateEngine | `rendering/engines/kida.py` | Low | Feature parity |
| Implement in JinjaTemplateEngine | `rendering/engines/jinja.py` | Low | Feature parity |
| Migrate 4 engine checks | Multiple | Medium | Cleaner architecture |
| Add capability tests | `tests/unit/rendering/` | Low | Regression safety |

### Phase 3: Metadata Conventions (2-3 days)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Add `get_user_metadata()` | `core/page/metadata.py` | Low | Better API |
| Add `get_internal_metadata()` | `core/page/metadata.py` | Low | Better API |
| Add convenience properties | `core/page/metadata.py` | Low | Cleaner code |
| Document conventions | `docs/` | Low | Better DX |
| Migrate critical internal access | Selected files | Low | Demonstrate pattern |

---

## Validation Plan

### Automated Validation

**grep patterns to track progress**:

```bash
# Phase 1: Should decrease to 0
grep -r "def template_exists" bengal/content_types/ | wc -l

# Phase 2: Should decrease to 2 (factory + config default)
grep -r 'template_engine.*"kida"' bengal/ | grep -v test | wc -l
grep -r 'engine_type.*"kida"' bengal/ | grep -v test | wc -l

# Phase 2: Should increase (capability checks)
grep -r "has_capability" bengal/ | wc -l
```

### Test Coverage

| Component | Test File | Coverage Target |
|-----------|-----------|-----------------|
| `safe_template_exists` | `tests/unit/rendering/test_engine_utils.py` | 100% |
| `resolve_template_cascade` | `tests/unit/content_types/test_templates.py` | 100% |
| `EngineCapability` | `tests/unit/rendering/test_engine_protocol.py` | 100% |
| Metadata accessors | `tests/unit/core/test_page_metadata.py` | 100% |

### Integration Validation

```bash
# Full test suite must pass
pytest tests/ -x

# Build example sites
bengal build site/
bengal build example-sites/milos-blog/
```

---

## Success Criteria

### Code Quality

1. **No duplicate helpers**: `template_exists` defined in one place
2. **No magic strings**: Engine names in constants/enums
3. **Feature detection**: Engine capabilities queried, not assumed
4. **Clear conventions**: Internal vs user metadata separated

### Metrics

| Metric | Before | Target | Validation |
|--------|--------|--------|------------|
| `template_exists` definitions | 5 | 1 | `grep "def template_exists"` |
| Engine name string literals | 10+ | 2 (factory + config) | `grep '"kida"'` |
| Direct `.env.get_template()` calls | 5 | 0 | `grep "env.get_template"` |
| Capability checks | 0 | 4+ | `grep "has_capability"` |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code | Medium | Medium | Gradual migration, backward compat |
| Performance regression | Low | Low | Benchmark hot paths before/after |
| Incomplete migration | Medium | Low | Track via grep patterns |
| Capability enum grows unwieldy | Low | Low | Flag enum naturally handles composition |

---

## Decisions Made

### Why Flag enum for capabilities?

**Chosen**: `EngineCapability` Flag enum  
**Rejected**: Individual `can_*()` methods

**Rationale**:
1. **Composability**: `BLOCK_CACHING | INTROSPECTION` is natural
2. **Single property**: One `capabilities` property vs N methods
3. **Extensibility**: Add new capabilities without protocol changes
4. **Queryability**: Easy to ask "what can this engine do?"

### Why defer typed config?

**Chosen**: Pattern definition only; full implementation in future RFC  
**Rejected**: Full implementation in this RFC

**Rationale**:
1. **Scope control**: 227+ call sites is a large migration
2. **Risk isolation**: Separate concerns for easier review
3. **Incremental value**: Quick wins deliverable now

### Why keep direct `.metadata` access?

**Chosen**: Add new methods, keep old access  
**Rejected**: Deprecate direct access

**Rationale**:
1. **Backward compatibility**: 265+ call sites
2. **Migration burden**: Too invasive for this RFC
3. **Valid use cases**: Direct access still useful for dynamic keys

---

## Open Questions

1. **Capability discovery**: Should we add `list_capabilities()` or `describe_capabilities()` for tooling?
   - **Recommendation**: Not in initial implementation; add if tooling needs arise.

2. **Logging verbosity**: Should `safe_template_exists` log by default?
   - **Recommendation**: No - opt-in via `log_failures=True` to avoid noise.

---

## References

- `bengal/rendering/engines/protocol.py`: Template engine protocol
- `bengal/rendering/engines/kida.py`: Kida engine implementation
- `bengal/rendering/engines/jinja.py`: Jinja engine implementation
- `bengal/content_types/strategies.py`: Content type strategies with duplication
- `bengal/content_types/base.py`: Base strategy class
- `bengal/orchestration/incremental/template_detector.py`: Template detection with engine check

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-30 | Initial draft |
| 2025-12-30 | Added missing engine check location, updated counts, added validation plan, clarified scope |
