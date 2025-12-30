# RFC: Code Quality Improvements

**Status**: Draft  
**Created**: 2025-12-30  
**Updated**: 2025-12-30  
**Author**: AI Assistant  
**Priority**: Medium  
**Affects**: `bengal/content_types/`, `bengal/rendering/`, `bengal/core/`

---

## Executive Summary

This RFC addresses code quality issues identified outside of caching systems. The focus is on reducing code duplication, improving abstractions, and establishing cleaner patterns for common operations.

**Key Issues**:
1. `template_exists` helper duplicated 5 times despite being a protocol method
2. Engine-specific checks scattered across codebase instead of using feature detection
3. Direct config/metadata access (400+ calls) instead of typed accessors
4. Duplicated pattern detection logic across content type strategies

**Proposed Solutions**: Centralize common patterns, use protocol methods, add feature detection capabilities.

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

**Each copy is identical**:
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

**Root Cause**: The inline helpers don't use the protocol method, likely because:
1. They handle `template_engine is None` case
2. They add debug logging on failure
3. Original author may not have known about protocol method

---

### Issue 2: Scattered Engine-Specific Checks

Manual engine type checks appear in multiple files:

```python
# orchestration/render.py:174
template_engine = self.site.config.get("template_engine", "jinja2")
if template_engine != "kida":
    return

# orchestration/build/rendering.py:319
template_engine = orchestrator.site.config.get("template_engine", "jinja2")
if template_engine != "kida":
    return

# server/build_trigger.py:735
engine_type = self.site.config.get("template_engine", "kida")
if engine_type != "kida":
    return False  # Only Kida supports block-level detection
```

**Problems**:
1. Magic strings (`"kida"`, `"jinja2"`) scattered across codebase
2. Feature availability tied to engine name, not capability query
3. Default engine inconsistent (`"jinja2"` vs `"kida"` in different places)
4. Adding a new engine requires finding all these checks

---

### Issue 3: Direct Config Access Everywhere

**183 calls** to `site.config.get()` across 84 files.

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

---

### Issue 4: Direct Metadata Access

**263 calls** to `.metadata.get()` across 81 files.

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
| `template_exists` duplicated 5 times | ✅ Verified | grep found 5 inline definitions |
| Protocol has `template_exists` method | ✅ Verified | `rendering/engines/protocol.py:139` |
| Engine checks scattered | ✅ Verified | Found in `render.py`, `rendering.py`, `build_trigger.py` |
| 183 config.get() calls | ✅ Verified | grep count across 84 files |
| 263 metadata.get() calls | ✅ Verified | grep count across 81 files |

---

## Proposed Solutions

### Fix 1: Use Protocol Method for Template Existence

**Remove inline helpers, use protocol method with null-safe wrapper**:

```python
# rendering/engines/utils.py (NEW)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

def safe_template_exists(
    template_engine: TemplateEngineProtocol | None,
    name: str,
) -> bool:
    """
    Check if template exists with null-safety and logging.
    
    Centralizes the common pattern of checking template existence
    with graceful handling of missing engine.
    
    Args:
        template_engine: Template engine (may be None)
        name: Template name to check
    
    Returns:
        True if template exists, False otherwise
    """
    if template_engine is None:
        return False
    
    return template_engine.template_exists(name)
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

---

### Fix 2: Engine Feature Detection

**Add capabilities to engine protocol**:

```python
# rendering/engines/protocol.py (ENHANCED)
from enum import Flag, auto

class EngineCapability(Flag):
    """Capabilities that template engines may support."""
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

---

### Fix 3: Typed Config Access (Long-term)

**Add typed config wrapper**:

```python
# config/typed.py (NEW)
from dataclasses import dataclass
from typing import Any

@dataclass
class BuildConfig:
    """Typed access to build configuration."""
    max_workers: int | None = None
    parallel: bool = True
    incremental: bool | None = None  # None = auto
    complexity_ordering: bool = True
    directive_cache: bool | None = None  # None = auto

@dataclass 
class SiteConfig:
    """Typed access to site configuration."""
    title: str = ""
    baseurl: str = "/"
    template_engine: str = "kida"
    # ... more fields
    
    build: BuildConfig = field(default_factory=BuildConfig)
    
    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> SiteConfig:
        """Create typed config from raw dict."""
        build_dict = config.get("build", {}) or {}
        return cls(
            title=config.get("title", ""),
            baseurl=config.get("baseurl", "/"),
            template_engine=config.get("template_engine", "kida"),
            build=BuildConfig(
                max_workers=build_dict.get("max_workers"),
                parallel=build_dict.get("parallel", True),
                # ...
            ),
        )
```

**Usage**:
```python
# Before
max_workers = self.site.config.get("max_workers")
engine = site.config.get("template_engine", "kida")

# After (with IDE completion and type safety)
max_workers = self.site.typed_config.build.max_workers
engine = self.site.typed_config.template_engine
```

**Note**: This is a larger refactor. Recommend implementing in phases:
1. Add `typed_config` property to Site
2. Migrate new code to use it
3. Gradually migrate existing code

---

### Fix 4: Internal Metadata Keys Convention

**Formalize the `_` prefix convention**:

```python
# core/page/metadata.py (ENHANCED)

class PageMetadataMixin:
    """Mixin providing metadata access."""
    
    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get user-defined frontmatter value.
        
        Does NOT return internal keys (prefixed with `_`).
        """
        if key.startswith("_"):
            return default
        return self.metadata.get(key, default)
    
    def get_internal_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get internal metadata value.
        
        Only returns keys prefixed with `_`.
        """
        if not key.startswith("_"):
            key = f"_{key}"
        return self.metadata.get(key, default)
    
    @property
    def is_generated(self) -> bool:
        """Whether page was dynamically generated."""
        return bool(self.metadata.get("_generated"))
    
    @property
    def assigned_template(self) -> str | None:
        """Template explicitly assigned to this page."""
        return self.metadata.get("template")
```

---

### Fix 5: Content Type Template Cascade

**Extract common template cascade logic**:

```python
# content_types/templates.py (NEW)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.engines.protocol import TemplateEngineProtocol

def resolve_template_cascade(
    candidates: list[str],
    template_engine: TemplateEngineProtocol | None,
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
        return fallback
    
    for candidate in candidates:
        if template_engine.template_exists(candidate):
            return candidate
    
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

## Implementation Plan

### Phase 1: Quick Wins (Week 1)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Add `safe_template_exists()` | `rendering/engines/utils.py` | Low | Reduces duplication |
| Remove 5 inline helpers | `content_types/*.py` | Low | Cleaner code |
| Add `resolve_template_cascade()` | `content_types/templates.py` | Low | Better abstraction |

### Phase 2: Feature Detection (Week 2)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Add `EngineCapability` enum | `rendering/engines/protocol.py` | Low | Enables detection |
| Implement in KidaTemplateEngine | `rendering/engines/kida.py` | Low | Feature parity |
| Implement in JinjaTemplateEngine | `rendering/engines/jinja.py` | Low | Feature parity |
| Migrate engine checks | Multiple | Medium | Cleaner architecture |

### Phase 3: Metadata Conventions (Week 3)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Add `get_user_metadata()` | `core/page/metadata.py` | Low | Better API |
| Add `get_internal_metadata()` | `core/page/metadata.py` | Low | Better API |
| Add convenience properties | `core/page/metadata.py` | Low | Cleaner code |
| Document conventions | `docs/` | Low | Better DX |

### Phase 4: Typed Config (Week 4+)

| Task | File | Risk | Impact |
|------|------|------|--------|
| Create `SiteConfig` dataclass | `config/typed.py` | Medium | Type safety |
| Add `typed_config` property | `core/site/core.py` | Medium | Gradual migration |
| Migrate critical paths | Multiple | Medium | Type safety |

---

## Success Criteria

### Code Quality

1. **No duplicate helpers**: `template_exists` defined in one place
2. **No magic strings**: Engine names in constants/enums
3. **Feature detection**: Engine capabilities queried, not assumed
4. **Clear conventions**: Internal vs user metadata separated

### Metrics

| Metric | Before | Target |
|--------|--------|--------|
| `template_exists` definitions | 5 | 1 |
| Engine name string literals | 10+ | 2 (factory + config) |
| Direct `.env.get_template()` calls | 5 | 0 |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code | Medium | Medium | Gradual migration, backward compat |
| Performance regression | Low | Low | Benchmark hot paths |
| Incomplete migration | Medium | Low | Track via grep patterns |

---

## Open Questions

1. **Typed config granularity**: Should we type all config, or just commonly-accessed sections?
   - **Recommendation**: Start with `build`, `site`, `autodoc` - the most accessed.

2. **Capability enum vs methods**: Should capabilities be an enum or individual `can_*()` methods?
   - **Recommendation**: Enum (composable, extensible, single property).

3. **Backward compatibility for metadata access**: Should we deprecate direct `.metadata` access?
   - **Recommendation**: No - too invasive. Add new methods, document preference.

---

## References

- `bengal/rendering/engines/protocol.py`: Template engine protocol
- `bengal/content_types/strategies.py`: Content type strategies with duplication
- `bengal/content_types/base.py`: Base strategy class

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-30 | Initial draft |

