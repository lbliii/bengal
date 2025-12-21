# Complete Bengal Configuration Inventory

**Status**: Ready for Deletion ✅  
**Created**: 2025-12-02  
**Last Updated**: 2025-12-21  
**Purpose**: Document ALL config keys, their sources, defaults, and issues

---

## Executive Summary

**Most work in this RFC is complete.** The configuration system has been significantly improved:

- ✅ Centralized `bengal/config/defaults.py` with 300+ lines of config defaults
- ✅ `get_max_workers()` auto-detection adopted in 6+ files (0 hardcoded `4` values remain)
- ✅ Bool/dict normalization via `normalize_bool_or_dict()`
- ✅ Deprecation system with migration helpers
- ✅ All missing sections added to `KNOWN_SECTIONS`

**Remaining work is minor** and can be tracked as separate issues if desired.

---

## ✅ Completed Work

### 1. Centralized Config Defaults

Created `bengal/config/defaults.py` with:
- Comprehensive `DEFAULTS` dictionary covering all config sections
- `get_max_workers()` - auto-detects CPU count (leaves 1 core, min 4 workers)
- `get_pagination_per_page()` - centralized pagination default
- `normalize_bool_or_dict()` - standardizes bool/dict config handling
- `is_feature_enabled()` / `get_feature_config()` - feature flag helpers

**Adoption verified:**
- `get_max_workers()` used in 6 files: `render.py`, `taxonomy.py`, `asset.py`, `related_posts.py`, `content_discovery.py`, `validators/config.py`
- `is_feature_enabled()` / `get_feature_config()` used in 6 files
- Zero remaining hardcoded `max_workers = 4` values

### 2. KNOWN_SECTIONS Updated

All sections now registered in `ConfigLoader.KNOWN_SECTIONS`:

```python
KNOWN_SECTIONS = {
    # Core
    "site", "build", "build_badge", "theme", "params",
    # Content
    "content", "markdown", "taxonomies",
    # Features
    "features", "search", "graph",
    # Navigation
    "menu", "pagination",
    # Output
    "output_formats", "assets",
    # Development
    "dev", "health_check",
    # Integrations
    "fonts", "autodoc", "i18n",
    # Versioning
    "versioning",
}
```

### 3. Deprecation System

Created `bengal/config/deprecation.py` with:
- `DEPRECATED_KEYS` mapping old → new config locations
- `check_deprecated_keys()` - warns on deprecated usage
- `migrate_deprecated_keys()` - auto-migration helper
- `print_deprecation_warnings()` - user-friendly console output
- `get_deprecation_summary()` - markdown summary for docs

**Deprecated keys tracked:**
| Old Key | New Location |
|---------|-------------|
| `minify_assets` | `assets.minify` |
| `optimize_assets` | `assets.optimize` |
| `fingerprint_assets` | `assets.fingerprint` |
| `generate_sitemap` | `features.sitemap` |
| `generate_rss` | `features.rss` |
| `markdown_engine` | `content.markdown_parser` |
| `validate_links` | `health.linkcheck.enabled` |

### 4. Bool/Dict Normalization

Features like `health_check`, `search`, `graph`, `output_formats` now consistently handle both:
- Boolean: `health_check: false`
- Dict: `health_check: { enabled: true, verbose: true }`

---

## ⏳ Minor Remaining Items

### 1. Pagination Default Duplication (Low Priority)

`per_page = 10` still appears in 6 files (10 matches total). Could adopt `get_pagination_per_page()` but impact is minimal.

**Files:** `pagination.py`, `pagination_helpers.py`, `taxonomy.py`, `section.py`, `link_suggestions.py`, `knowledge_graph.py`

### 2. Excerpt Length Duplication (Low Priority)

`excerpt_length = 200` appears in 3 files. Could centralize but impact is minimal.

**Files:** `json_generator.py`, `index_generator.py`, `output_formats/__init__.py`

### 3. Long-Term Ideas (Not Started)

These are aspirational and can be separate RFCs if pursued:

- **Config schema validation**: JSON Schema or pydantic for early error detection
- **Config-based profiles**: Allow `build.profile: theme-dev` in config (currently CLI-only)
- **Auto-generated config docs**: Derive reference docs from code annotations

---

## Recommendation

**Delete this RFC.** Core objectives achieved:

1. ✅ Single source of truth for defaults (`defaults.py`)
2. ✅ Auto-detecting worker count
3. ✅ Deprecation warnings for legacy keys
4. ✅ Bool/dict normalization
5. ✅ All sections registered

**Changelog entry:**

```markdown
## Configuration System Cleanup

- Created `bengal/config/defaults.py` with centralized defaults and helper functions
- Added `get_max_workers()` auto-detection (CPU count - 1, min 4)
- Added deprecation system for legacy config keys with migration helpers
- Standardized bool/dict config handling via `normalize_bool_or_dict()`
- Registered all config sections in `KNOWN_SECTIONS`
```

---

## Reference: Current Config Structure

For historical reference, the full config structure is documented in the `DEFAULTS` dict in `bengal/config/defaults.py`.

### Config Sections (17 total)

| Section | Purpose |
|---------|---------|
| `site` | Site metadata (title, baseurl, author) |
| `build` | Build options (output_dir, parallel, incremental) |
| `theme` | Theme settings (appearance, palette, features) |
| `content` | Content processing (excerpt_length, toc_depth) |
| `markdown` | Markdown parser config |
| `features` | Feature toggles (rss, sitemap, search) |
| `search` | Search configuration |
| `graph` | Knowledge graph settings |
| `menu` | Navigation menus |
| `pagination` | Pagination settings |
| `assets` | Asset processing |
| `output_formats` | Output format options |
| `health_check` | Health check configuration |
| `fonts` | Font configuration |
| `autodoc` | API documentation generator |
| `i18n` | Internationalization |
| `params` | Custom user parameters |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `BENGAL_BASEURL` | Override baseurl |
| `BENGAL_RAISE_ON_CONFIG_ERROR` | Raise on config errors |
| `BENGAL_DEV_SERVER` | Mark as dev server mode |
| `BENGAL_WATCHDOG_BACKEND` | Filesystem watcher backend |
| `BENGAL_DEBOUNCE_MS` | Build debounce time |
