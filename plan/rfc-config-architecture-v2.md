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
from typing import Any, Protocol
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

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # -------------------------------------------------------------------------
    # Section Accessors (cached for performance)
    # -------------------------------------------------------------------------

    @cached_property
    def site(self) -> ConfigSection:
        return ConfigSection(self._data.get("site", {}), "site")

    @cached_property
    def build(self) -> ConfigSection:
        return ConfigSection(self._data.get("build", {}), "build")

    @cached_property
    def dev(self) -> ConfigSection:
        return ConfigSection(self._data.get("dev", {}), "dev")

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

### Step 1: Restructure DEFAULTS (1 day)

Move all flat keys into canonical nested sections:

```python
# Before
"title": "Bengal Site",
"output_dir": "public",

# After  
"site": {"title": "Bengal Site", ...},
"build": {"output_dir": "public", ...},
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

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| **No `_flatten_config()`** | Method deleted from codebase |
| **Single loader** | One `ConfigLoader` class handles all modes |
| **DEFAULTS nested** | All values in canonical sections |
| **Config accessor** | `config.site.title` works everywhere |
| **Typos fail loudly** | `config.site.tittle` raises `AttributeError` |
| **Nested caching works** | `ConfigSection._cache` prevents object churn |
| **Validation at load** | Missing required keys raise `ConfigError` |
| **Templates updated** | All Jinja templates use nested access |
| **Tests pass** | All tests updated and passing |
| **Migration script** | `scripts/migrate_config_access.py` exists |

## Migration Safety

### Automated Migration Script

Create a script to find and report all flat access patterns:

```python
# scripts/migrate_config_access.py

import re
from pathlib import Path

FLAT_KEYS = {
    "title", "baseurl", "description", "author", "language",  # site.*
    "output_dir", "content_dir", "parallel", "incremental",   # build.*
    "cache_templates", "watch_backend", "live_reload", "port", # dev.*
}

MIGRATION_MAP = {
    "title": "site.title",
    "baseurl": "site.baseurl",
    "output_dir": "build.output_dir",
    "parallel": "build.parallel",
    # ... complete mapping
}

def find_flat_access(file: Path) -> list[tuple[int, str, str]]:
    """Find config['flat_key'] and config.get('flat_key') patterns."""
    issues = []
    content = file.read_text()

    # Pattern: config["key"] or config['key']
    for match in re.finditer(r'config\[(["\'])(\w+)\1\]', content):
        key = match.group(2)
        if key in FLAT_KEYS:
            line_num = content[:match.start()].count('\n') + 1
            issues.append((line_num, key, MIGRATION_MAP.get(key, f"?.{key}")))

    # Pattern: config.get("key") or config.get('key')
    for match in re.finditer(r'config\.get\((["\'])(\w+)\1', content):
        key = match.group(2)
        if key in FLAT_KEYS:
            line_num = content[:match.start()].count('\n') + 1
            issues.append((line_num, key, MIGRATION_MAP.get(key, f"?.{key}")))

    return issues

def main():
    for py_file in Path("bengal").rglob("*.py"):
        issues = find_flat_access(py_file)
        for line, old, new in issues:
            print(f"{py_file}:{line}: config['{old}'] → config.{new}")
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

**Recommendation**: Skip the shim. Breaking changes are cleaner than prolonged deprecation. The migration script catches all cases.

## Timeline

| Step | Duration | Deliverable |
|------|----------|-------------|
| Restructure DEFAULTS | 1 day | Nested structure |
| Config Accessor | 1 day | `Config` + `ConfigSection` classes |
| Unified Loader + Validation | 1-2 days | Single loader with validation |
| Migration Script | 0.5 day | Automated flat-access finder |
| Update Codebase | 3-4 days | All Python access patterns updated |
| Update Templates | 1 day | Jinja template access updated |
| Update Tests | 1-2 days | All config tests updated |
| Delete Old Code | 0.5 day | Remove deprecated files |
| **Total** | **~9-11 days** | Complete architecture change |

**Note**: Original 6-day estimate was optimistic. Template updates and test fixes typically surface edge cases.

## Design Decisions (Resolved)

1. **`Config` class design** — ✅ Use `__slots__` for memory efficiency. Do NOT add `__getattr__` for dynamic sections — explicit `cached_property` accessors are safer and enable IDE autocomplete.

2. **Custom user keys** — ✅ Access via `config["myapp"]["setting"]` (dict access) or `config.raw["myapp"]` for full dict. No `get_nested()` helper — dot-path strings are error-prone and lose type safety.

3. **Feature expansion logging** — ✅ Log at DEBUG level. Users can enable `--debug` to see expansions:
   ```
   DEBUG: Feature 'search: true' expanded to search.enabled=true, output_formats.site_wide=[index_json]
   ```

4. **Missing key behavior** — ✅ Attribute access raises `AttributeError` (fail loudly on typos). Use `.get(key)` for optional keys that may not exist.

5. **Nested section caching** — ✅ `ConfigSection` caches nested sections in `_cache` dict to avoid repeated object creation on chained access.

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
