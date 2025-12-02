# RFC: Config Defaults Cleanup

**Status**: Draft  
**Created**: 2025-12-02  
**Priority**: Medium  
**Est. Impact**: Better DX, fewer "gotcha" moments

---

## Problem Statement

Bengal's configuration system has several "sharp edges" that cause unexpected behavior:

1. **Hard-coded defaults that should auto-detect** (`max_workers: 4`)
2. **Config in multiple places with confusing overrides** (`health_check`)
3. **Inconsistent naming** (`minify_assets` vs `assets.minify`)
4. **Scattered defaults** (no single source of truth)

---

## Issues Found

### Issue 1: `max_workers` Hard-coded to 4

**Current**: 6 places hard-code `max_workers` default to 4:

```python
# render.py, taxonomy.py, related_posts.py
max_workers = self.site.config.get("max_workers", 4)
```

**Problem**: Users with 11+ cores get 4 workers unless they explicitly set `max_workers: null`.

**Fix**: Default to `None` → auto-detect:

```python
def get_max_workers(config: dict) -> int:
    """Get max_workers with smart auto-detection."""
    configured = config.get("max_workers")
    if configured is None:
        return os.cpu_count() or 4
    return configured
```

### Issue 2: `health_check` in Multiple Places

**Current**: Can be in `build.yaml` AND `environments/*.yaml`:

```yaml
# config/_default/build.yaml
health_check: false  # <-- User sets this

# config/environments/local.yaml  
health_check:
  verbose: true  # <-- Overrides the false!
```

**Problem**: Dict overrides boolean, user thinks health checks are disabled but they're not.

**Fix Options**:
- A) Only allow `health_check` in one file
- B) Smarter merge: `health_check: false` should win over `health_check: { ... }`
- C) Require explicit `enabled: false` in the dict form

### Issue 3: Inconsistent Config Key Naming

**Current**:
```python
# Some use flat keys
minify = self.site.config.get("minify_assets", True)
fingerprint = self.site.config.get("fingerprint_assets", True)

# Some use nested
assets_cfg = self.site.config.get("assets", {})
minify = assets_cfg.get("minify", True)
```

**Problem**: Users don't know which to set:
- `minify_assets: false` (flat)
- `assets.minify: false` (nested)

**Fix**: Standardize on nested structure, deprecate flat keys:

```yaml
# Canonical form
assets:
  minify: false
  fingerprint: true

# Deprecated (show warning)
minify_assets: false  # ⚠️ Deprecated, use assets.minify
```

### Issue 4: No Single Source of Truth for Defaults

**Current**: Defaults scattered across:
- Code: `config.get("key", 4)`
- Config files: `_default/*.yaml`
- CLI: `@click.option(..., default=...)`
- Profiles: `utils/profile.py`

**Problem**: Changing a default requires updating multiple places.

**Fix**: Create `bengal/config/defaults.py`:

```python
# bengal/config/defaults.py
"""Single source of truth for all config defaults."""

DEFAULTS = {
    "build": {
        "parallel": True,
        "incremental": True,
        "max_workers": None,  # Auto-detect
    },
    "assets": {
        "minify": True,
        "fingerprint": True,
        "optimize": True,
    },
    "health_check": {
        "enabled": True,
        "verbose": False,
    },
    "pagination": {
        "per_page": 10,
    },
}

def get_default(key_path: str) -> Any:
    """Get default value for a config key path like 'build.max_workers'."""
    ...
```

---

## Implementation Plan

### Phase 1: Fix `max_workers` (Day 1)
- [ ] Create `get_max_workers()` utility function
- [ ] Replace all 6 hard-coded defaults
- [ ] Remove `max_workers: null` requirement from docs

### Phase 2: Fix `health_check` Merge (Day 1)
- [ ] Update config loader to handle bool/dict merge properly
- [ ] Add warning when conflicting settings detected
- [ ] Document expected behavior

### Phase 3: Standardize Config Keys (Day 2)
- [ ] Create deprecation warnings for flat keys
- [ ] Update code to prefer nested structure
- [ ] Update docs/examples

### Phase 4: Create Defaults Module (Day 2-3)
- [ ] Create `bengal/config/defaults.py`
- [ ] Update all `config.get()` calls to use defaults module
- [ ] Add tests for default resolution

---

## Migration Path

### For `max_workers`
No user action needed - auto-detect becomes default.

### For `health_check`
Users with `health_check: false` + `health_check: { verbose: true }` will get a warning:

```
⚠️ Config conflict: health_check set to false in build.yaml but
   has settings in local.yaml. Using enabled: false.
```

### For Asset Config Keys
Deprecation warning for 2 releases:

```
⚠️ Deprecated: 'minify_assets' - use 'assets.minify' instead
```

---

## Affected Files

- `bengal/orchestration/render.py` (3 occurrences)
- `bengal/orchestration/taxonomy.py` (1 occurrence)
- `bengal/orchestration/related_posts.py` (1 occurrence)
- `bengal/orchestration/asset.py` (1 occurrence + naming issue)
- `bengal/orchestration/build/finalization.py` (health_check)
- `bengal/config/loader.py` (merge logic)

---

## Success Criteria

- [ ] `max_workers` auto-detects without config
- [ ] `health_check: false` works regardless of environment files
- [ ] Deprecated flat config keys show warnings
- [ ] All defaults in single module

---

## Appendix: Full List of Hard-coded Defaults

| Key | Default | Files | Should Be |
|-----|---------|-------|-----------|
| `max_workers` | 4 | 6 files | `os.cpu_count()` |
| `pagination.per_page` | 10 | 3 files | Central default |
| `minify_assets` | True | 1 file | `assets.minify` |
| `fingerprint_assets` | True | 1 file | `assets.fingerprint` |
| `optimize_assets` | True | 1 file | `assets.optimize` |
| `generate_sitemap` | True | 1 file | Central default |
| `generate_rss` | True | 1 file | Central default |
| `cache_templates` | True | 1 file | Central default |
| `transform_links` | True | 1 file | Central default |
