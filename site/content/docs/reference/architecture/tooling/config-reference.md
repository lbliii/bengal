---
title: Config Reference
nav_title: Config Reference
description: Auto-generated reference of all configuration options and defaults
weight: 25
---

# Config Reference

This page is **auto-generated** from `bengal.config.defaults.DEFAULTS`.
Do not edit manually. Run `poe gen-docs` or `poe build` to regenerate.

## Top-Level Keys

| Key | Description |
|-----|-------------|
| `assets` | Asset processing (minify, optimize, fingerprint) |
| `build` | Build settings (output_dir, parallel, incremental, pretty_urls) |
| `connect_to_ide` | Cursor MCP one-click install |
| `content` | Content processing (excerpt, TOC, sorting) |
| `content_signals` | AI/crawler content policy |
| `dev` | Development server (port, live_reload, watch) |
| `document_application` | View Transitions, speculation rules |
| `external_refs` | Cross-project documentation links |
| `features` | Feature toggles (rss, sitemap, search, json) |
| `graph` | Graph visualization |
| `health_check` | Health validators and thresholds |
| `html_output` | HTML formatting (mode, remove_comments) |
| `i18n` | Internationalization |
| `link_previews` | Wikipedia-style hover cards |
| `markdown` | Markdown parser (patitas, toc_depth) |
| `output_formats` | Output formats (JSON, llm_txt, changelog) |
| `pagination` | Pagination (per_page) |
| `search` | Search configuration (Lunr, UI, analytics) |
| `site` | Site metadata (title, baseurl, author, language) |
| `static` | Static files (enabled, dir) |
| `structured_data` | Schema.org JSON-LD |
| `theme` | Theme settings (name, syntax highlighting, features) |

## Default Values by Section

### `assets`

- **`fingerprint`**: `true`
- **`minify`**: `true`
- **`optimize`**: `true`
- **`pipeline`**: `false`

### `build`

- **`assets_dir`**: `"assets"`
- **`content_dir`**: `"content"`
- **`debug`**: `false`
- **`fast_mode`**: `false`
- **`fast_writes`**: `false`
- **`incremental`**: `null`
- **`max_workers`**: `null`
- **`min_page_size`**: 1000
- **`minify_html`**: `true`
- **`output_dir`**: `"public"`
- **`parallel`**: `true`
- **`parallel_autodoc`**: `true`
- **`parallel_graph`**: `true`
- **`pretty_urls`**: `true`
- **`stable_section_references`**: `true`
- **`strict_mode`**: `false`
- **`templates_dir`**: `"templates"`
- **`track_dependency_ordering`**: `true`
- **`transform_links`**: `true`
- **`validate_build`**: `true`
- **`validate_links`**: `true`
- **`validate_templates`**: `false`

### `connect_to_ide`

- **`enabled`**: `false`
- **`mcp_url`**: `""`
- **`server_name`**: `"Docs"`

### `content`

- **`default_type`**: `"doc"`
- **`excerpt_length`**: 750
- **`excerpt_words`**: 150
- **`reading_speed`**: 200
- **`related_count`**: 5
- **`related_threshold`**: 0.25
- **`sort_order`**: `"asc"`
- **`sort_pages_by`**: `"weight"`
- **`summary_length`**: 160
- **`toc_depth`**: 4
- **`toc_min_headings`**: 2
- **`toc_style`**: `"nested"`

### `content_signals`

- **`ai_input`**: `true`
- **`ai_train`**: `false`
- **`enabled`**: `true`
- **`include_sitemap`**: `true`
- **`search`**: `true`
- **`user_agents`**: *object* (1 keys)
  - `*`: `null`

### `dev`

- **`cache_templates`**: `true`
- **`live_reload`**: `true`
- **`port`**: 8000
- **`watch_backend`**: `true`

### `document_application`

- **`enabled`**: `true`
- **`interactivity`**: *object* (6 keys)
  - `accordions`: `"native_details"`
  - `code_copy`: `"enhanced"`
  - `dropdowns`: `"popover"`
  - `modals`: `"native_dialog"`
  - `tabs`: `"css_state_machine"`
  - `tooltips`: `"popover"`
- **`navigation`**: *object* (3 keys)
  - `scroll_restoration`: `true`
  - `transition_style`: `"crossfade"`
  - `view_transitions`: `false`
- **`speculation`**: *object* (5 keys)
  - `auto_generate`: `true`
  - `enabled`: `true`
  - `exclude_patterns`: []
  - `prefetch`: *object* (2 keys)
  - `prerender`: *object* (2 keys)

### `external_refs`

- **`cache_dir`**: `".bengal/cache/external_refs"`
- **`default_cache_days`**: 7
- **`enabled`**: `true`
- **`export_index`**: `false`
- **`indexes`**: []
- **`templates`**: *object* (9 keys)
  - `fastapi`: `"https://fastapi.tiangolo.com/reference/{module}/#{name}"`
  - `httpx`: `"https://www.python-httpx.org/api/#{name_lower}"`
  - `numpy`: `"https://numpy.org/doc/stable/reference/generated/numpy.{name}.html"`
  - `pandas`: `"https://pandas.pydata.org/docs/reference/api/pandas.{name}.html"`
  - `pydantic`: `"https://docs.pydantic.dev/latest/api/{module}/#{name}"`
  - `python`: `"https://docs.python.org/3/library/{module}.html#{name}"`
  - `requests`: `"https://requests.readthedocs.io/en/latest/api/#{name}"`
  - `sqlalchemy`: `"https://docs.sqlalchemy.org/en/20/core/{module}.html#{name}"`
  - `typing`: `"https://docs.python.org/3/library/typing.html#{name}"`

### `features`

- **`json`**: `true`
- **`llm_txt`**: `true`
- **`rss`**: `true`
- **`search`**: `true`
- **`sitemap`**: `true`

### `graph`

- **`enabled`**: `true`
- **`path`**: `"/graph/"`

### `health_check`

- **`build_validators`**: [`"config"`, `"output"`, `"directives"`, `"links"`, `"rendering"`, ... (9 total)]
- **`ci_validators`**: [`"rss"`, `"sitemap"`, `"fonts"`, `"assets"`]
- **`connectivity_thresholds`**: *object* (3 keys)
  - `adequately_linked`: 1.0
  - `lightly_linked`: 0.25
  - `well_connected`: 2.0
- **`enabled`**: `true`
- **`full_validators`**: [`"connectivity"`, `"performance"`, `"cache"`]
- **`isolated_threshold`**: 5
- **`lightly_linked_threshold`**: 20
- **`link_weights`**: *object* (6 keys)
  - `explicit`: 1.0
  - `menu`: 10.0
  - `related`: 0.75
  - `sequential`: 0.25
  - `taxonomy`: 1.0
  - `topical`: 0.5
- **`orphan_threshold`**: 5
- **`strict_mode`**: `false`
- **`super_hub_threshold`**: 50
- **`verbose`**: `false`

### `html_output`

- **`collapse_blank_lines`**: `true`
- **`mode`**: `"minify"`
- **`remove_comments`**: `true`

### `i18n`

- **`default_in_subdir`**: `false`
- **`default_language`**: `"en"`
- **`strategy`**: `null`

### `link_previews`

- **`allowed_hosts`**: []
- **`allowed_schemes`**: [`"https"`]
- **`enabled`**: `true`
- **`exclude_selectors`**: [`"nav"`, `".toc"`, `".breadcrumb"`, `".pagination"`, `".card"`, ... (10 total)]
- **`hide_delay`**: 150
- **`host_failure_threshold`**: 3
- **`hover_delay`**: 200
- **`include_selectors`**: [`".prose"`]
- **`max_tags`**: 3
- **`show_date`**: `true`
- **`show_dead_links`**: `true`
- **`show_reading_time`**: `true`
- **`show_section`**: `true`
- **`show_tags`**: `true`
- **`show_word_count`**: `true`

### `markdown`

- **`ast_cache`**: *object* (1 keys)
  - `persist_tokens`: `false`
- **`parser`**: `"patitas"`
- **`toc_depth`**: `"2-4"`

### `output_formats`

- **`enabled`**: `true`
- **`options`**: *object* (7 keys)
  - `excerpt_length`: 200
  - `exclude_patterns`: [`"404.html"`, `"search.html"`]
  - `exclude_sections`: []
  - `include_chunks`: `true`
  - `include_full_content_in_index`: `false`
  - `json_indent`: `null`
  - `llm_separator_width`: 80
- **`per_page`**: [`"json"`]
- **`site_wide`**: [`"index_json"`, `"llms_txt"`, `"changelog"`, `"agent_manifest"`]

### `pagination`

- **`per_page`**: 10

### `search`

- **`analytics`**: *object* (2 keys)
  - `enabled`: `false`
  - `event_endpoint`: `null`
- **`enabled`**: `true`
- **`lunr`**: *object* (4 keys)
  - `max_results`: 50
  - `min_query_length`: 2
  - `prebuilt`: `true`
  - `preload`: `"smart"`
- **`ui`**: *object* (3 keys)
  - `modal`: `true`
  - `placeholder`: `"Search documentation..."`
  - `recent_searches`: 5

### `site`

- **`author`**: `""`
- **`baseurl`**: `""`
- **`description`**: `""`
- **`language`**: `"en"`
- **`title`**: `"Bengal Site"`

### `static`

- **`dir`**: `"static"`
- **`enabled`**: `true`

### `structured_data`

- **`article`**: `true`

### `theme`

- **`default_appearance`**: `"system"`
- **`default_palette`**: `"snow-lynx"`
- **`features`**: []
- **`max_tags_display`**: 10
- **`name`**: `"default"`
- **`popular_tags_count`**: 20
- **`show_author`**: `true`
- **`show_children_default`**: `true`
- **`show_excerpts_default`**: `true`
- **`show_prev_next`**: `true`
- **`show_reading_time`**: `true`
- **`syntax_highlighting`**: *object* (2 keys)
  - `css_class_style`: `"semantic"`
  - `theme`: `"auto"`
