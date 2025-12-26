# RFC: Engine-Agnostic Template Context Layer

**Status**: Implemented  
**Created**: 2025-12-26  
**Revised**: 2025-12-26  
**Implemented**: 2025-12-26  
**Priority**: High  
**Scope**: `bengal/rendering/`

---

## Executive Summary

Bengal currently duplicates template context setup across template engines (Jinja2, Kida). This leads to:

- Missing globals when adding new engines
- Inconsistent wrapper usage
- Maintenance burden when adding new context variables

This RFC proposes extending the existing `_get_global_contexts()` infrastructure in `bengal/rendering/context/` with a new public `get_engine_globals()` function that all engines consume, ensuring identical template access patterns regardless of engine choice.

---

## Problem Statement

### Current Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                           Bengal Core                                │
│  ┌──────────┐   ┌──────────┐   ┌───────────────┐   ┌─────────────┐ │
│  │   Site   │   │  Config  │   │  ThemeConfig  │   │  Metadata   │ │
│  └────┬─────┘   └────┬─────┘   └───────┬───────┘   └──────┬──────┘ │
└───────┼──────────────┼─────────────────┼──────────────────┼─────────┘
        │              │                 │                  │
        ▼              ▼                 ▼                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Jinja Environment (environment.py:413-446)                           │
│                                                                        │
│   env.globals["site"] = SiteContext(site)           ✅ Wrapper        │
│   env.globals["config"] = ConfigContext(config)     ✅ Wrapper        │
│   env.globals["theme"] = ThemeContext(theme)        ✅ Wrapper        │
│   env.globals["bengal"] = build_template_metadata() ✅                │
│   env.globals["versions"] = site.versions           ✅                │
│   env.globals["versioning_enabled"] = ...           ✅                │
│   env.globals["url_for"] = ...                      ✅ Engine-specific│
│   env.globals["get_menu"] = ...                     ✅ Engine-specific│
│   env.globals["getattr"] = getattr                  ✅                │
│   + ~15 more globals                                                   │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ Kida Engine (kida.py:165-219)                                         │
│                                                                        │
│   env.globals["site"] = SiteContext(site)           ✅ Wrapper        │
│   env.globals["config"] = ConfigContext(config)     ✅ Wrapper        │
│   env.globals["theme"] = ThemeContext(theme)        ✅ Wrapper        │
│   env.globals["_raw_site"] = site                   ✅                │
│   env.globals["bengal"] = build_template_metadata() ✅                │
│   env.globals["versions"] = site.versions           ✅                │
│   env.globals["versioning_enabled"] = ...           ✅                │
│   env.globals["url_for"] = ...                      ✅ Engine-specific│
│   env.globals["get_menu"] = ...                     ✅ Engine-specific│
│   env.globals["getattr"] = getattr                  ✅                │
└───────────────────────────────────────────────────────────────────────┘
```

### Issues

| Issue | Impact | Example |
| :--- | :--- | :--- |
| **Duplication** | ~35-40 lines per engine | `environment.py:413-446` vs `kida.py:165-219` |
| **Drift** | Engines get out of sync | Kida was missing `bengal`, `versions`, and wrappers until recently. |
| **Onboarding** | High friction for new engines | Future engines (Mako, Liquid) must manually implement Bengal's "ergonomic defaults" (Wrappers). |
| **Testing** | Fragmentation | No single place to verify that `site.title` fallbacks to `""` across all engines. |
| **Bugs** | Environment inconsistencies | Missing `bengal` metadata in Kida caused 1302 page build failures in late 2025. |

### Root Cause

Context setup is currently an **engine implementation detail** rather than a **core rendering service**. This violates the Principle of Least Surprise for theme developers who expect identical global variables regardless of the engine.

---

## Related Work

Bengal already has the building blocks for context management in `bengal/rendering/context/__init__.py`, but they are currently scoped to **per-page rendering** rather than **engine initialization**.

```python
# Existing: _get_global_contexts() (private, for per-page context)
def _get_global_contexts(site: Site) -> dict[str, Any]:
    """Get cached global context wrappers (site, config, theme, menus)."""
    # ... uses a thread-safe cache to avoid redundant allocations
    return {
        "site": SiteContext(site),
        "config": ConfigContext(site.config),
        "theme": ThemeContext(theme_obj) if theme_obj else ThemeContext._empty(),
        "menus": MenusContext(site),
    }
```

**The Gap**:

- `_get_global_contexts()` is private and only used by `build_page_context()`.
- It lacks certain "static" globals needed by engines like `getattr`, `_raw_site`, and `bengal` metadata.
- Engines are currently forced to "re-invent" the initialization of these wrappers.

---

## Proposed Solution

### Design: Extend Existing Infrastructure

We will promote the existing private infrastructure to a public API. This ensures that the logic used to build per-page context and the logic used to initialize engines stays perfectly synchronized.

```python
# bengal/rendering/context/__init__.py

def get_engine_globals(site: Site) -> dict[str, Any]:
    """
    Get all engine-agnostic globals for template engine initialization.

    This is the SINGLE SOURCE OF TRUTH for engine globals.
    Use this in Jinja, Kida, and any future engines.

    Implementation Notes:
    - Cached and thread-safe via _get_global_contexts().
    - Uses local imports for metadata to prevent circular dependencies.
    """
    # Reuse existing cached contexts (site, config, theme, menus)
    # This leverages the existing id(site) cache for performance.
    contexts = _get_global_contexts(site)

    # Build metadata with fallback (Local import prevents circularity)
    try:
        from bengal.utils.metadata import build_template_metadata
        bengal_metadata = build_template_metadata(site)
    except Exception:
        bengal_metadata = {"engine": {"name": "Bengal SSG", "version": "unknown"}}

    return {
        # Core context wrappers (from existing cache)
        **contexts,

        # Raw site for internal template functions
        "_raw_site": site,

        # Metadata for templates/JS
        "bengal": bengal_metadata,

        # Versioning
        "versioning_enabled": site.versioning_enabled,
        "versions": site.versions,

        # Python builtin useful in templates
        "getattr": getattr,
    }
```

### Engine Integration

Each engine becomes much simpler:

```python
# bengal/rendering/engines/kida.py (after refactor)

from bengal.rendering.context import get_engine_globals

class KidaTemplateEngine:
    def __init__(self, site: Site, *, profile: bool = False):
        self.site = site
        self._env = Environment(...)

        # One-line shared context setup!
        self._env.globals.update(get_engine_globals(site))

        # Engine-specific additions only
        self._env.globals["url_for"] = self._url_for
        self._env.globals["get_menu"] = self._get_menu
        self._env.globals["get_menu_lang"] = self._get_menu_lang
        # ... other Kida-specific setup
```

```python
# bengal/rendering/template_engine/environment.py (after refactor)

from bengal.rendering.context import get_engine_globals

def create_jinja_environment(site, template_engine, profile):
    env = Environment(...)

    # One-line shared context setup!
    env.globals.update(get_engine_globals(site))

    # Jinja-specific additions
    env.globals["url_for"] = template_engine._url_for
    env.globals["get_menu"] = template_engine._get_menu
    env.globals["get_menu_lang"] = template_engine._get_menu_lang
    # ... other Jinja-specific setup (extensions, profiling, etc.)

    return env
```

---

## Implementation Plan

### Phase 1: Infrastructure (Day 1)

**Target**: `bengal/rendering/context/__init__.py`

- [ ] Implement `get_engine_globals(site: Site)` function.
- [ ] Add `get_engine_globals` to `__all__`.
- [ ] **Test**: Create `tests/rendering/context/test_engine_globals.py` and verify all keys are present.

### Phase 2: Engine Refactor (Day 1)

**Target 1**: `bengal/rendering/template_engine/environment.py` (Jinja2)

- [ ] Remove lines 413-446 (manual globals setup).
- [ ] Replace with `env.globals.update(get_engine_globals(site))`.
- [ ] Verify `url_for`, `get_menu`, and `get_menu_lang` remain as engine-specific.

**Target 2**: `bengal/rendering/engines/kida.py` (Kida)

- [ ] Remove lines 165-178 and 211-219 (manual globals setup).
- [ ] Replace with `self._env.globals.update(get_engine_globals(site))`.
- [ ] Ensure `_register_bengal_template_functions` is simplified but preserves engine-specific filters.

### Phase 3: Validation (Day 2)

- [ ] **Parity Test**: `tests/rendering/test_engine_context_parity.py`.
- [ ] **Build Test**: Run `bengal build` on `example-sites/milos-blog/` using both `--engine jinja` and `--engine kida`.

---

## Security & Privacy Considerations

### 1. Information Exposure

By centralizing context, we ensure that the `expose_metadata` setting (minimal/standard/extended) is applied consistently across all engines via `build_template_metadata`. This prevents an engine from accidentally leaking rendering details (like specific library versions) in "minimal" mode.

### 2. Data Sanitization

All globals provided via `get_engine_globals` use Bengal's "Smart Wrappers" (`SiteContext`, `ConfigContext`, etc.). These wrappers are designed to:

- Prevent templates from accessing private `_` methods/attributes of the underlying objects.
- Return safe defaults (like empty strings) instead of `None` or raising errors, reducing the risk of XSS through unhandled `None` types in some engines.

### 3. Raw Site Access

The `_raw_site` global remains available for internal template functions but is prefixed with an underscore to discourage theme developers from using it directly. We should continue to move commonly requested data into the safe `SiteContext` wrapper.

---

## API Design

### Function Signature

```python
def get_engine_globals(site: Site) -> dict[str, Any]:
    """
    Get all engine-agnostic globals for template engine initialization.

    Cached and thread-safe.
    """
```

### Usage Pattern

```python
# Standard pattern for any template engine
from bengal.rendering.context import get_engine_globals

env.globals.update(get_engine_globals(site))

# Engine-specific additions
env.globals["url_for"] = self._url_for
env.globals["get_menu"] = self._get_menu
```

---

## Context Variables Reference

### Shared Globals (from `get_engine_globals()`)

| Variable | Type | Description |
| :--- | :--- | :--- |
| `site` | `SiteContext` | Wrapped site with safe access |
| `config` | `ConfigContext` | Wrapped config with safe access |
| `theme` | `ThemeContext` | Wrapped theme with `has()` method |
| `menus` | `MenusContext` | Menu access helper |
| `_raw_site` | `Site` | Raw site for internal use |
| `bengal` | `dict` | Metadata (capabilities, engine info) |
| `versioning_enabled` | `bool` | Whether versioning is active |
| `versions` | `list` | Available versions |
| `getattr` | `builtin` | Python's getattr for templates |

### Engine-Specific Globals (added by each engine)

| Variable | Owner | Description |
| :--- | :--- | :--- |
| `url_for` | Engine | URL generation (needs engine context) |
| `get_menu` | Engine | Menu retrieval (needs engine caching) |
| `get_menu_lang` | Engine | Language-specific menu |
| `breadcrumbs` | Engine | Breadcrumb generation |

---

## Testing Strategy

### Unit Tests

```python
# tests/rendering/context/test_engine_globals.py

class TestGetEngineGlobals:
    def test_includes_site_context(self, mock_site):
        globals = get_engine_globals(mock_site)
        assert isinstance(globals["site"], SiteContext)

    def test_includes_config_context(self, mock_site):
        globals = get_engine_globals(mock_site)
        assert isinstance(globals["config"], ConfigContext)

    def test_includes_theme_context(self, mock_site):
        globals = get_engine_globals(mock_site)
        assert isinstance(globals["theme"], ThemeContext)

    def test_includes_bengal_metadata(self, mock_site):
        globals = get_engine_globals(mock_site)
        assert "bengal" in globals

    def test_includes_versioning(self, mock_site):
        globals = get_engine_globals(mock_site)
        assert "versioning_enabled" in globals
        assert "versions" in globals

    def test_includes_raw_site(self, mock_site):
        globals = get_engine_globals(mock_site)
        assert globals["_raw_site"] is mock_site
```

### Integration Tests

```python
# tests/rendering/test_engine_context_parity.py

class TestEngineParity:
    """Ensure Jinja and Kida get identical shared context."""

    def test_core_globals_match(self, site):
        jinja_engine = JinjaTemplateEngine(site)
        kida_engine = KidaTemplateEngine(site)

        jinja_globals = set(jinja_engine.env.globals.keys())
        kida_globals = set(kida_engine._env.globals.keys())

        # Core globals must be present in both
        core = {"site", "config", "theme", "bengal", "versions",
                "versioning_enabled", "getattr", "_raw_site"}
        assert core <= jinja_globals
        assert core <= kida_globals

    def test_wrapper_types_match(self, site):
        jinja_engine = JinjaTemplateEngine(site)
        kida_engine = KidaTemplateEngine(site)

        assert type(jinja_engine.env.globals["site"]) == type(kida_engine._env.globals["site"])
        assert type(jinja_engine.env.globals["config"]) == type(kida_engine._env.globals["config"])
        assert type(jinja_engine.env.globals["theme"]) == type(kida_engine._env.globals["theme"])
```

---

## Migration Guide

### For Engine Maintainers

**Before (duplicated setup):**

```python
class MyTemplateEngine:
    def __init__(self, site):
        self._env.globals["site"] = SiteContext(site)
        self._env.globals["config"] = ConfigContext(site.config)
        self._env.globals["theme"] = ThemeContext(site.theme_config)
        self._env.globals["bengal"] = build_template_metadata(site)
        self._env.globals["versioning_enabled"] = site.versioning_enabled
        self._env.globals["versions"] = site.versions
        self._env.globals["_raw_site"] = site
        self._env.globals["getattr"] = getattr
        # ... engine-specific stuff
```

**After (one line for shared, explicit for engine-specific):**

```python
from bengal.rendering.context import get_engine_globals

class MyTemplateEngine:
    def __init__(self, site):
        # Shared globals (one line!)
        self._env.globals.update(get_engine_globals(site))

        # Engine-specific only
        self._env.globals["url_for"] = self._url_for
        self._env.globals["get_menu"] = self._get_menu
```

### For Theme Developers

No changes required! Templates continue to work exactly the same.

### For Plugin Authors

If you're adding template globals, consider:

1. Adding to `get_engine_globals()` if it's engine-agnostic
2. Adding to the specific engine if it's engine-specific

---

## Benefits

| Benefit | Description |
| :--- | :--- |
| **Single Source of Truth** | One function defines all shared context variables |
| **Engine Parity** | Guaranteed identical shared context across engines |
| **Easier New Engines** | Adding Mako/Liquid/etc. becomes trivial |
| **Better Testing** | Test shared context once, not per-engine |
| **Reduced Bugs** | No more "forgot to add X to Kida" issues |
| **Cleaner Code** | ~30 fewer lines per engine |
| **Leverages Existing Infra** | Uses existing `_get_global_contexts()` caching |

---

## Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| Breaking changes | Additive change; engines can adopt incrementally |
| Performance | Reuses existing cache from `_get_global_contexts()` |
| Engine-specific needs | Engines add their own globals after the shared ones |
| Over-abstraction | It's just one function returning a dict — minimal abstraction |

---

## Success Criteria

- [ ] `get_engine_globals()` returns all shared globals
- [ ] Jinja uses `get_engine_globals()` (not inline setup)
- [ ] Kida uses `get_engine_globals()` (not inline setup)
- [ ] Full test suite passes
- [ ] Bengal site builds with both engines
- [ ] No more "missing variable" errors due to engine mismatch
- [ ] Parity test ensures engines stay in sync

---

## Future Considerations

### Plugin-Provided Context

```python
# Future: Allow plugins to register additional globals
_engine_global_extensions: list[Callable[[Site], dict[str, Any]]] = []

def register_engine_global(fn: Callable[[Site], dict[str, Any]]) -> None:
    """Allow plugins to add globals to all engines."""
    _engine_global_extensions.append(fn)

def get_engine_globals(site: Site) -> dict[str, Any]:
    result = _core_engine_globals(site)
    for ext in _engine_global_extensions:
        result.update(ext(site))
    return result
```

---

## References

- Issue: Kida missing `bengal` global causing 1302 page failures
- Existing: `bengal/rendering/context/__init__.py:_get_global_contexts()`
- Related: `bengal/rendering/context/site_wrappers.py`
- Related: `bengal/rendering/template_engine/environment.py`
- Related: `bengal/rendering/engines/kida.py`
- Protocol: `bengal/rendering/engines/protocol.py`

---

## Appendix: Current Globals Inventory

### From `environment.py` (Jinja)

```python
# Lines 413-446 — shared globals (will use get_engine_globals)
env.globals["site"] = SiteContext(site)
env.globals["config"] = ConfigContext(site.config)
env.globals["theme"] = ThemeContext(site.theme_config)
env.globals["_raw_site"] = site
env.globals["versioning_enabled"] = site.versioning_enabled
env.globals["versions"] = site.versions
env.globals["bengal"] = build_template_metadata(site)
env.globals["getattr"] = getattr

# Engine-specific (remain in environment.py)
env.globals["url_for"] = template_engine._url_for
env.globals["get_menu"] = template_engine._get_menu
env.globals["get_menu_lang"] = template_engine._get_menu_lang
```

### From `kida.py` (Kida)

```python
# Lines 165-219 — shared globals (will use get_engine_globals)
env.globals["site"] = SiteContext(self.site)
env.globals["config"] = ConfigContext(self.site.config)
env.globals["theme"] = ThemeContext(self.site.theme_config)
env.globals["_raw_site"] = self.site
env.globals["bengal"] = build_template_metadata(self.site)
env.globals["versioning_enabled"] = self.site.versioning_enabled
env.globals["versions"] = self.site.versions
env.globals["getattr"] = getattr

# Engine-specific (remain in kida.py)
env.globals["url_for"] = self._url_for
env.globals["get_menu"] = self._get_menu
env.globals["get_menu_lang"] = self._get_menu_lang
```

---

## Changelog

| Date | Change |
| :--- | :--- |
| 2025-12-26 | Initial draft |
| 2025-12-26 | Revised: Replace TemplateContext class with get_engine_globals() function; add Related Work section; fix linter/formatting issues |
| 2025-12-26 | Improved: Detailed Issue examples, circular import safeguards, file:line targets in implementation plan, and new Security section |
