# RFC: Enable Search by Default

| Field | Value |
|-------|-------|
| **Status** | Implemented |
| **Created** | 2026-01-04 |
| **Updated** | 2026-01-04 |
| **Author** | Bengal Team |
| **Scope** | Behavior Change (Minor) |
| **Goal** | Make search work out-of-the-box for all configuration modes |

## Summary

Fix Bengal's configuration loading so that search functionality works immediately without requiring explicit configuration. Currently, sites created with `bengal new` get search by default, but sites using directory-based config without a `features.yaml` file do not—even though `defaults.py` has search enabled.

## Motivation

### The Problem

**Current behavior varies by config mode:**

Sites created with `bengal new`:
- ✅ Get `features.yaml` with `search: True`
- ✅ Feature expansion adds `index_json` to output formats
- ✅ Search works

Sites with directory-based config (missing `features.yaml`):
- ❌ No `index.json` generated
- ❌ No `/search/` page works
- ❌ Search modal has nothing to search

**The root cause**: `ConfigDirectoryLoader` starts with an empty config dictionary and only merges files from `_default/`. It does NOT inherit from `DEFAULTS` in `defaults.py`.

```python
# bengal/config/directory_loader.py (line 194)
config: dict[str, Any] = {}  # ← Starts empty, not from DEFAULTS!
```

Meanwhile, `defaults.py` already has the correct defaults:

```python
# bengal/config/defaults.py (lines 322-326)
"output_formats": {
    "enabled": True,
    "per_page": ["json"],
    "site_wide": ["index_json"],  # ← Already correct!
    ...
}
```

### Additional Confusion: Two Different `features` Systems

Bengal has two separate "features" concepts that cause confusion:

1. **Top-level `features:`** (dict) — Triggers feature expansion via `expand_features()`
   ```yaml
   # config/_default/features.yaml
   features:
     search: true  # ← Expands to output_formats.site_wide: ["index_json"]
   ```

2. **`theme.features:`** (array) — Template feature flags for UI components
   ```yaml
   # config/_default/theme.yaml
   theme:
     features:
       - search           # ← Only enables search UI, NOT index generation
       - search.suggest
       - search.highlight
   ```

Users naturally assume `theme.features: [search]` enables search fully. It doesn't—it only enables the search UI components in templates.

### Discovery Path

The Rosettes documentation site has this exact problem:

```
rosettes/site/config/_default/
├── autodoc.yaml
├── build.yaml
├── content.yaml
├── fonts.yaml
├── params.yaml
├── site.yaml
└── theme.yaml    ← Has theme.features: [search, ...] but no features.yaml
```

Result: Search UI appears but doesn't work because no `index.json` is generated.

### User Experience Impact

**Expected**: "My site config has search enabled, search works"

**Actual**: "I have `search.enabled: True` in defaults, `search` in theme.features, but no search index. Why?"

## Design

### Root Cause Analysis

The configuration system has three layers:

| Layer | Source | Applied? |
|-------|--------|----------|
| 1. Bengal Defaults | `defaults.py` DEFAULTS dict | ❌ **Not applied for directory configs** |
| 2. User Config | `config/_default/*.yaml` | ✅ Applied |
| 3. Environment/Profile | `config/environments/*.yaml` | ✅ Applied |

For single-file configs (`bengal.toml`), the `ConfigLoader._default_config()` method returns hardcoded defaults. But for directory-based configs, `ConfigDirectoryLoader` starts with `{}`.

### Proposal: Apply DEFAULTS as Base Layer

**Change `ConfigDirectoryLoader.load()` to start with DEFAULTS instead of empty dict.**

```python
# bengal/config/directory_loader.py

def load(
    self,
    config_dir: Path,
    environment: str | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    """Load configuration with DEFAULTS as base layer."""

    if self.track_origins:
        self.origin_tracker = ConfigWithOrigin()

    if environment is None:
        environment = detect_environment()
        logger.debug("environment_detected", environment=environment)

    # NEW: Start with DEFAULTS as base layer
    from bengal.config.defaults import DEFAULTS
    config = deep_merge({}, DEFAULTS)

    if self.origin_tracker:
        self.origin_tracker.merge(DEFAULTS, "_bengal_defaults")

    # Layer 1: User defaults from _default/
    defaults_dir = config_dir / "_default"
    if defaults_dir.exists():
        default_config = self._load_directory(defaults_dir, _origin_prefix="_default")
        config = deep_merge(config, default_config)
        if self.origin_tracker:
            self.origin_tracker.merge(default_config, "_default")

    # ... rest unchanged ...
```

**Why this approach:**

| Benefit | Explanation |
|---------|-------------|
| **Fixes the real issue** | Directory configs now inherit all defaults |
| **Minimal change** | One line change + import |
| **Backwards compatible** | User config still overrides defaults |
| **Consistent behavior** | Same defaults apply regardless of config mode |
| **Transparent** | `bengal config show --origin` shows `_bengal_defaults` layer |

### Alternative Considered: Implicit Feature Expansion

Auto-enable `index_json` when `search.enabled: True`:

```python
def apply_implicit_features(config: dict) -> dict:
    if get_nested_key(config, "search.enabled", True):
        site_wide = get_nested_key(config, "output_formats.site_wide", [])
        if "index_json" not in site_wide:
            site_wide = list(site_wide) + ["index_json"]
            set_nested_key(config, "output_formats.site_wide", site_wide)
    return config
```

**Rejected because:**
- Adds magic behavior coupling
- Doesn't fix the broader issue (other defaults also not applied)
- More complex than applying DEFAULTS as base layer

## Implementation

### Changes Required

**1. Update `directory_loader.py`:**

```python
# bengal/config/directory_loader.py

from bengal.config.defaults import DEFAULTS
from bengal.config.merge import deep_merge

class ConfigDirectoryLoader:
    def load(
        self,
        config_dir: Path,
        environment: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        # ... existing setup code ...

        # NEW: Start with DEFAULTS as base layer
        config = deep_merge({}, DEFAULTS)

        if self.origin_tracker:
            self.origin_tracker.merge(DEFAULTS, "_bengal_defaults")

        # Layer 1: User defaults from _default/ (overrides DEFAULTS)
        defaults_dir = config_dir / "_default"
        if defaults_dir.exists():
            default_config = self._load_directory(defaults_dir, _origin_prefix="_default")
            config = deep_merge(config, default_config)
            # ... rest unchanged ...
```

**2. Update `ConfigLoader._default_config()` to use DEFAULTS:**

Currently this method has hardcoded values. Update to derive from DEFAULTS for consistency:

```python
def _default_config(self) -> dict[str, Any]:
    """Get default configuration from centralized DEFAULTS."""
    from bengal.config.defaults import DEFAULTS
    return deep_merge({}, DEFAULTS)
```

**3. Add tests:**

```python
def test_directory_config_inherits_defaults():
    """Directory-based configs should inherit from DEFAULTS."""
    loader = ConfigDirectoryLoader()
    # Load from empty _default/ directory
    config = loader.load(empty_config_dir)

    # Should have default output_formats
    assert config["output_formats"]["site_wide"] == ["index_json"]
    assert config["search"]["enabled"] is True

def test_user_config_overrides_defaults():
    """User config should override inherited defaults."""
    loader = ConfigDirectoryLoader()
    # _default/ has output_formats.site_wide: []
    config = loader.load(custom_config_dir)

    assert config["output_formats"]["site_wide"] == []  # User override
```

### Migration

**Non-breaking for existing sites:**

| Site Type | Current Behavior | New Behavior |
|-----------|------------------|--------------|
| `bengal new` sites | Search works | No change |
| Directory config with `features.yaml` | Search works | No change |
| Directory config without `features.yaml` | Search broken | ✅ **Fixed** |
| Explicit `output_formats.site_wide: []` | No index | Still no index (respected) |
| Explicit `search.enabled: false` | Search disabled | Still disabled (respected) |

**If user explicitly doesn't want defaults:**

```yaml
# config/_default/build.yaml
output_formats:
  site_wide: []  # Explicitly disable site-wide outputs
```

## Impact

### Breaking Changes

**None.** This is purely additive:
- Sites that work today continue to work
- Sites missing defaults now get them
- Explicit user config always wins

### Build Performance

**Negligible:**
- `index.json` generation is fast (JSON serialization)
- File is ~10-50KB depending on site size
- Already computed during page processing

### Config Origin Tracking

After this change, `bengal config show --origin` will show:

```
output_formats.site_wide: ["index_json"]
  └─ _bengal_defaults (inherited)

output_formats.site_wide: ["index_json", "rss"]  
  └─ _bengal_defaults (base)
  └─ _default/features.yaml (merged)
```

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| **Search works by default** | Any Bengal site has working search without explicit config |
| **Directory configs get defaults** | `ConfigDirectoryLoader` applies DEFAULTS base layer |
| **Origin tracking works** | `bengal config show --origin` shows `_bengal_defaults` |
| **Overrides work** | User can still disable with explicit config |
| **No breaking changes** | Existing sites build without modification |

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1: Config loader update | 1 hour | Update `directory_loader.py`, `loader.py` |
| 2: Tests | 1 hour | Add inheritance and override tests |
| 3: Documentation | 30 min | Update config docs, clarify `theme.features` vs `features` |
| **Total** | ~2.5 hours | |

## Future Considerations

### Clarify `theme.features` vs `features`

Consider renaming to reduce confusion:
- `theme.features` → `theme.ui_flags` or `theme.components`
- `features` → keep as-is (already clear in context)

Or document prominently that these are separate systems.

### Config Validation Warning

Add a warning when `theme.features` contains `search` but no search index will be generated:

```python
if "search" in theme_features and "index_json" not in site_wide_formats:
    logger.warning(
        "search_ui_without_index",
        suggestion="Add 'features.search: true' or 'output_formats.site_wide: [index_json]'",
    )
```

## References

- Bengal config defaults: `bengal/config/defaults.py`
- Directory config loader: `bengal/config/directory_loader.py`
- Feature mappings: `bengal/config/feature_mappings.py`
- Search index generation: `bengal/postprocess/output_formats/index_generator.py`
- New site config creation: `bengal/cli/commands/new/config.py`
- Discovered via: Rosettes site missing search despite `theme.features: [search, ...]`
