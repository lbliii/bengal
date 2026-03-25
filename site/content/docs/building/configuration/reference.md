---
title: Configuration Reference
description: Complete reference of all bengal.toml options
weight: 30
icon: book
nav_title: Reference
tags:
- configuration
- reference
keywords:
- bengal.toml
- config
- options
- settings
category: reference
---

# Configuration Reference

All options for `bengal.toml`. Every option has a sensible default — most sites only need `[site]` and `[build]`.

## [site]

Site metadata used in templates, feeds, and SEO.

```toml
[site]
title = "My Site"              # Required
baseurl = "https://example.com"
description = "Site description"
author = "Author Name"
language = "en"
```

## [build]

Controls the build pipeline, caching, and parallelism.

```toml
[build]
output_dir = "public"          # Where built files go
content_dir = "content"        # Where content lives
assets_dir = "assets"          # Static assets directory
templates_dir = "templates"    # Custom template overrides
parallel = true                # Enable parallel processing
incremental = true             # Enable incremental builds
max_workers = 8                # Limit parallel workers (default: auto-detect)
pretty_urls = true             # /page/ instead of /page.html
fast_mode = false              # Skip HTML formatting for speed
strict_mode = false            # Fail on warnings
debug = false                  # Extra logging
minify_html = false            # Minify HTML output
validate_build = true          # Run post-build validation
validate_templates = false     # Validate template context
validate_links = false         # Check internal links
transform_links = true         # Transform internal links to pretty URLs
cache_templates = true         # Cache compiled templates
fast_writes = false            # Skip write for unchanged files
stable_section_references = false  # Deterministic section IDs
min_page_size = 0              # Minimum page count for parallel
track_dependency_ordering = false  # Track build dependency order
parallel_graph = false         # Parallel graph analysis
parallel_autodoc = false       # Parallel autodoc extraction
```

## [dev]

Development server settings.

```toml
[dev]
port = 8000                    # Server port
live_reload = true             # Enable live reload via SSE
cache_templates = false        # Cache templates in dev (default: off for hot reload)
watch_backend = true           # Watch backend files for changes
```

## [theme]

Theme selection and appearance.

```toml
[theme]
name = "default"
default_appearance = "system"  # "light", "dark", or "system"
default_palette = ""
show_reading_time = true
show_author = true
show_prev_next = true
show_children_default = false
show_excerpts_default = false
max_tags_display = 10
popular_tags_count = 20
features = []                  # Feature flags: "content.math", etc.

[theme.syntax_highlighting]
theme = "auto"                 # Syntax theme name
css_class_style = "semantic"   # "semantic" or "pygments"
```

## [content]

Content processing defaults.

```toml
[content]
default_type = "docs"
excerpt_length = 200
excerpt_words = 50
summary_length = 300
reading_speed = 200            # Words per minute
related_count = 5
related_threshold = 0.1
toc_depth = 3
toc_min_headings = 2
toc_style = "nested"           # "nested" or "flat"
sort_pages_by = "weight"       # "weight", "date", "title", "modified"
sort_order = "asc"
strict_contracts = false
```

## [pagination]

```toml
[pagination]
per_page = 10
```

## [search]

Client-side search with Lunr. Can be `true`/`false` or a table.

```toml
[search]
enabled = true

[search.lunr]
prebuilt = false
min_query_length = 2
max_results = 10
preload = "smart"              # "immediate", "smart", "lazy"

[search.ui]
modal = true
recent_searches = 5
placeholder = "Search..."

[search.analytics]
enabled = false
event_endpoint = ""
```

## [assets]

Asset processing pipeline.

```toml
[assets]
minify = false
optimize = false
fingerprint = false
pipeline = true
```

## [html_output]

HTML formatting for built pages.

```toml
[html_output]
mode = "pretty"                # "minify", "pretty", "raw"
remove_comments = false
collapse_blank_lines = true
```

## [static]

Static file handling.

```toml
[static]
enabled = true
dir = "static"
```

## [features]

Toggle site-wide features.

```toml
[features]
rss = true
sitemap = true
search = true
json = false
llm_txt = false
syntax_highlighting = true
```

## [health_check]

Build and content validation. Can be `true`/`false` or a table.

```toml
[health_check]
enabled = true
verbose = false
strict_mode = false
orphan_threshold = 5
super_hub_threshold = 50
isolated_threshold = 0
lightly_linked_threshold = 3
build_validators = []          # Validators run during build
full_validators = []           # Validators for full check
ci_validators = []             # Validators for CI

[health_check.connectivity_thresholds]
well_connected = 0.7
adequately_linked = 0.4
lightly_linked = 0.1

[health_check.link_weights]
explicit = 1.0
menu = 0.8
taxonomy = 0.6
related = 0.4
topical = 0.3
sequential = 0.2
```

## [i18n]

Internationalization settings.

```toml
[i18n]
strategy = ""                  # null or strategy name
default_language = "en"
default_in_subdir = false
content_structure = ""
fallback_to_default = true
gettext_domain = "messages"

[[i18n.languages]]
code = "en"
name = "English"
weight = 1

[[i18n.languages]]
code = "es"
name = "Español"
weight = 2
```

## [output_formats]

Control which output formats are generated. Can be `true`/`false` or a table.

```toml
[output_formats]
enabled = true
per_page = ["html"]            # Per-page formats
site_wide = ["rss", "sitemap"] # Site-wide formats

[output_formats.options]
excerpt_length = 200
json_indent = 2
llm_separator_width = 80
include_full_content_in_index = false
include_chunks = false
exclude_sections = []
exclude_patterns = []
```

## [content_signals]

AI and crawler content policies.

```toml
[content_signals]
enabled = false
search = true
ai_input = true                # Allow AI RAG/grounding
ai_train = false               # Allow AI training
include_sitemap = true

[content_signals.user_agents]
"*" = ""                       # Per-agent policies
```

## [structured_data]

Schema.org JSON-LD generation.

```toml
[structured_data]
article = true
```

## [markdown]

Markdown parser configuration.

```toml
[markdown]
parser = "patitas"             # "patitas" or "mistune"
toc_depth = "2-4"

[markdown.ast_cache]
persist_tokens = false
```

## [graph]

Knowledge graph analysis. Can be `true`/`false` or a table.

```toml
[graph]
enabled = false
path = ".bengal/graph"
```

## [external_refs]

Cross-project documentation links. Can be `true`/`false` or a table.

```toml
[external_refs]
enabled = false
export_index = false
cache_dir = ".bengal/refs"
default_cache_days = 7
templates = {}

[[external_refs.indexes]]
name = "other-project"
url = "https://example.com/refs.json"
cache_days = 7
```

## [link_previews]

Hover card configuration. Can be `true`/`false` or a table.

```toml
[link_previews]
enabled = false
hover_delay = 300
hide_delay = 200
show_section = true
show_reading_time = true
show_word_count = false
show_date = false
show_tags = false
max_tags = 3
include_selectors = []
exclude_selectors = []
allowed_hosts = []
allowed_schemes = ["https"]
host_failure_threshold = 3
show_dead_links = false
```

## [document_application]

Modern browser features: view transitions, speculation rules, interactive elements.

```toml
[document_application]
enabled = false

[document_application.navigation]
view_transitions = false
transition_style = "crossfade" # "crossfade", "fade-slide", "slide", "none"
scroll_restoration = true

[document_application.speculation]
enabled = false
auto_generate = false
exclude_patterns = []

[document_application.speculation.prerender]
eagerness = "moderate"         # "conservative", "moderate", "eager"
patterns = []

[document_application.speculation.prefetch]
eagerness = "moderate"
patterns = []

[document_application.interactivity]
tabs = "css_state_machine"
accordions = "native_details"
modals = "native_dialog"
tooltips = "popover"
dropdowns = "popover"
code_copy = "enhanced"
```

## [connect_to_ide]

Cursor IDE integration.

```toml
[connect_to_ide]
enabled = false
mcp_url = ""
server_name = ""
```

## [taxonomies]

Define taxonomy term→field mappings.

```toml
[taxonomies]
tags = "tags"
categories = "categories"
```

## [data]

Data file directory.

```toml
[data]
dir = "data"
```

## [autodoc.python]

Python API documentation extraction.

```toml
[autodoc.python]
enabled = false
source_dirs = []
output_prefix = "api"
```

## See Also

- [[docs/building/configuration/profiles|Build Profiles]] — Environment-specific config
- [[docs/building/configuration/variants|Multi-Variant Builds]] — Build different site variants
