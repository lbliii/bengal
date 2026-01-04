# RFC: Config Architecture V2 — Canonical Nested Structure

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-01-04 |
| **Author** | Bengal Team |
| **Scope** | Breaking Change |
| **Goal** | Eliminate flattening complexity, make config predictable |

## Summary

Replace Bengal's configuration system with a **canonical nested structure**. Remove the flattening step entirely. One structure, one loader, zero ambiguity.

## Problem Statement

### Current Architecture Issues

**1. Dual-Level Key Ambiguity**

After loading, values exist at both levels:

```python
config["title"]          # "Bengal Site" (from DEFAULTS flat key)
config["site"]["title"]  # "My Site" (from user config)
# Which wins? It depends on flattening order.
```

**2. Fragile Flattening Logic**

The `_flatten_config()` method has complex precedence rules:

```python
# Current logic (simplified)
flat = dict(config)

if "site" in config:
    for key, value in config["site"].items():
        flat[key] = value  # Always override (after our fix)
```

Problems:
- Order-dependent (DEFAULTS first, user config second, then flatten)
- Two separate implementations (`ConfigLoader` vs `ConfigDirectoryLoader`)
- `ConfigLoader._flatten_config()` only handles `site`, `build`
- `ConfigDirectoryLoader._flatten_config()` also handles `dev`, `features`, `assets`

**3. DEFAULTS Has Both Flat and Nested Keys**

```python
DEFAULTS = {
    "title": "Bengal Site",        # Flat
    "baseurl": "",                 # Flat
    "output_dir": "public",        # Flat
    # ...
    "site": { ... },               # Would be nested (not currently present)
    "theme": { "name": "default" } # Nested
}
```

This creates ambiguity about canonical location.

**4. Two Config Loaders with Duplicated Logic**

| Feature | `ConfigLoader` | `ConfigDirectoryLoader` |
|---------|---------------|------------------------|
| Flattens `site.*` | ✅ | ✅ |
| Flattens `build.*` | ✅ | ✅ |
| Flattens `dev.*` | ❌ | ✅ |
| Flattens `features.*` | ❌ | ✅ |
| Flattens `assets.*` | ❌ | ✅ |
| Applies DEFAULTS | via `_default_config()` | via `deep_merge({}, DEFAULTS)` |
| Feature expansion | ❌ | ✅ |
| Section normalization | ✅ | ❌ |

**5. Feature Expansion is Hidden**

```yaml
# User writes:
features:
  search: true

# Bengal internally expands to:
search:
  enabled: true
  preload: smart
output_formats:
  site_wide: [index_json]
```

This is powerful but:
- Not discoverable without reading `feature_mappings.py`
- Removes `features` key from config (via `pop()`)
- Easy to confuse with `theme.features` (UI flags, not expanded)

### Root Cause

The architecture evolved organically to support multiple access patterns:
- `config["title"]` (Hugo-like flat access)
- `config["site"]["title"]` (structured TOML/YAML)

This duality creates complexity that compounds with:
- DEFAULTS layering
- Environment overrides
- Feature expansion
- Two loader implementations

## Proposed Architecture

### Design Principles

1. **Single canonical structure** — Nested (`site.title`, `build.parallel`)
2. **DEFAULTS only nested** — Remove flat top-level duplicates
3. **No runtime flattening** — Config dict is never mutated post-load
4. **Accessor for ergonomics** — `Config` class provides flat access as computed property
5. **Unified loader** — One loader handles both file and directory modes
6. **Explicit feature expansion** — Clear documentation, optional verbose mode

### New DEFAULTS Structure

```python
# bengal/config/defaults.py

DEFAULTS: dict[str, Any] = {
    # -------------------------------------------------------------------------
    # Site Metadata (canonical location: site.*)
    # -------------------------------------------------------------------------
    "site": {
        "title": "Bengal Site",
        "baseurl": "",
        "description": "",
        "author": "",
        "language": "en",
    },

    # -------------------------------------------------------------------------
    # Build Settings (canonical location: build.*)
    # -------------------------------------------------------------------------
    "build": {
        "output_dir": "public",
        "content_dir": "content",
        "assets_dir": "assets",
        "templates_dir": "templates",
        "parallel": True,
        "incremental": None,
        "max_workers": None,
        "pretty_urls": True,
        "minify_html": True,
        "strict_mode": False,
        "debug": False,
        "validate_build": True,
        "validate_links": True,
        "transform_links": True,
        "fast_writes": False,
        "fast_mode": False,
    },

    # -------------------------------------------------------------------------
    # Development (canonical location: dev.*)
    # -------------------------------------------------------------------------
    "dev": {
        "cache_templates": True,
        "watch_backend": True,
        "live_reload": True,
        "port": 8000,
    },

    # -------------------------------------------------------------------------
    # Theme, Search, Content, etc. (unchanged - already nested)
    # -------------------------------------------------------------------------
    "theme": { ... },
    "search": { ... },
    "content": { ... },
    # ...
}
```

### Config Accessor Class

```python
# bengal/config/accessor.py

from __future__ import annotations
from typing import Any, Protocol, cast
from functools import cached_property

# -----------------------------------------------------------------------------
# Type Protocols (for IDE autocomplete)
# -----------------------------------------------------------------------------

class SiteConfig(Protocol):
    """Type hints for site.* config section."""
    title: str
    baseurl: str
    description: str
    author: str
    language: str

class BuildConfig(Protocol):
    """Type hints for build.* config section."""
    output_dir: str
    content_dir: str
    assets_dir: str
    templates_dir: str
    parallel: bool
    incremental: bool | None
    max_workers: int | None
    pretty_urls: bool
    minify_html: bool
    strict_mode: bool
    debug: bool

class DevConfig(Protocol):
    """Type hints for dev.* config section."""
    cache_templates: bool
    watch_backend: bool
    live_reload: bool
    port: int

# -----------------------------------------------------------------------------
# Config Classes
# -----------------------------------------------------------------------------

class Config:
    """
    Configuration accessor with structured access.

    Access patterns:
        >>> cfg = Config(loaded_dict)
        >>> cfg.site.title           # Attribute access (preferred)
        'My Site'
        >>> cfg.build.parallel       # Nested sections
        True
        >>> cfg["theme"]["name"]     # Dict access for dynamic keys
        'default'
        >>> cfg.site.get("custom")   # Optional keys (returns None)
        None
        >>> cfg.site.typo            # Typos raise AttributeError!
        AttributeError: No config key 'typo' in section
    """

    __slots__ = ("_data", "__dict__") # __dict__ needed for cached_property

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # -------------------------------------------------------------------------
    # Section Accessors (cached for performance)
    # -------------------------------------------------------------------------

    @cached_property
    def site(self) -> SiteConfig:
        """Returns site section cast to SiteConfig protocol for IDE support."""
        return cast(SiteConfig, ConfigSection(self._data.get("site", {}), "site"))

    @cached_property
    def build(self) -> BuildConfig:
        """Returns build section cast to BuildConfig protocol for IDE support."""
        return cast(BuildConfig, ConfigSection(self._data.get("build", {}), "build"))

    @cached_property
    def dev(self) -> DevConfig:
        """Returns dev section cast to DevConfig protocol for IDE support."""
        return cast(DevConfig, ConfigSection(self._data.get("dev", {}), "dev"))

    @cached_property
    def theme(self) -> ConfigSection:
        return ConfigSection(self._data.get("theme", {}), "theme")

    @cached_property
    def search(self) -> ConfigSection:
        return ConfigSection(self._data.get("search", {}), "search")

    @cached_property
    def content(self) -> ConfigSection:
        return ConfigSection(self._data.get("content", {}), "content")

    @cached_property
    def assets(self) -> ConfigSection:
        return ConfigSection(self._data.get("assets", {}), "assets")

    @cached_property
    def output_formats(self) -> ConfigSection:
        return ConfigSection(self._data.get("output_formats", {}), "output_formats")

    @cached_property
    def features(self) -> ConfigSection:
        return ConfigSection(self._data.get("features", {}), "features")

    def __getattr__(self, key: str) -> ConfigSection:
        """
        Enables config.custom_section.key for user-defined sections.
        Fallthrough for any section not explicitly defined as a property.
        """
        if key.startswith("_"):
            raise AttributeError(key)
        return ConfigSection(self._data.get(key, {}), key)

    # -------------------------------------------------------------------------
    # Dict Access (for dynamic/custom keys)
    # -------------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    @property
    def raw(self) -> dict[str, Any]:
        """Raw config dict for serialization/debugging."""
        return self._data


class ConfigSection:
    """
    Accessor for a config section with attribute access.

    Design decisions:
        1. Missing keys raise AttributeError (typos fail loudly)
        2. Use .get(key) for optional keys that may not exist
        3. Nested dicts become cached ConfigSection for chaining
        4. Nested sections are cached to avoid repeated object creation

    Example:
        config.theme.syntax_highlighting.css_class_style  # Cached at each level
    """

    __slots__ = ("_data", "_path", "_cache")

    def __init__(self, data: dict[str, Any], path: str = "") -> None:
        self._data = data
        self._path = path  # For error messages
        self._cache: dict[str, ConfigSection] = {}  # Cache nested sections

    def __getattr__(self, key: str) -> Any:
        # Prevent infinite recursion on special attributes
        if key.startswith("_"):
            raise AttributeError(key)

        # Check if key exists — fail loudly on typos!
        if key not in self._data:
            path_str = f"{self._path}.{key}" if self._path else key
            raise AttributeError(
                f"No config key '{key}' in section. "
                f"Use .get('{key}') for optional keys. Path: {path_str}"
            )

        value = self._data[key]

        # Wrap nested dicts as ConfigSection (cached)
        if isinstance(value, dict):
            if key not in self._cache:
                nested_path = f"{self._path}.{key}" if self._path else key
                self._cache[key] = ConfigSection(value, nested_path)
            return self._cache[key]

        return value

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: section["key"]. Raises KeyError if missing."""
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Safe access for optional keys. Returns default if missing."""
        value = self._data.get(key, default)
        if isinstance(value, dict):
            nested_path = f"{self._path}.{key}" if self._path else key
            return ConfigSection(value, nested_path)
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __repr__(self) -> str:
        return f"ConfigSection({self._path or 'root'}: {list(self._data.keys())})"

    def __bool__(self) -> bool:
        """Allow `if config.section:` to check if section has data."""
        return bool(self._data)

    def keys(self) -> list[str]:
        """List available keys in this section."""
        return list(self._data.keys())
```

### Unified Config Loader

```python
# bengal/config/loader.py (replaces old loader.py and directory_loader.py)

class ConfigLoader:
    """
    Single loader for all config modes.

    Precedence (lowest to highest):
        1. DEFAULTS (nested structure)
        2. User config (single file or directory)
        3. Environment overrides (optional)
        4. Profile overrides (optional)
    """

    def __init__(self, track_origins: bool = False) -> None:
        self.track_origins = track_origins
        self.origin_tracker: ConfigWithOrigin | None = None

    def load(
        self,
        site_root: Path,
        environment: str | None = None,
        profile: str | None = None,
    ) -> Config:
        """
        Load configuration from site root.

        Auto-detects config mode:
            - config/ directory exists → directory mode
            - bengal.toml/yaml exists → single-file mode
            - Neither → DEFAULTS only
        """
        if self.track_origins:
            self.origin_tracker = ConfigWithOrigin()

        # Layer 0: DEFAULTS
        config = deep_merge({}, DEFAULTS)
        if self.origin_tracker:
            self.origin_tracker.merge(DEFAULTS, "_bengal_defaults")

        # Layer 1: User config
        config_dir = site_root / "config"
        single_file = self._find_config_file(site_root)

        if config_dir.exists() and config_dir.is_dir():
            user_config = self._load_directory(config_dir)
            config = deep_merge(config, user_config)
        elif single_file:
            user_config = self._load_file(single_file)
            config = deep_merge(config, user_config)

        # Layer 2: Environment (auto-detect or explicit)
        if environment is None:
            environment = detect_environment()

        if environment and config_dir.exists():
            env_config = self._load_environment(config_dir, environment)
            if env_config:
                config = deep_merge(config, env_config)

        # Layer 3: Profile
        if profile and config_dir.exists():
            profile_config = self._load_profile(config_dir, profile)
            if profile_config:
                config = deep_merge(config, profile_config)

        # Feature expansion
        config = expand_features(config)

        # Platform env vars (Netlify, Vercel, GitHub)
        config = apply_env_overrides(config)

        return Config(config)

    def _find_config_file(self, site_root: Path) -> Path | None:
        for name in ("bengal.toml", "bengal.yaml", "bengal.yml"):
            path = site_root / name
            if path.exists():
                return path
        return None

    def _load_file(self, path: Path) -> dict[str, Any]:
        if path.suffix == ".toml":
            return load_toml(path)
        return load_yaml(path)

    def _load_directory(self, config_dir: Path) -> dict[str, Any]:
        defaults_dir = config_dir / "_default"
        if not defaults_dir.exists():
            return {}

        configs = []
        for yaml_file in sorted(defaults_dir.glob("*.yaml")):
            configs.append(load_yaml(yaml_file))
        for yml_file in sorted(defaults_dir.glob("*.yml")):
            configs.append(load_yaml(yml_file))

        return batch_deep_merge(configs)

    # ... _load_environment, _load_profile similar to current ...
```

### Site Integration

```python
# bengal/core/site.py

class Site:
    def __init__(self, ...):
        self.config = Config(loaded_dict)

    # Direct access patterns
    @property
    def title(self) -> str:
        return self.config.site.title

    @property
    def baseurl(self) -> str:
        return self.config.site.baseurl

    @property
    def output_dir(self) -> Path:
        return Path(self.config.build.output_dir)
```

Access patterns:

```python
# Structured access (preferred)
title = site.config.site.title
parallel = site.config.build.parallel

# Dict access when needed
theme_name = site.config["theme"]["name"]

# Convenience properties
title = site.title
output = site.output_dir
```

### Template Access

Templates receive config via the render context. The `Config` object is exposed directly:

```python
# bengal/core/render.py

def build_render_context(site: Site, page: Page) -> dict[str, Any]:
    return {
        "config": site.config,      # Full Config object
        "site": site,               # Site object (has config property)
        "page": page,
        # ...
    }
```

**Jinja template access patterns:**

```jinja
{# Structured access (preferred) #}
<title>{{ config.site.title }}</title>
<meta name="description" content="{{ config.site.description }}">

{# Check if optional key exists #}
{% if config.site.get("analytics_id") %}
  <script>/* analytics */</script>
{% endif %}

{# Theme settings #}
{% if config.theme.syntax_highlighting.enabled %}
  <link rel="stylesheet" href="{{ config.theme.syntax_highlighting.css_path }}">
{% endif %}

{# Via site convenience properties #}
<base href="{{ site.baseurl }}">
```

**Migration from flat access:**

```jinja
{# Before (flat) #}
{{ config.title }}
{{ config.baseurl }}

{# After (nested) #}
{{ config.site.title }}
{{ config.site.baseurl }}
```

### Hot Path Optimization

For code that accesses config thousands of times (e.g., per-page rendering), hoist section references:

```python
# ❌ Bad: Creates ConfigSection objects repeatedly
for page in pages:
    if config.theme.syntax_highlighting.enabled:  # 2 new objects per iteration
        highlight(page, config.theme.syntax_highlighting.line_numbers)

# ✅ Good: Cache section reference
syntax_config = config.theme.syntax_highlighting  # Cached ConfigSection
for page in pages:
    if syntax_config.enabled:  # Reuses cached object
        highlight(page, syntax_config.line_numbers)
```

The `Config` class uses `cached_property` for top-level sections, and `ConfigSection` caches nested sections internally. However, hoisting is still recommended for tight loops.

### Feature Expansion Integration

Feature expansion (`features.search: true` → detailed config) runs during loading, before the `Config` object is created:

```python
# bengal/config/loader.py

def load(self, site_root: Path, ...) -> Config:
    # Layer 0: DEFAULTS (nested)
    config = deep_merge({}, DEFAULTS)

    # Layer 1: User config
    user_config = self._load_user_config(site_root)
    config = deep_merge(config, user_config)

    # Layer 2: Environment overrides
    config = self._apply_environment(config, environment)

    # Layer 3: Profile overrides
    config = self._apply_profile(config, profile)

    # Feature expansion (BEFORE creating Config object)
    # This mutates the dict, expanding shorthand to full config
    config = expand_features(config)

    # Platform env vars (Netlify, Vercel, GitHub)
    config = apply_env_overrides(config)

    # Validation
    validate_config(config)

    # Create immutable accessor
    return Config(config)
```

**Key Points**:
- `expand_features()` runs on the raw dict, not the `Config` object
- The `Config` object is created *after* expansion, so it sees the expanded values
- Feature expansion is transparent to code using `Config` — they see the final state

**Feature expansion example**:

```yaml
# User writes (shorthand):
features:
  search: true

# After expand_features():
search:
  enabled: true
  lunr:
    prebuilt: true
    preload: smart
  # ... full search config from DEFAULTS
output_formats:
  site_wide:
    - index_json  # Added by search expansion
```

**Debugging feature expansion**:

```python
# In loader, log at DEBUG level:
if logger.isEnabledFor(logging.DEBUG):
    before = config.get("features", {})
    config = expand_features(config)
    after = {k: config.get(k) for k in ["search", "output_formats", "rss", "sitemap"]}
    logger.debug("feature_expansion", before=before, after=after)
```

### Config Validation

Validate required keys at load time to fail fast:

```python
# bengal/config/loader.py

REQUIRED_KEYS = {
    "site": ["title"],
    "build": ["output_dir", "content_dir"],
}

def validate_config(config: dict[str, Any]) -> None:
    """Validate required keys exist. Raises ConfigError if missing."""
    missing = []
    for section, keys in REQUIRED_KEYS.items():
        section_data = config.get(section, {})
        for key in keys:
            if key not in section_data:
                missing.append(f"{section}.{key}")

    if missing:
        raise ConfigError(
            f"Missing required config keys: {', '.join(missing)}. "
            f"Add them to your bengal.yaml or config/_default/*.yaml"
        )
```

Called at end of `ConfigLoader.load()`:

```python
def load(self, site_root: Path, ...) -> Config:
    # ... layer merging ...

    # Validate before returning
    validate_config(config)

    return Config(config)
```

## Impact Analysis

### Benefits

| Benefit | Description |
|---------|-------------|
| **Predictable precedence** | DEFAULTS → user config → env overrides. No flattening. |
| **Single source of truth** | `site.title` is the only location |
| **Unified loader** | One implementation, not two |
| **Type-safe access** | `config.site.title` with IDE autocomplete |
| **Easier debugging** | No hidden mutation step |
| **Less code** | Delete `_flatten_config()` entirely |

### Performance

| Operation | Current | Proposed |
|-----------|---------|----------|
| Config load | O(N) merge + O(K) flatten | O(N) merge only |
| Key access | O(1) dict lookup | O(1) attribute lookup |
| Nested access | N/A | O(1) cached after first access |
| Memory | 2× (flat + nested copies) | 1× (nested only) |

**Caching details:**

- `Config` uses `cached_property` for top-level sections (`site`, `build`, etc.)
- `ConfigSection` uses internal `_cache` dict for nested sections
- Chained access like `config.theme.syntax_highlighting.enabled` creates objects once, reuses on subsequent calls
- For tight loops, hoisting section references is still recommended (see Hot Path Optimization)

## Implementation Plan

### Step 0: Pre-Migration Verification (Required)

Before starting, run the migration script to establish a baseline:

```bash
# Generate baseline report
python scripts/migrate_config_access.py --templates --json > baseline.json

# Review summary
cat baseline.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'''
Flat Access Patterns Found:
  Total: {d['summary']['total_issues']}
  Files: {d['summary']['files_with_issues']}

By Type:
  dict_access: {d['summary']['by_type'].get('dict_access', 0)}
  get_call: {d['summary']['by_type'].get('get_call', 0)}  
  template: {d['summary']['by_type'].get('template', 0)}
''')"
```

**Gate**: Do not proceed if total issues > 100. Review patterns and refine script.

### Step 1: Restructure DEFAULTS (1 day)

Move all flat keys into canonical nested sections:

```python
# Before (current state - mixed flat and nested)
DEFAULTS = {
    "title": "Bengal Site",           # FLAT - move to site.title
    "baseurl": "",                    # FLAT - move to site.baseurl
    "output_dir": "public",           # FLAT - move to build.output_dir
    "parallel": True,                 # FLAT - move to build.parallel
    # ...
    "theme": {"name": "default"},     # Already nested - keep as-is
}

# After (fully nested)
DEFAULTS = {
    "site": {
        "title": "Bengal Site",
        "baseurl": "",
        "description": "",
        "author": "",
        "language": "en",
    },
    "build": {
        "output_dir": "public",
        "content_dir": "content",
        "assets_dir": "assets",
        "templates_dir": "templates",
        "parallel": True,
        "incremental": None,
        "max_workers": None,
        "pretty_urls": True,
        "minify_html": True,
        "strict_mode": False,
        "debug": False,
        "validate_build": True,
        "validate_links": True,
        "transform_links": True,
        "fast_writes": False,
        "fast_mode": False,
    },
    "dev": {
        "cache_templates": True,
        "watch_backend": True,
        "live_reload": True,
        "port": 8000,
    },
    "theme": {...},    # Already nested
    "search": {...},   # Already nested
    # ...
}
```

### Step 2: Config Accessor (1 day)

Create `bengal/config/accessor.py`:
- `Config` class with section accessors
- `ConfigSection` for nested access
- Dict-like access for raw data

### Step 3: Unified Loader (1-2 days)

Create `bengal/config/unified_loader.py`:
- Merge `ConfigLoader` and `ConfigDirectoryLoader`
- Delete `_flatten_config()` entirely
- Return `Config` object, not dict

### Step 4: Update Codebase (2-3 days)

Update `bengal/config/env_overrides.py`:
- Target `config["site"]["baseurl"]` instead of flat keys.
- Ensure platform auto-detection (Netlify/Vercel/GitHub) is preserved.

Find and replace all flat access patterns:

```bash
# Find all config["flat_key"] patterns
rg 'config\["(title|baseurl|output_dir|parallel|...)"\]' --type py
rg "config\.get\(['\"]" --type py
```

Update to structured access:
- `config["title"]` → `config.site.title`
- `config.get("parallel")` → `config.build.parallel`

### Step 5: Delete Old Code

Remove:
- `bengal/config/loader.py` (replaced by unified)
- `bengal/config/directory_loader.py` (replaced by unified)
- All `_flatten_config()` methods

## Alternatives Considered

### 1. Keep Flattening, Fix Edge Cases

**Rejected** — We've already fixed several edge cases. The complexity keeps creating subtle bugs. Delete the complexity.

### 2. Only Flat Config (Like Hugo)

**Rejected** — YAML/TOML are naturally nested. Forcing flat structure requires ugly prefixes (`site_title`, `build_parallel`).

### 3. Gradual Migration with Shims

**Rejected** — Adds complexity, delays cleanup, confuses the codebase with two access patterns.

## Edge Cases

### Empty Sections

```python
# User config has no theme section
config.theme           # Returns empty ConfigSection({})
config.theme.name      # Raises AttributeError (fail loudly)
config.theme.get("name")  # Returns None (safe access)
bool(config.theme)     # Returns False
```

### User Custom Keys

```python
# bengal.yaml
myapp:
  api_key: "secret"
  timeout: 30

# Access pattern
config["myapp"]["api_key"]  # Dict access for custom sections
config.raw["myapp"]         # Get raw dict for serialization
```

### Keys with Special Characters

```python
# bengal.yaml
site:
  some-key: "value"      # Hyphens (common in YAML)
  "123": "numeric start" # Numeric keys

# Access pattern (dict-style required)
config.site["some-key"]  # Hyphens not valid Python identifiers
config.site["123"]       # Numeric keys
config.site.get("some-key")  # Also works
```

### Truthiness of Values

```python
# False-y values are preserved
config.build.debug       # False (not truthy, but exists)
config.build.max_workers # None (explicit null)

# Check existence vs truthiness
"debug" in config.build  # True (key exists)
bool(config.build.debug) # False (value is False)
```

### Nested `None` Values

```python
# bengal.yaml
theme:
  syntax_highlighting: null

# Access pattern
config.theme.syntax_highlighting  # Returns None (not ConfigSection)
config.theme.syntax_highlighting.enabled  # AttributeError on None!

# Safe pattern for optional nested sections
sh = config.theme.get("syntax_highlighting") or {}
enabled = sh.get("enabled", False)
```

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| **No `_flatten_config()`** | Method deleted from codebase |
| **Single loader** | One `ConfigLoader` class handles all modes |
| **DEFAULTS nested** | All 15+ flat keys moved to canonical sections |
| **Config accessor** | `config.site.title` works everywhere |
| **Typos fail loudly** | `config.site.tittle` raises `AttributeError` |
| **Nested caching works** | `ConfigSection._cache` prevents object churn |
| **Validation at load** | Missing required keys raise `ConfigError` |
| **Feature expansion integrated** | `expand_features()` runs before `Config` creation |
| **Templates updated** | All 16 template flat-access patterns migrated |
| **Tests pass** | All tests updated and passing |
| **Migration script** | `scripts/migrate_config_access.py` with JSON output |
| **Zero migration issues** | `migrate_config_access.py` reports 0 issues |
| **CI gate** | `BENGAL_STRICT_CONFIG=1` in test suite |

### Verification Commands

```bash
# 1. No _flatten_config methods remain
rg '_flatten_config' bengal/ --type py | wc -l  # Should be 0

# 2. Migration script reports zero issues
python scripts/migrate_config_access.py --templates --json | jq '.summary.total_issues'  # Should be 0

# 3. All tests pass with strict mode
BENGAL_STRICT_CONFIG=1 pytest tests/ -x

# 4. DEFAULTS has no flat keys
python -c "
from bengal.config.defaults import DEFAULTS
flat_keys = [k for k in DEFAULTS if not isinstance(DEFAULTS[k], dict)]
print(f'Flat keys remaining: {flat_keys}')
assert not flat_keys, 'DEFAULTS should be fully nested'
"
```

## Migration Safety

### Automated Migration Script

Create a comprehensive script to find, report, and optionally fix all flat access patterns:

```python
# scripts/migrate_config_access.py
"""
Config Access Migration Tool

Finds and reports all flat config access patterns that need migration
to the new nested structure. Supports dry-run and auto-fix modes.

Usage:
    python scripts/migrate_config_access.py                    # Dry run, report only
    python scripts/migrate_config_access.py --fix              # Auto-fix Python files
    python scripts/migrate_config_access.py --templates        # Include Jinja templates
    python scripts/migrate_config_access.py --json > report.json  # Machine-readable output
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

# Complete mapping of flat keys to canonical nested locations
MIGRATION_MAP: dict[str, str] = {
    # site.* (Site Metadata)
    "title": "site.title",
    "baseurl": "site.baseurl",
    "description": "site.description",
    "author": "site.author",
    "language": "site.language",
    # build.* (Build Settings)
    "output_dir": "build.output_dir",
    "content_dir": "build.content_dir",
    "assets_dir": "build.assets_dir",
    "templates_dir": "build.templates_dir",
    "parallel": "build.parallel",
    "incremental": "build.incremental",
    "max_workers": "build.max_workers",
    "pretty_urls": "build.pretty_urls",
    "minify_html": "build.minify_html",
    "strict_mode": "build.strict_mode",
    "debug": "build.debug",
    "validate_build": "build.validate_build",
    "validate_links": "build.validate_links",
    "transform_links": "build.transform_links",
    "fast_writes": "build.fast_writes",
    "fast_mode": "build.fast_mode",
    # dev.* (Development)
    "cache_templates": "dev.cache_templates",
    "watch_backend": "dev.watch_backend",
    "live_reload": "dev.live_reload",
    "port": "dev.port",
}

FLAT_KEYS = frozenset(MIGRATION_MAP.keys())

# Patterns that indicate nested access (not flat) - skip these
NESTED_ACCESS_SECTIONS = frozenset({
    "site", "build", "dev", "theme", "search", "content", "assets",
    "output_formats", "features", "graph", "i18n", "markdown",
    "health_check", "pagination", "menu", "taxonomies",
})


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Issue:
    """A single flat access pattern found in code."""
    file: Path
    line: int
    column: int
    old_pattern: str
    new_pattern: str
    context: str  # The line of code for review
    pattern_type: str  # "dict_access" | "get_call" | "template"

@dataclass
class MigrationReport:
    """Aggregated migration report."""
    issues: list[Issue] = field(default_factory=list)
    files_scanned: int = 0
    files_with_issues: int = 0

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_issues": len(self.issues),
                "files_scanned": self.files_scanned,
                "files_with_issues": self.files_with_issues,
                "by_type": self._count_by_type(),
                "by_key": self._count_by_key(),
            },
            "issues": [
                {
                    "file": str(i.file),
                    "line": i.line,
                    "column": i.column,
                    "old": i.old_pattern,
                    "new": i.new_pattern,
                    "type": i.pattern_type,
                }
                for i in self.issues
            ],
        }

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.pattern_type] = counts.get(issue.pattern_type, 0) + 1
        return counts

    def _count_by_key(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for issue in self.issues:
            # Extract key from old_pattern
            key = issue.old_pattern.split("[")[1].split("]")[0].strip("\"'") \
                if "[" in issue.old_pattern else \
                issue.old_pattern.split("(")[1].split(")")[0].split(",")[0].strip("\"'")
            counts[key] = counts.get(key, 0) + 1
        return counts


# =============================================================================
# Pattern Matching
# =============================================================================

def find_python_issues(file: Path) -> list[Issue]:
    """Find flat config access patterns in Python files."""
    issues: list[Issue] = []

    try:
        content = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return issues

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        # Pattern 1: config["key"] or config['key']
        # Matches: config["title"], site.config["baseurl"], self.config["parallel"]
        for match in re.finditer(r'(\w*\.?config)\[(["\'])(\w+)\2\]', line):
            prefix = match.group(1)  # "config" or "site.config" etc.
            key = match.group(3)

            # Skip if accessing a known nested section
            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                section, attr = new_path.split(".")
                issues.append(Issue(
                    file=file,
                    line=line_num,
                    column=match.start() + 1,
                    old_pattern=match.group(0),
                    new_pattern=f'{prefix}.{section}.{attr}',
                    context=line.strip(),
                    pattern_type="dict_access",
                ))

        # Pattern 2: config.get("key") or config.get("key", default)
        # Handles: config.get("title"), config.get("parallel", True)
        for match in re.finditer(
            r'(\w*\.?config)\.get\((["\'])(\w+)\2(?:,\s*([^)]+))?\)',
            line
        ):
            prefix = match.group(1)
            key = match.group(3)
            default = match.group(4)

            # Skip if accessing a known nested section
            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                section, attr = new_path.split(".")

                if default:
                    new_pattern = f'{prefix}.{section}.get("{attr}", {default})'
                else:
                    new_pattern = f'{prefix}.{section}.get("{attr}")'

                issues.append(Issue(
                    file=file,
                    line=line_num,
                    column=match.start() + 1,
                    old_pattern=match.group(0),
                    new_pattern=new_pattern,
                    context=line.strip(),
                    pattern_type="get_call",
                ))

    return issues


def find_template_issues(file: Path) -> list[Issue]:
    """Find flat config access patterns in Jinja templates."""
    issues: list[Issue] = []

    try:
        content = file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return issues

    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        # Pattern: {{ config.title }} or {{ config.baseurl }}
        for match in re.finditer(r'\{\{\s*config\.(\w+)\s*(\|[^}]+)?\}\}', line):
            key = match.group(1)
            filter_chain = match.group(2) or ""

            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                issues.append(Issue(
                    file=file,
                    line=line_num,
                    column=match.start() + 1,
                    old_pattern=match.group(0),
                    new_pattern=f'{{{{ config.{new_path}{filter_chain} }}}}',
                    context=line.strip(),
                    pattern_type="template",
                ))

        # Pattern: {% if config.debug %} or similar
        for match in re.finditer(r'\{%[^%]*config\.(\w+)[^%]*%\}', line):
            key = match.group(1)

            if key in NESTED_ACCESS_SECTIONS:
                continue

            if key in FLAT_KEYS:
                new_path = MIGRATION_MAP[key]
                old_pattern = f"config.{key}"
                new_pattern = f"config.{new_path}"
                issues.append(Issue(
                    file=file,
                    line=line_num,
                    column=match.start() + 1,
                    old_pattern=old_pattern,
                    new_pattern=new_pattern,
                    context=line.strip(),
                    pattern_type="template",
                ))

    return issues


# =============================================================================
# Main
# =============================================================================

def scan_codebase(
    root: Path,
    include_templates: bool = False,
) -> MigrationReport:
    """Scan codebase for flat config access patterns."""
    report = MigrationReport()
    files_with_issues: set[Path] = set()

    # Scan Python files
    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        report.files_scanned += 1
        issues = find_python_issues(py_file)
        if issues:
            files_with_issues.add(py_file)
            for issue in issues:
                report.add(issue)

    # Scan templates if requested
    if include_templates:
        for template_file in root.rglob("*.html"):
            report.files_scanned += 1
            issues = find_template_issues(template_file)
            if issues:
                files_with_issues.add(template_file)
                for issue in issues:
                    report.add(issue)

    report.files_with_issues = len(files_with_issues)
    return report


def print_report(report: MigrationReport) -> None:
    """Print human-readable migration report."""
    print(f"\n{'='*60}")
    print("Config Migration Report")
    print(f"{'='*60}\n")

    print(f"Files scanned:     {report.files_scanned}")
    print(f"Files with issues: {report.files_with_issues}")
    print(f"Total issues:      {len(report.issues)}\n")

    if not report.issues:
        print("✅ No flat config access patterns found!")
        return

    # Group by file
    by_file: dict[Path, list[Issue]] = {}
    for issue in report.issues:
        by_file.setdefault(issue.file, []).append(issue)

    for file, issues in sorted(by_file.items()):
        print(f"\n📄 {file} ({len(issues)} issues)")
        print("-" * 40)
        for issue in issues:
            print(f"  L{issue.line}: {issue.old_pattern}")
            print(f"       → {issue.new_pattern}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Config access migration tool")
    parser.add_argument("--root", type=Path, default=Path("bengal"),
                       help="Root directory to scan")
    parser.add_argument("--templates", action="store_true",
                       help="Include Jinja templates in scan")
    parser.add_argument("--json", action="store_true",
                       help="Output JSON report")
    parser.add_argument("--fix", action="store_true",
                       help="Auto-fix issues (USE WITH CAUTION)")
    args = parser.parse_args()

    if args.fix:
        print("⚠️  --fix mode not implemented. Review issues manually.")
        return 1

    report = scan_codebase(args.root, include_templates=args.templates)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    return 0 if not report.issues else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Usage**:

```bash
# Dry run - report all issues
python scripts/migrate_config_access.py

# Include templates
python scripts/migrate_config_access.py --templates

# Machine-readable output for CI
python scripts/migrate_config_access.py --json > migration-report.json

# Count issues by type
python scripts/migrate_config_access.py --json | jq '.summary'
```

### Template Migration

For Jinja templates, scan for flat access:

```bash
# Find flat access in templates
rg 'config\.(title|baseurl|output_dir|parallel)' --type html
rg 'config\[' templates/
```

### Deprecation Period (Optional)

If gradual migration is preferred, add a compatibility shim with deprecation warnings:

```python
# bengal/config/compat.py (temporary)

class CompatConfig(Config):
    """Temporary wrapper that warns on flat access. Delete after migration."""

    _FLAT_TO_NESTED = {
        "title": ("site", "title"),
        "baseurl": ("site", "baseurl"),
        "output_dir": ("build", "output_dir"),
        # ...
    }

    def __getitem__(self, key: str) -> Any:
        if key in self._FLAT_TO_NESTED:
            section, nested_key = self._FLAT_TO_NESTED[key]
            warnings.warn(
                f"Flat config access deprecated: config['{key}'] → "
                f"config.{section}.{nested_key}",
                DeprecationWarning,
                stacklevel=2
            )
            return getattr(getattr(self, section), nested_key)
        return super().__getitem__(key)
```

**Recommendation**: Given the scope (512 `config.get("` patterns), include the shim with `BENGAL_STRICT_CONFIG=1` opt-in for early adopters:

```python
# Default: Warnings enabled (deprecation period)
# BENGAL_STRICT_CONFIG=1: Errors (fail-fast for testing)

import os
STRICT_CONFIG = os.environ.get("BENGAL_STRICT_CONFIG") == "1"

class CompatConfig(Config):
    def __getitem__(self, key: str) -> Any:
        if key in self._FLAT_TO_NESTED:
            section, nested_key = self._FLAT_TO_NESTED[key]
            msg = (
                f"Flat config access deprecated: config['{key}'] → "
                f"config.{section}.{nested_key}"
            )
            if STRICT_CONFIG:
                raise DeprecationWarning(msg)
            else:
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return getattr(getattr(self, section), nested_key)
        return super().__getitem__(key)
```

**Migration Path**:
1. v1.x: Return `CompatConfig` with warnings (one release cycle)
2. v2.0: Return `Config` directly (breaking change)
3. CI: Run with `BENGAL_STRICT_CONFIG=1` to catch regressions

## Timeline

| Step | Duration | Deliverable |
|------|----------|-------------|
| Restructure DEFAULTS | 1 day | Nested structure |
| Config Accessor | 1 day | `Config` + `ConfigSection` classes |
| Unified Loader + Validation | 1-2 days | Single loader with validation |
| Migration Script + Dry Run | 0.5 day | ✅ Created, verified 134 issues |
| Update 67 Files (134 issues) | 2-3 days | All flat access patterns migrated |
| Update Templates | 0.5 day | 8 template patterns migrated |
| Update Tests | 1-2 days | All config tests updated |
| Delete Old Code + Final QA | 1 day | Remove deprecated files, integration test |
| **Total** | **~8-11 days** | Complete architecture change |

**Scope Analysis** (verified via `migrate_config_access.py`):
- **Total flat access patterns: 134 across 67 files**
  - `get_call` patterns: 111
  - `dict_access` patterns: 15
  - `template` patterns: 8
- Most frequent keys: `baseurl` (53), `title` (21), `max_workers` (16)
- Existing `_flatten_config` tests: 6 test cases to rewrite

**Note**: Initial grep found 512 `config.get("` patterns, but the migration script filters to only flat keys (not nested section access like `config.get("theme")`), reducing actual migration scope significantly.

## Design Decisions (Resolved)

> **Summary of Key Decisions**:
> - Fully nested DEFAULTS (no flat keys)
> - `Config` accessor with `cached_property` for sections
> - Fail-loud on typos (`AttributeError`), use `.get()` for optional
> - One-release deprecation period with `CompatConfig` shim
> - Comprehensive migration script with JSON output
> - Pre-migration verification gate (Step 0)

1. **`Config` class design** — ✅ Use `__slots__` for memory efficiency. Do NOT add `__getattr__` for dynamic sections — explicit `cached_property` accessors are safer and enable IDE autocomplete.

2. **Custom user keys** — ✅ Access via `config["myapp"]["setting"]` (dict access) or `config.raw["myapp"]` for full dict. No `get_nested()` helper — dot-path strings are error-prone and lose type safety.

3. **Feature expansion logging** — ✅ Log at DEBUG level. Users can enable `--debug` to see expansions:
   ```
   DEBUG: Feature 'search: true' expanded to search.enabled=true, output_formats.site_wide=[index_json]
   ```

4. **Missing key behavior** — ✅ Attribute access raises `AttributeError` (fail loudly on typos). Use `.get(key)` for optional keys that may not exist.

5. **Nested section caching** — ✅ `ConfigSection` caches nested sections in `_cache` dict to avoid repeated object creation on chained access.

6. **Thread Safety** — ✅ The `Config` accessor uses `cached_property`, which is not inherently thread-safe. To prevent race conditions during parallel rendering, `ConfigLoader.load()` will perform a "pre-flight" access of all core properties (`site`, `build`, `dev`) before returning the object, ensuring they are warmed in a single-threaded context.

## Files Changed

### Created

| File | Purpose |
|------|---------|
| `bengal/config/accessor.py` | `Config` and `ConfigSection` classes |
| `bengal/config/validation.py` | `validate_config()` and `REQUIRED_KEYS` |
| `scripts/migrate_config_access.py` | Migration helper to find flat access patterns |

### Modified

| File | Changes |
|------|---------|
| `bengal/config/defaults.py` | Restructure to fully nested |
| `bengal/config/loader.py` | Rewrite as unified loader, add validation |
| `bengal/config/env_overrides.py` | Update to target nested `site.baseurl` |
| `bengal/core/render.py` | Update template context to expose `Config` |
| `bengal/core/site.py` | Update to use `Config` accessor |
| `templates/**/*.html` | Update all flat config access to nested |

### Deleted

| File | Reason |
|------|--------|
| `bengal/config/directory_loader.py` | Merged into `loader.py` |
| All `_flatten_config()` methods | No longer needed |

## References

- DEFAULTS: `bengal/config/defaults.py`
- Feature expansion: `bengal/config/feature_mappings.py`
- Merge utilities: `bengal/config/merge.py`
- Related RFC: `plan/rfc-search-enabled-by-default.md` (exposed flattening issues)
