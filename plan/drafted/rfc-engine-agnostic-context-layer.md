# RFC: Engine-Agnostic Template Context Layer

**Status**: Draft  
**Created**: 2025-12-26  
**Priority**: High  
**Scope**: `bengal/rendering/`

---

## Executive Summary

Bengal currently duplicates template context setup across template engines (Jinja2, Kida). This leads to:
- Missing globals when adding new engines
- Inconsistent wrapper usage
- Maintenance burden when adding new context variables

This RFC proposes a unified `TemplateContext` layer that all engines consume, ensuring identical template access patterns regardless of engine choice.

---

## Problem Statement

### Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Bengal Core                                │
│  ┌──────────┐   ┌──────────┐   ┌───────────────┐   ┌─────────────┐ │
│  │   Site   │   │  Config  │   │  ThemeConfig  │   │  Metadata   │ │
│  └────┬─────┘   └────┬─────┘   └───────┬───────┘   └──────┬──────┘ │
└───────┼──────────────┼─────────────────┼──────────────────┼─────────┘
        │              │                 │                  │
        ▼              ▼                 ▼                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Jinja Environment (environment.py:378-446)                            │
│                                                                        │
│   env.globals["site"] = SiteContext(site)           ✅ Wrapper        │
│   env.globals["config"] = ConfigContext(config)     ✅ Wrapper        │
│   env.globals["theme"] = ThemeContext(theme)        ✅ Wrapper        │
│   env.globals["bengal"] = build_template_metadata() ✅                │
│   env.globals["versions"] = site.versions           ✅                │
│   env.globals["versioning_enabled"] = ...           ✅                │
│   env.globals["url_for"] = ...                      ✅                │
│   env.globals["get_menu"] = ...                     ✅                │
│   env.globals["getattr"] = getattr                  ✅                │
│   + ~15 more globals                                                   │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ Kida Engine (kida.py:158-218)                                         │
│                                                                        │
│   env.globals["site"] = SiteContext(site)           ✅ (after fix)    │
│   env.globals["config"] = ConfigContext(config)     ✅ (after fix)    │
│   env.globals["theme"] = ThemeContext(theme)        ✅ (after fix)    │
│   env.globals["bengal"] = build_template_metadata() ✅ (after fix)    │
│   env.globals["versions"] = site.versions           ✅ (after fix)    │
│   env.globals["versioning_enabled"] = ...           ✅ (after fix)    │
│   env.globals["url_for"] = ...                      ✅                │
│   env.globals["get_menu"] = ...                     ✅                │
│   env.globals["getattr"] = getattr                  ✅                │
│   ❓ Missing: _raw_site, other Jinja-specific globals?                │
└───────────────────────────────────────────────────────────────────────┘
```

### Issues

| Issue | Impact | Example |
|-------|--------|---------|
| **Duplication** | ~60 lines duplicated per engine | Each engine re-implements context setup |
| **Drift** | Engines get out of sync | Kida was missing `bengal`, `versions`, wrappers |
| **Onboarding** | New engines must copy-paste | Future engines (Mako, Liquid) face same issues |
| **Testing** | Must test context separately per engine | No single source of truth |
| **Bugs** | Easy to forget globals | 1302 pages failed due to missing `bengal` |

### Root Cause

Context setup is **embedded in engine implementations** instead of being a **shared, engine-agnostic service**.

---

## Proposed Solution

### Design: TemplateContext Factory

Create a centralized `TemplateContext` class that:
1. Prepares all context variables in one place
2. Applies appropriate wrappers (SiteContext, ConfigContext, etc.)
3. Returns a dict that any engine can consume

```python
# bengal/rendering/context/template_context.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from bengal.rendering.context.site_wrappers import (
    ConfigContext,
    SiteContext,
    ThemeContext,
)
from bengal.utils.metadata import build_template_metadata

if TYPE_CHECKING:
    from bengal.core.site import Site


class TemplateContext:
    """
    Engine-agnostic template context preparation.

    Provides a unified interface for preparing template globals that all
    template engines (Jinja2, Kida, future engines) can consume.

    Example:
        # In any template engine
        context = TemplateContext(site)
        env.globals.update(context.globals())
        env.filters.update(context.filters())
    """

    __slots__ = ("_site", "_globals_cache", "_filters_cache")

    def __init__(self, site: Site):
        self._site = site
        self._globals_cache: dict[str, Any] | None = None
        self._filters_cache: dict[str, Callable] | None = None

    def globals(self) -> dict[str, Any]:
        """
        Get all template globals.

        Returns a dict ready to merge into env.globals.
        Cached after first call for performance.
        """
        if self._globals_cache is not None:
            return self._globals_cache

        site = self._site

        # Core context objects (with safe wrappers)
        context: dict[str, Any] = {
            # Primary objects - wrapped for safe template access
            "site": SiteContext(site),
            "config": ConfigContext(site.config),
            "theme": (
                ThemeContext(site.theme_config)
                if site.theme_config
                else ThemeContext._empty()
            ),

            # Raw site for internal functions that need it
            "_raw_site": site,

            # Metadata for templates/JS
            "bengal": self._build_metadata(),

            # Versioning
            "versioning_enabled": site.versioning_enabled,
            "versions": site.versions,

            # Python builtins useful in templates
            "getattr": getattr,
            "len": len,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "sorted": sorted,
            "reversed": reversed,
            "dict": dict,
            "list": list,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }

        self._globals_cache = context
        return context

    def _build_metadata(self) -> dict[str, Any]:
        """Build bengal metadata with fallback."""
        try:
            return build_template_metadata(self._site)
        except Exception:
            return {"engine": {"name": "Bengal SSG", "version": "unknown"}}

    def filters(self) -> dict[str, Callable]:
        """
        Get common template filters.

        Note: Engine-specific filters (like Jinja's autoescape)
        should still be added by the engine.
        """
        if self._filters_cache is not None:
            return self._filters_cache

        from bengal.rendering.template_engine.url_helpers import filter_dateformat

        filters: dict[str, Callable] = {
            "dateformat": filter_dateformat,
            "date": filter_dateformat,
        }

        self._filters_cache = filters
        return filters

    @classmethod
    def for_engine(
        cls,
        site: Site,
        engine_type: str = "generic",
    ) -> "TemplateContext":
        """
        Factory method for engine-specific context.

        Args:
            site: Bengal Site instance
            engine_type: "jinja", "kida", or "generic"

        Returns:
            Configured TemplateContext instance
        """
        return cls(site)
```

### Engine Integration

Each engine becomes much simpler:

```python
# bengal/rendering/engines/kida.py (after refactor)

class KidaTemplateEngine:
    def __init__(self, site: Site, *, profile: bool = False):
        self.site = site
        self._env = Environment(...)

        # One-line context setup!
        context = TemplateContext(site)
        self._env.globals.update(context.globals())
        self._env.filters.update(context.filters())

        # Engine-specific additions
        self._register_kida_specific()
```

```python
# bengal/rendering/template_engine/environment.py (after refactor)

def create_jinja_environment(site, template_engine, profile):
    env = Environment(...)

    # One-line context setup!
    context = TemplateContext(site)
    env.globals.update(context.globals())
    env.filters.update(context.filters())

    # Jinja-specific additions (profiling, extensions, etc.)
    _register_jinja_specific(env, template_engine)

    return env
```

---

## Implementation Plan

### Phase 1: Create TemplateContext (Day 1)

```yaml
Files:
  - CREATE: bengal/rendering/context/template_context.py
  - CREATE: tests/rendering/context/test_template_context.py

Tasks:
  - [ ] Implement TemplateContext class
  - [ ] Extract all globals from environment.py into TemplateContext.globals()
  - [ ] Extract common filters into TemplateContext.filters()
  - [ ] Add comprehensive tests
```

### Phase 2: Refactor Jinja (Day 1-2)

```yaml
Files:
  - MODIFY: bengal/rendering/template_engine/environment.py

Tasks:
  - [ ] Replace inline globals with TemplateContext.globals()
  - [ ] Replace inline filters with TemplateContext.filters()
  - [ ] Keep Jinja-specific setup (extensions, profiling) separate
  - [ ] Run full test suite
  - [ ] Test site build
```

### Phase 3: Refactor Kida (Day 2)

```yaml
Files:
  - MODIFY: bengal/rendering/engines/kida.py

Tasks:
  - [ ] Replace inline globals with TemplateContext.globals()
  - [ ] Replace inline filters with TemplateContext.filters()
  - [ ] Keep Kida-specific setup (adapter functions) separate
  - [ ] Run Kida test suite
  - [ ] Test site build with template_engine: kida
```

### Phase 4: Documentation & Cleanup (Day 2-3)

```yaml
Tasks:
  - [ ] Update TemplateEngineProtocol documentation
  - [ ] Add "Adding a New Template Engine" guide
  - [ ] Remove duplicate code
  - [ ] Add deprecation warnings for direct globals access
```

---

## API Design

### TemplateContext

```python
class TemplateContext:
    """Engine-agnostic template context."""

    def __init__(self, site: Site): ...

    def globals(self) -> dict[str, Any]:
        """All template globals (cached)."""

    def filters(self) -> dict[str, Callable]:
        """Common template filters (cached)."""

    def tests(self) -> dict[str, Callable]:
        """Common template tests (cached)."""

    @classmethod
    def for_engine(cls, site: Site, engine_type: str) -> TemplateContext:
        """Factory with engine-specific configuration."""
```

### Usage Pattern

```python
# Standard pattern for any template engine
context = TemplateContext(site)

# Merge into engine's globals
env.globals.update(context.globals())
env.filters.update(context.filters())

# Engine-specific additions
env.globals["engine_specific_func"] = my_func
```

---

## Context Variables Reference

### Core Globals (from TemplateContext)

| Variable | Type | Description |
|----------|------|-------------|
| `site` | `SiteContext` | Wrapped site with safe access |
| `config` | `ConfigContext` | Wrapped config with safe access |
| `theme` | `ThemeContext` | Wrapped theme with `has()` method |
| `_raw_site` | `Site` | Raw site for internal use |
| `bengal` | `dict` | Metadata (capabilities, engine info) |
| `versioning_enabled` | `bool` | Whether versioning is active |
| `versions` | `list` | Available versions |
| `getattr` | `builtin` | Python's getattr for templates |

### Engine-Specific Globals

| Variable | Owner | Description |
|----------|-------|-------------|
| `url_for` | Engine | URL generation (needs engine context) |
| `get_menu` | Engine | Menu retrieval (needs engine caching) |
| `breadcrumbs` | Engine | Breadcrumb generation |

### Filters (from TemplateContext)

| Filter | Description |
|--------|-------------|
| `dateformat` | Format dates |
| `date` | Alias for dateformat |

### Engine-Specific Filters

| Filter | Owner | Description |
|--------|-------|-------------|
| `safe` | Jinja | Mark as safe HTML |
| `autoescape` | Jinja | Control escaping |
| (Kida has same via compatibility) | | |

---

## Testing Strategy

### Unit Tests

```python
# tests/rendering/context/test_template_context.py

class TestTemplateContext:
    def test_globals_includes_site_context(self, mock_site):
        ctx = TemplateContext(mock_site)
        assert isinstance(ctx.globals()["site"], SiteContext)

    def test_globals_includes_config_context(self, mock_site):
        ctx = TemplateContext(mock_site)
        assert isinstance(ctx.globals()["config"], ConfigContext)

    def test_globals_includes_theme_context(self, mock_site):
        ctx = TemplateContext(mock_site)
        assert isinstance(ctx.globals()["theme"], ThemeContext)

    def test_globals_includes_bengal_metadata(self, mock_site):
        ctx = TemplateContext(mock_site)
        assert "bengal" in ctx.globals()
        assert "capabilities" in ctx.globals()["bengal"]

    def test_globals_cached(self, mock_site):
        ctx = TemplateContext(mock_site)
        g1 = ctx.globals()
        g2 = ctx.globals()
        assert g1 is g2  # Same object, not recomputed

    def test_filters_includes_dateformat(self, mock_site):
        ctx = TemplateContext(mock_site)
        assert "dateformat" in ctx.filters()
```

### Integration Tests

```python
# tests/rendering/test_context_parity.py

class TestEngineParity:
    """Ensure Jinja and Kida get identical context."""

    def test_globals_match(self, site):
        jinja_engine = JinjaTemplateEngine(site)
        kida_engine = KidaTemplateEngine(site)

        jinja_globals = set(jinja_engine.env.globals.keys())
        kida_globals = set(kida_engine._env.globals.keys())

        # Core globals must match
        core = {"site", "config", "theme", "bengal", "versions", "getattr"}
        assert core <= jinja_globals
        assert core <= kida_globals

    def test_site_wrapper_type_matches(self, site):
        jinja_engine = JinjaTemplateEngine(site)
        kida_engine = KidaTemplateEngine(site)

        assert type(jinja_engine.env.globals["site"]) == type(kida_engine._env.globals["site"])
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
        # ... 20 more lines
```

**After (one line):**
```python
class MyTemplateEngine:
    def __init__(self, site):
        context = TemplateContext(site)
        self._env.globals.update(context.globals())
        self._env.filters.update(context.filters())
        # Add only engine-specific stuff
```

### For Theme Developers

No changes required! Templates continue to work exactly the same.

### For Plugin Authors

If you're adding template globals, consider:
1. Adding to `TemplateContext` if it's engine-agnostic
2. Adding to the specific engine if it's engine-specific

---

## Benefits

| Benefit | Description |
|---------|-------------|
| **Single Source of Truth** | One place to define all context variables |
| **Engine Parity** | Guaranteed identical context across engines |
| **Easier New Engines** | Adding Mako/Liquid/etc. becomes trivial |
| **Better Testing** | Test context once, not per-engine |
| **Reduced Bugs** | No more "forgot to add X to Kida" issues |
| **Cleaner Code** | ~60 fewer lines per engine |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking changes | Keep backward compatibility; deprecate, don't remove |
| Performance | Cache everything; single dict copy is fast |
| Engine-specific needs | Engines can still add their own globals after |
| Over-abstraction | Keep it simple; just a dict factory |

---

## Success Criteria

- [ ] `TemplateContext.globals()` returns all core globals
- [ ] Jinja uses `TemplateContext` (not inline setup)
- [ ] Kida uses `TemplateContext` (not inline setup)
- [ ] Full test suite passes
- [ ] Bengal site builds with both engines
- [ ] No more "missing variable" errors due to engine mismatch
- [ ] Documentation updated

---

## Future Considerations

### Extensibility

```python
# Future: Plugin-provided context
class TemplateContext:
    _extensions: list[Callable] = []

    @classmethod
    def register_extension(cls, fn: Callable[[Site], dict[str, Any]]):
        """Allow plugins to add globals."""
        cls._extensions.append(fn)

    def globals(self) -> dict[str, Any]:
        result = self._core_globals()
        for ext in self._extensions:
            result.update(ext(self._site))
        return result
```

### Engine-Specific Context

```python
# Future: Engine-aware context
context = TemplateContext.for_engine(site, engine_type="kida")
# Returns context optimized for Kida (e.g., async-ready functions)
```

---

## References

- Issue: Kida missing `bengal` global causing 1302 page failures
- Related: `bengal/rendering/context/site_wrappers.py`
- Related: `bengal/rendering/template_engine/environment.py`
- Related: `bengal/rendering/engines/kida.py`
- Protocol: `bengal/rendering/engines/protocol.py`

---

## Appendix: Current Globals Inventory

### From `environment.py` (Jinja)

```python
# Line 413-446
env.globals["site"] = SiteContext(site)
env.globals["config"] = ConfigContext(site.config)
env.globals["theme"] = ThemeContext(site.theme_config)
env.globals["_raw_site"] = site
env.globals["versioning_enabled"] = site.versioning_enabled
env.globals["versions"] = site.versions
env.globals["bengal"] = build_template_metadata(site)
env.globals["url_for"] = template_engine._url_for
env.globals["get_menu"] = template_engine._get_menu
env.globals["get_menu_lang"] = template_engine._get_menu_lang
env.globals["getattr"] = getattr
```

### From `kida.py` (Kida, after fixes)

```python
# Line 158-218
env.globals["site"] = SiteContext(self.site)
env.globals["config"] = ConfigContext(self.site.config)
env.globals["theme"] = ThemeContext(self.site.theme_config)
env.globals["bengal"] = build_template_metadata(self.site)
env.globals["versioning_enabled"] = self.site.versioning_enabled
env.globals["versions"] = self.site.versions
env.globals["url_for"] = self._url_for
env.globals["get_menu"] = self._get_menu
env.globals["get_menu_lang"] = self._get_menu_lang
env.globals["getattr"] = getattr
```

### Missing from Kida (not yet added)

```python
env.globals["_raw_site"] = site  # Internal use
```

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-26 | Initial draft |
