# RFC: Config Defaults Cleanup & Centralization

**Status**: ✅ Implemented (Phases 1-3)  
**Created**: 2025-12-02  
**Author**: AI Assistant  
**Related**: `plan/active/config-inventory.md`

---

## Executive Summary

Bengal's configuration system has grown organically, resulting in:
- **Duplicated defaults** across 12+ files
- **5 missing sections** in `KNOWN_SECTIONS` validation
- **Confusing naming** (flat vs nested keys)
- **Ambiguous bool/dict handling**
- **Misleading CLI flags** (`--verbose` secretly enables health checks)

This RFC proposes a phased cleanup to centralize defaults, standardize naming, and improve DX.

---

## Problem Statement

### 1. Scattered Defaults (High Priority)

`max_workers` is hard-coded to `4` in **6 different files**:

| File | Location | Default |
|------|----------|---------|
| `render.py:294` | `_render_parallel()` | 4 |
| `render.py:387` | `_render_parallel()` | 4 |
| `render.py:481` | `_render_parallel()` | 4 |
| `taxonomy.py:634` | `_render_tag_pages_parallel()` | 4 |
| `asset.py:253` | `process_assets()` | varies |
| `loader.py:393` | `_default_config()` | cpu_count-1 |

**Impact**: Users with 16-core machines get 4 workers unless they manually set `max_workers`.

### 2. Missing `KNOWN_SECTIONS`

These sections are used throughout the codebase but will trigger "unknown section" warnings:

```python
# Current KNOWN_SECTIONS (missing 5!)
KNOWN_SECTIONS = {
    "site", "build", "markdown", "features", "taxonomies",
    "menu", "params", "assets", "pagination", "dev",
    "output_formats", "health_check", "fonts", "theme",
}

# Missing (used in 30+ files):
# - "search"    (10+ usages)
# - "content"   (templates + new/config.py)
# - "autodoc"   (autodoc module)
# - "i18n"      (10+ usages)
# - "graph"     (special_pages.py)
```

### 3. Duplicate Naming Patterns

| Flat Key | Nested Key | Both Work? |
|----------|------------|------------|
| `minify_assets` | `assets.minify` | ✅ Yes |
| `optimize_assets` | `assets.optimize` | ✅ Yes |
| `fingerprint_assets` | `assets.fingerprint` | ✅ Yes |
| `generate_sitemap` | `features.sitemap` | ✅ Yes |
| `generate_rss` | `features.rss` | ✅ Yes |

**Impact**: Users don't know which to use. Documentation inconsistent.

### 4. Bool/Dict Config Ambiguity

```yaml
# These behave DIFFERENTLY during config merge:

# Option A: Bool
health_check: false

# Option B: Dict
health_check:
  enabled: false
  verbose: true

# If both exist in different files, dict WINS
# User expects bool to disable, but dict overrides it
```

### 5. Misleading CLI Flags

```bash
# User expects: "show verbose output"
bengal build --verbose

# Actually does: Enables THEME_DEV profile which:
# - Enables 7 health check validators
# - Enables metrics collection
# - Enables detailed build stats
# - Shows phase timing
```

---

## Proposed Solution

### Phase 1: Centralize Defaults (Week 1)

**Create `bengal/config/defaults.py`**:

```python
"""
Single source of truth for all Bengal configuration defaults.

All config access should use these defaults via get_default().
"""
from __future__ import annotations

import os
from typing import Any

# Auto-detect optimal worker count
_CPU_COUNT = os.cpu_count() or 4
DEFAULT_MAX_WORKERS = max(4, _CPU_COUNT - 1)

DEFAULTS: dict[str, Any] = {
    # Site
    "title": "Bengal Site",
    "baseurl": "",
    "description": "",
    "author": "",
    "language": "en",

    # Build
    "output_dir": "public",
    "content_dir": "content",
    "assets_dir": "assets",
    "templates_dir": "templates",
    "parallel": True,
    "incremental": True,
    "max_workers": None,  # None = auto-detect
    "pretty_urls": True,
    "minify_html": True,
    "strict_mode": False,
    "debug": False,
    "validate_build": True,
    "validate_links": True,
    "transform_links": True,
    "cache_templates": True,
    "fast_writes": False,
    "stable_section_references": True,
    "min_page_size": 1000,

    # HTML Output
    "html_output": {
        "mode": "minify",
        "remove_comments": True,
        "collapse_blank_lines": True,
    },

    # Assets
    "assets": {
        "minify": True,
        "optimize": True,
        "fingerprint": True,
        "pipeline": False,
    },

    # Theme
    "theme": {
        "name": "default",
        "default_appearance": "system",
        "default_palette": "",
        "features": [],
        "show_reading_time": True,
        "show_author": True,
        "show_prev_next": True,
        "show_children_default": True,
        "show_excerpts_default": True,
        "max_tags_display": 10,
        "popular_tags_count": 20,
    },

    # Content
    "content": {
        "default_type": "doc",
        "excerpt_length": 200,
        "summary_length": 160,
        "reading_speed": 200,
        "related_count": 5,
        "related_threshold": 0.25,
        "toc_depth": 4,
        "toc_min_headings": 2,
        "toc_style": "nested",
        "sort_pages_by": "weight",
        "sort_order": "asc",
    },

    # Search
    "search": {
        "enabled": True,
        "lunr": {
            "prebuilt": True,
            "min_query_length": 2,
            "max_results": 50,
            "preload": "smart",
        },
        "ui": {
            "modal": True,
            "recent_searches": 5,
            "placeholder": "Search documentation...",
        },
        "analytics": {
            "enabled": False,
            "event_endpoint": None,
        },
    },

    # Pagination
    "pagination": {
        "per_page": 10,
    },

    # Health Check
    "health_check": {
        "enabled": True,
        "verbose": False,
        "strict_mode": False,
        "orphan_threshold": 5,
        "super_hub_threshold": 50,
    },

    # Features
    "features": {
        "rss": True,
        "sitemap": True,
        "search": True,
        "json": True,
        "llm_txt": True,
        "syntax_highlighting": True,
    },

    # Graph
    "graph": {
        "enabled": True,
        "path": "/graph/",
    },

    # i18n
    "i18n": {
        "strategy": None,
        "default_language": "en",
        "default_in_subdir": False,
    },

    # Output Formats
    "output_formats": {
        "enabled": True,
        "per_page": ["json"],
        "site_wide": ["index_json"],
        "options": {
            "excerpt_length": 200,
            "json_indent": None,
            "llm_separator_width": 80,
            "include_full_content_in_index": False,
            "exclude_sections": [],
            "exclude_patterns": ["404.html", "search.html"],
        },
    },

    # Markdown
    "markdown": {
        "parser": "mistune",
        "toc_depth": "2-4",
    },
}


def get_default(key: str, nested_key: str | None = None) -> Any:
    """
    Get default value for a config key.

    Args:
        key: Top-level config key
        nested_key: Optional nested key (dot-separated)

    Returns:
        Default value or None if not found

    Example:
        >>> get_default("max_workers")
        None  # Auto-detect
        >>> get_default("content", "excerpt_length")
        200
        >>> get_default("search", "lunr.prebuilt")
        True
    """
    value = DEFAULTS.get(key)

    if nested_key is None:
        return value

    if not isinstance(value, dict):
        return None

    # Handle dot-separated nested keys
    parts = nested_key.split(".")
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)

    return value


def get_max_workers(config_value: int | None = None) -> int:
    """
    Resolve max_workers with auto-detection.

    Args:
        config_value: User-configured value (None = auto-detect)

    Returns:
        Resolved worker count
    """
    if config_value is None or config_value == 0:
        return DEFAULT_MAX_WORKERS
    return config_value
```

**Update all hardcoded defaults**:

```python
# Before (render.py:294)
max_workers = self.site.config.get("max_workers", 4)

# After
from bengal.config.defaults import get_max_workers
max_workers = get_max_workers(self.site.config.get("max_workers"))
```

---

### Phase 2: Fix KNOWN_SECTIONS (Week 1)

**Update `bengal/config/loader.py`**:

```python
KNOWN_SECTIONS = {
    # Core
    "site",
    "build",
    "theme",
    "params",

    # Content
    "content",
    "markdown",
    "taxonomies",

    # Features
    "features",
    "search",
    "graph",

    # Navigation
    "menu",
    "pagination",

    # Output
    "output_formats",
    "assets",

    # Development
    "dev",
    "health_check",

    # Integrations
    "fonts",
    "autodoc",
    "i18n",
}
```

---

### Phase 3: Standardize Naming (Week 2)

**Deprecate flat asset keys** with warnings:

```python
# bengal/config/deprecation.py
DEPRECATED_KEYS = {
    "minify_assets": ("assets", "minify"),
    "optimize_assets": ("assets", "optimize"),
    "fingerprint_assets": ("assets", "fingerprint"),
    "generate_sitemap": ("features", "sitemap"),
    "generate_rss": ("features", "rss"),
    "markdown_engine": ("markdown", "parser"),
}

def check_deprecated_keys(config: dict[str, Any]) -> None:
    """Warn about deprecated config keys."""
    for old_key, (section, new_key) in DEPRECATED_KEYS.items():
        if old_key in config:
            logger.warning(
                "config_key_deprecated",
                old_key=old_key,
                new_key=f"{section}.{new_key}",
                note=f"'{old_key}' is deprecated, use '{section}.{new_key}' instead",
            )
```

---

### Phase 4: Fix Bool/Dict Handling (Week 2)

**Standardize config merge behavior**:

```python
def normalize_bool_or_dict(value: bool | dict, key: str) -> dict:
    """
    Normalize config that can be bool or dict.

    bool → {"enabled": bool}
    dict → dict (with "enabled" default True if missing)
    """
    if isinstance(value, bool):
        return {"enabled": value}
    if isinstance(value, dict):
        if "enabled" not in value:
            value["enabled"] = True
        return value
    raise ConfigValidationError(f"'{key}' must be bool or dict, got {type(value)}")
```

**Apply to**: `health_check`, `search`, `graph`, `output_formats`

---

### Phase 5: Clarify CLI Flags (Week 3)

**Rename/add CLI flags**:

| Current | Proposed | Behavior |
|---------|----------|----------|
| `--verbose` | `--theme-dev` | THEME_DEV profile |
| (new) | `--verbose` | Verbose output only |
| `--dev` | `--dev` | DEVELOPER profile |
| `--debug` | `--debug-log` | Debug logging only |

**Update `profile.py`**:

```python
@classmethod
def from_cli_args(
    cls,
    profile: str | None = None,
    dev: bool = False,
    theme_dev: bool = False,
    verbose: bool = False,  # Now just verbose output
    debug_log: bool = False,
) -> tuple[BuildProfile, dict[str, bool]]:
    """
    Returns:
        (profile, output_flags)

        output_flags = {
            "verbose_output": bool,  # Show detailed progress
            "debug_logging": bool,   # Enable debug logs
        }
    """
    output_flags = {
        "verbose_output": verbose,
        "debug_logging": debug_log,
    }

    if dev:
        return cls.DEVELOPER, output_flags
    if theme_dev:
        return cls.THEME_DEV, output_flags
    if profile:
        return cls.from_string(profile), output_flags

    return cls.WRITER, output_flags
```

---

## Migration Guide

### For Users

**No breaking changes in Phase 1-2**. Deprecation warnings only.

```yaml
# Deprecated (still works, shows warning):
minify_assets: true
generate_sitemap: true

# Preferred:
assets:
  minify: true
features:
  sitemap: true
```

**Phase 5 CLI changes** (breaking):

```bash
# Before
bengal build --verbose  # Enabled health checks!

# After
bengal build --theme-dev  # Same behavior
bengal build --verbose    # Just verbose output
```

---

## Implementation Plan

| Phase | Scope | Files Changed | Risk |
|-------|-------|---------------|------|
| 1 | Create `defaults.py`, update hardcoded defaults | 8 | Low |
| 2 | Add missing `KNOWN_SECTIONS` | 1 | Low |
| 3 | Add deprecation warnings | 2 | Low |
| 4 | Standardize bool/dict merge | 3 | Medium |
| 5 | Rename CLI flags | 4 | Medium |

**Total estimate**: 2-3 weeks

---

## Confidence Assessment

| Component | Confidence | Rationale |
|-----------|------------|-----------|
| Phase 1 (defaults.py) | 95% 🟢 | Straightforward, low risk |
| Phase 2 (KNOWN_SECTIONS) | 95% 🟢 | Simple addition |
| Phase 3 (deprecation) | 90% 🟢 | Non-breaking |
| Phase 4 (bool/dict) | 80% 🟡 | Needs careful testing |
| Phase 5 (CLI flags) | 75% 🟡 | Breaking change, needs docs |

**Overall**: 87% 🟢

---

## Alternatives Considered

### A. Do Nothing
- **Pro**: No effort
- **Con**: Technical debt grows, user confusion continues
- **Decision**: Rejected

### B. Full Config Rewrite with Pydantic
- **Pro**: Type safety, auto-validation, auto-docs
- **Con**: Large dependency, major refactor, breaking changes
- **Decision**: Defer to future (too disruptive now)

### C. Incremental Cleanup (This RFC)
- **Pro**: Low risk, immediate value, non-breaking (mostly)
- **Con**: Doesn't solve everything
- **Decision**: **Accepted**

---

## Success Criteria

- [ ] All defaults come from single source (`defaults.py`)
- [ ] No "unknown section" warnings for documented sections
- [ ] Deprecation warnings for old keys
- [ ] Consistent bool/dict handling
- [ ] CLI flags match user expectations
- [ ] Config reference documentation auto-generated

---

## Open Questions

1. **Should we bump minor version for CLI flag changes?**
   - Recommendation: Yes, v0.X+1.0

2. **Should `--verbose` be completely redefined?**
   - Option A: Keep THEME_DEV behavior (backward compatible)
   - Option B: Change to just verbose output (breaking but clearer)
   - Recommendation: Option B with deprecation period

3. **Should we add JSON Schema validation?**
   - Recommendation: Yes, but in a separate RFC

---

## References

- `plan/active/config-inventory.md` - Full config audit
- `bengal/config/loader.py` - Current implementation
- `bengal/utils/profile.py` - Profile system
