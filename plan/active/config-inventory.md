# Complete Bengal Configuration Inventory

**Status**: Investigation Complete  
**Created**: 2025-12-02  
**Purpose**: Document ALL config keys, their sources, defaults, and issues

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Top-level sections | 17 |
| Total config keys | ~120 |
| Hard-coded defaults | 47 |
| Documented in yaml | ~50 |
| Undocumented | ~30 |
| Duplicate defaults | 12 |

---

## Config Structure

### Known Sections (from `ConfigLoader.KNOWN_SECTIONS`)

```python
KNOWN_SECTIONS = {
    "site",           # Site metadata
    "build",          # Build options
    "markdown",       # Markdown parser config
    "features",       # Feature toggles
    "taxonomies",     # Taxonomy config
    "menu",           # Navigation menus
    "params",         # Custom parameters
    "assets",         # Asset processing
    "pagination",     # Pagination settings
    "dev",            # Development options
    "output_formats", # Output format options
    "health_check",   # Health check config
    "fonts",          # Font configuration
    "theme",          # Theme settings
}
```

**Additional sections found in code but not in KNOWN_SECTIONS**:
- `search` - Search configuration
- `content` - Content processing
- `autodoc` - API documentation
- `i18n` - Internationalization
- `graph` - Knowledge graph
- `rss` - RSS feed settings

---

## Complete Config Reference

### 1. Site Section (`site:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `title` | string | `"Bengal Site"` | loader.py | Site title |
| `baseurl` | string | `""` | loader.py | Base URL for links |
| `description` | string | `""` | - | Site description |
| `author` | string | `""` | - | Site author |
| `language` | string | `"en"` | - | Site language |
| `favicon` | string | - | templates | Path to favicon |
| `logo_image` | string | - | templates | Logo image path |
| `logo_text` | string | - | templates | Logo text |
| `og_image` | string | - | templates | Default OG image |

**Issues**:
- `logo_image` accessible via BOTH `site.config.get('logo_image')` AND `site.config.get('site', {}).get('logo_image')`

---

### 2. Build Section (`build:`)

| Key | Type | Default | Source | Duplicated In | Notes |
|-----|------|---------|--------|---------------|-------|
| `output_dir` | string | `"public"` | loader.py | - | Output directory |
| `content_dir` | string | `"content"` | loader.py | - | Content directory |
| `assets_dir` | string | `"assets"` | loader.py | - | Assets directory |
| `templates_dir` | string | `"templates"` | loader.py | - | Templates directory |
| `parallel` | bool | `True` | loader.py | validators.py | Enable parallelism |
| `incremental` | bool | `True` | loader.py | validators.py | Incremental builds |
| `max_workers` | int | `4` ⚠️ | **6 files!** | render.py, taxonomy.py, etc | **SHOULD AUTO-DETECT** |
| `pretty_urls` | bool | `True` | loader.py | validators.py | Pretty URL structure |
| `minify_html` | bool | `True` | loader.py | feature_mappings.py | Minify HTML output |
| `strict_mode` | bool | `False` | loader.py | validators.py | Fail on errors |
| `debug` | bool | `False` | loader.py | validators.py | Debug mode |
| `validate_build` | bool | `True` | loader.py | - | Run health checks |
| `validate_links` | bool | `True` | loader.py | validators.py | Validate links |
| `transform_links` | bool | `True` | link_transformer.py | - | Transform relative links |
| `cache_templates` | bool | `True` | template_engine.py | - | Cache Jinja templates |
| `fast_writes` | bool | `False` | pipeline.py | - | Skip atomic writes |
| `stable_section_references` | bool | `True` | loader.py | validators.py | Path-based section refs |
| `min_page_size` | int | `1000` | loader.py | - | Min expected page size |

**Issues**:
- ⚠️ `max_workers` hard-coded to 4 in 6 different files
- `parallel`, `incremental` duplicated in validators

**Undocumented keys in build section**:
- `fast_mode` (bool, default `False`) - Skip non-essential processing
- `fast_writes` (bool, default `False`) - Skip atomic file writes

---

### 3. HTML Output (`html_output:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `mode` | string | `"minify"` | loader.py | `minify|pretty|raw` |
| `remove_comments` | bool | `True` | loader.py | Remove HTML comments |
| `collapse_blank_lines` | bool | `True` | loader.py | Collapse whitespace |

---

### 4. Assets Section (`assets:`)

| Key | Type | Default | Source | Also As | Notes |
|-----|------|---------|--------|---------|-------|
| `minify` | bool | `True` | loader.py | `minify_assets` | Minify assets |
| `optimize` | bool | `True` | loader.py | `optimize_assets` | Optimize assets |
| `fingerprint` | bool | `True` | loader.py | `fingerprint_assets` | Add fingerprints |
| `pipeline` | bool | `False` | asset.py | - | Use asset pipeline |

**Issues**:
- ⚠️ Dual naming: `assets.minify` AND `minify_assets` both work
- Code uses `minify_assets` pattern in some places

---

### 5. Theme Section (`theme:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `name` | string | `"default"` | loader.py, theme.py | Theme name |
| `default_appearance` | string | `"system"` | loader.py, theme.py | `light|dark|system` |
| `default_palette` | string | `""` | loader.py, theme.py | Palette key |
| `features` | list | `[]` | theme.py | Theme features |
| `show_reading_time` | bool | `True` | theme.yaml | Display reading time |
| `show_author` | bool | `True` | theme.yaml | Display author |
| `show_prev_next` | bool | `True` | theme.yaml | Prev/next navigation |
| `show_children_default` | bool | `True` | theme.yaml | Show child pages |
| `show_excerpts_default` | bool | `True` | theme.yaml | Show excerpts |
| `max_tags_display` | int | `10` | theme.yaml | Max tags before "+N more" |
| `popular_tags_count` | int | `20` | theme.yaml | Tags in widget |

---

### 6. Search Section (`search:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `enabled` | bool | `True` | search.yaml | Enable search |
| `lunr.prebuilt` | bool | `True` | lunr_index_generator.py | Pre-build index |
| `lunr.min_query_length` | int | `2` | search.yaml | Min query length |
| `lunr.max_results` | int | `50` | search.yaml | Max results |
| `lunr.preload` | string | `"smart"` | search.yaml | `immediate|smart|lazy` |
| `ui.modal` | bool | `True` | search.yaml | Enable Cmd+K |
| `ui.recent_searches` | int | `5` | search.yaml | Recent search count |
| `ui.placeholder` | string | `"Search..."` | search.yaml | Placeholder text |
| `analytics.enabled` | bool | `False` | search.yaml | Search analytics |
| `analytics.event_endpoint` | string | `null` | search.yaml | Analytics endpoint |

**Issues**:
- `search_preload` used in templates (should be `search.lunr.preload`)

---

### 7. Content Section (`content:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `default_type` | string | `"doc"` | content.yaml | Default content type |
| `excerpt_length` | int | `200` | content.yaml, new/config.py | Excerpt chars |
| `summary_length` | int | `160` | content.yaml | Meta description chars |
| `reading_speed` | int | `200` | content.yaml, new/config.py | Words per minute |
| `related_count` | int | `5` | content.yaml, new/config.py | Related pages count |
| `related_threshold` | float | `0.25` | content.yaml | Min similarity |
| `toc_depth` | int | `4` | content.yaml, new/config.py | Max heading depth |
| `toc_min_headings` | int | `2` | content.yaml | Min headings for TOC |
| `toc_style` | string | `"nested"` | content.yaml | `nested|flat` |
| `sort_pages_by` | string | `"weight"` | content.yaml | `weight|date|title|modified` |
| `sort_order` | string | `"asc"` | content.yaml | `asc|desc` |

**Issues**:
- Duplicated defaults in `cli/commands/new/config.py`

---

### 8. Features Section (`features:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `rss` | bool | `True` | features.yaml | Generate RSS |
| `sitemap` | bool | `True` | features.yaml | Generate sitemap |
| `search` | bool | `True` | features.yaml | Generate search index |
| `json` | bool | `True` | features.yaml | Per-page JSON |
| `llm_txt` | bool | `True` | features.yaml | LLM-friendly text |
| `syntax_highlighting` | bool | `True` | features.yaml | Code highlighting |

**Also accessible as top-level** (legacy):
- `generate_sitemap` (→ `features.sitemap`)
- `generate_rss` (→ `features.rss`)

---

### 9. Pagination Section (`pagination:`)

| Key | Type | Default | Source | Duplicated In | Notes |
|-----|------|---------|--------|---------------|-------|
| `per_page` | int | `10` | taxonomy.py, section.py | 3 files | Items per page |

**Issues**:
- ⚠️ Duplicated default (10) in multiple files

---

### 10. Menu Section (`menu:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `main` | list | - | menu.py | Main navigation |
| `footer` | list | - | - | Footer navigation |
| `sidebar` | list | - | - | Sidebar navigation |

Menu item structure:
```yaml
menu:
  main:
    - name: "Home"
      url: "/"
      weight: 0
      parent: null  # Optional
```

---

### 11. i18n Section (`i18n:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `strategy` | string | - | various | `prefix` for URL prefix |
| `default_language` | string | `"en"` | various | Default language |
| `default_in_subdir` | bool | `False` | various | Default lang in subdir |

---

### 12. Output Formats (`output_formats:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `enabled` | bool | `True` | postprocess.py | Enable output formats |
| `per_page` | list | `["json"]` | __init__.py | Per-page formats |
| `site_wide` | list | `["index_json"]` | __init__.py | Site-wide formats |
| `options.json` | bool | `False` | __init__.py | JSON output |
| `options.llm_txt` | bool | `False` | __init__.py | LLM text output |
| `options.site_json` | bool | `False` | __init__.py | Site JSON index |
| `options.site_llm` | bool | `False` | __init__.py | Full LLM text |
| `options.excerpt_length` | int | `200` | __init__.py | Excerpt length |
| `options.json_indent` | int | - | __init__.py | JSON indentation |
| `options.llm_separator_width` | int | `80` | __init__.py | LLM separator width |
| `options.include_full_content_in_index` | bool | `False` | __init__.py | Full content in index |
| `options.exclude_sections` | list | `[]` | __init__.py | Sections to exclude |
| `options.exclude_patterns` | list | `["404.html", "search.html"]` | __init__.py | Patterns to exclude |

---

### 13. Health Check (`health_check:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `enabled` | bool | `True` | finalization.py | Enable health checks |
| `verbose` | bool | `False` | finalization.py | Verbose output |
| `strict_mode` | bool | `False` | finalization.py | Fail on errors |
| `orphan_threshold` | int | `5` | connectivity.py | Orphan page warning threshold |
| `super_hub_threshold` | int | `50` | connectivity.py | Super hub warning threshold |

**Issues**:
- ⚠️ Can be bool (`health_check: false`) OR dict (`health_check: { enabled: false }`)
- Dict overrides bool when in different files!

---

### 14. Fonts Section (`fonts:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `<name>.family` | string | - | fonts/__init__.py | Font family |
| `<name>.weights` | list | `[400]` | fonts/__init__.py | Font weights |
| `<name>.styles` | list | `["normal"]` | fonts/__init__.py | Font styles |

---

### 15. Autodoc Section (`autodoc:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `github_repo` | string | - | autodoc.yaml | GitHub repo (owner/repo) |
| `github_branch` | string | `"main"` | autodoc.yaml | Git branch |
| `default_description` | string | - | autodoc.yaml | Default description |
| `python.enabled` | bool | `True` | autodoc.yaml | Enable Python docs |
| `python.source_dirs` | list | - | autodoc.yaml | Source directories |
| `python.output_dir` | string | `"content/api"` | autodoc.yaml | Output directory |
| `python.docstring_style` | string | `"auto"` | autodoc.yaml | Docstring style |
| `python.exclude` | list | `[]` | autodoc.yaml | Exclusion patterns |
| `python.include_private` | bool | `False` | autodoc.yaml | Include _private |
| `python.include_special` | bool | `False` | autodoc.yaml | Include __special__ |
| `python.display_name` | string | `"API Reference"` | autodoc.py | Section title |
| `cli.enabled` | bool | `False` | autodoc.yaml | Enable CLI docs |
| `cli.app_module` | string | - | autodoc.yaml | CLI module path |
| `cli.framework` | string | `"click"` | autodoc.yaml | CLI framework |
| `cli.output_dir` | string | `"content/cli"` | autodoc.yaml | Output directory |
| `cli.display_name` | string | `"CLI Reference"` | autodoc.py | Section title |
| `cli.include_hidden` | bool | `False` | autodoc.py | Include hidden commands |
| `openapi.enabled` | bool | `False` | - | Enable OpenAPI docs |
| `openapi.spec_file` | string | - | - | OpenAPI spec path |

---

### 16. Graph Section (`graph:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `enabled` | bool | `True` | postprocess.py, special_pages.py | Enable graph |
| `path` | string | `"/graph/"` | special_pages.py | Graph page path |

---

### 17. Markdown Section (`markdown:`)

| Key | Type | Default | Source | Notes |
|-----|------|---------|--------|-------|
| `parser` | string | `"mistune"` | pipeline.py | Parser engine |
| `engine` | string | - | metadata.py | Legacy (→ parser) |
| `toc_depth` | string | `"2-4"` | python_markdown.py | TOC depth range |

---

### 18. Params Section (`params:`)

Custom user-defined parameters accessible in templates as `site.config.params.*`.

---

### 19. Dev Section (`dev:`)

Development-only settings (not well documented).

---

### 20. Build Profiles (CLI-based, not config file)

Profiles determine health checks and metrics collection via CLI flags, NOT config files.

| Profile | CLI Flags | Health Checks | Metrics | Memory |
|---------|-----------|---------------|---------|--------|
| `WRITER` | (default) | config, output, links, directives | ❌ | ❌ |
| `THEME_DEV` | `--verbose` | + rendering, navigation, menu | ✅ | ❌ |
| `DEVELOPER` | `--dev` | ALL | ✅ | ✅ |

**Profile selection priority**:
1. `--dev` → DEVELOPER
2. `--theme-dev` → THEME_DEV
3. `--profile=X` → X
4. `--verbose` → THEME_DEV
5. `--debug` → DEVELOPER
6. Default → WRITER

**Profile config keys** (from `profile.get_config()`):
- `show_phase_timing` (bool)
- `track_memory` (bool)
- `enable_debug_output` (bool)
- `collect_metrics` (bool)
- `health_checks.enabled` (list or "all")
- `health_checks.disabled` (list)
- `verbose_build_stats` (bool)
- `verbose_console_logs` (bool)
- `live_progress.enabled` (bool)
- `live_progress.show_recent_items` (bool)
- `live_progress.show_metrics` (bool)
- `live_progress.max_recent` (int)

**Issues**:
- ⚠️ `--verbose` causes THEME_DEV profile (not just verbose output)
- ⚠️ Profile health checks can be overridden by `health_check:` in config
- ⚠️ No way to specify profile in config file (CLI only)

---

## Issues Summary

### 1. Duplicated Defaults (Should be centralized)

| Key | Default | Files |
|-----|---------|-------|
| `max_workers` | `4` | render.py (3x), taxonomy.py, related_posts.py, asset.py |
| `pagination.per_page` | `10` | taxonomy.py (2x), section.py |
| `excerpt_length` | `200` | content.yaml, new/config.py (5x), __init__.py |
| `reading_speed` | `200` | content.yaml, new/config.py (3x) |

### 2. Inconsistent Naming

| Flat Key | Nested Key | Notes |
|----------|------------|-------|
| `minify_assets` | `assets.minify` | Both work, confusing |
| `fingerprint_assets` | `assets.fingerprint` | Both work |
| `optimize_assets` | `assets.optimize` | Both work |
| `generate_sitemap` | `features.sitemap` | Legacy vs modern |
| `generate_rss` | `features.rss` | Legacy vs modern |
| `search_preload` | `search.lunr.preload` | Template uses wrong key |

### 3. Missing from KNOWN_SECTIONS

- `search`
- `content`
- `autodoc`
- `i18n`
- `graph`
- `rss` (if separate from features)

### 4. Bool/Dict Confusion

Keys that accept BOTH bool AND dict:
- `health_check`
- `search`
- `graph`
- `output_formats`

### 5. Undocumented Config Keys

- `expose_metadata` (minimal|standard|extended)
- `expose_metadata_json`
- `dev_server` (internal, set by server)
- `fast_writes`
- `transform_links`
- `cache_templates`
- Many `output_formats.options.*` keys

---

## Recommendations

1. **Create `bengal/config/defaults.py`** - Single source of truth
2. **Fix `max_workers`** - Default to `os.cpu_count()` not `4`
3. **Add missing sections to `KNOWN_SECTIONS`**
4. **Standardize bool/dict handling** - Consistent merge behavior
5. **Deprecate flat asset keys** - Use `assets.*` only
6. **Document all keys** - Generate from code, not manually
7. **Add config schema validation** - JSON Schema or similar
