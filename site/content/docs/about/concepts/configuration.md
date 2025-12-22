---
title: Configure Bengal
nav_title: Configure
description: Configuration reference for site settings, menus, and content processing
weight: 10
type: doc
draft: false
lang: en
tags:
- configuration
- config
- reference
keywords:
- configuration
- config
- toml
- yaml
- settings
category: documentation
---

Bengal supports TOML, YAML, and directory-based configuration files.

## Configuration Structure

Bengal configuration follows a **Three-Layer Architecture** to separate concerns:

1. **`site`** (Identity & Metadata)
   - Who you are: title, author, baseurl
   - Structure: menus, taxonomies
   - *Does NOT control content processing.*

2. **`content`** (Processing Pipeline)
   - How Bengal computes content: excerpts, reading time, TOC depth
   - *This is the API that themes rely on.*
   - **Why separate this?** It allows you to switch themes without breaking your content model or SEO metadata. The theme just displays what Bengal computed.

3. **`params`** (User Variables)
   - Custom site-specific data
   - Accessible in templates as `{{ site.config.params.foo }}`

## File Formats & Locations

Bengal looks for configuration in the following order:

1. `bengal.toml` (Recommended for simple sites)
2. `bengal.yaml` / `bengal.yml`
3. `config.toml`
4. `config.yaml` / `config.yml`
5. `config/` directory (Recommended for complex sites)

### Directory-Based Config

For larger sites, you can split configuration into multiple files:

```text
config/
├── _default/
│   ├── site.yaml      # Identity: title, author, menus
│   ├── content.yaml   # Processing: excerpt_length, sorting
│   ├── params.yaml    # Custom variables
│   ├── build.yaml     # Build settings
│   └── features.yaml  # Feature flags
├── environments/
│   ├── local.yaml     # Dev overrides
│   └── production.yaml # Prod overrides
```

## Reference

### `[site]`

General site identity and metadata.

```toml
[site]
title = "My Site"
description = "A Bengal SSG site"
baseurl = "https://example.com"
language = "en"
author = "Your Name"

[site.taxonomies]
tags = "tags"
categories = "categories"

[[site.menu.main]]
name = "Home"
url = "/"
weight = 1
```

### `[content]`

Controls how Bengal processes and organizes content.

| Setting | Default | Description |
|---------|---------|-------------|
| `default_type` | `"doc"` | Default content type for sections |
| `excerpt_length` | `200` | Length of auto-generated excerpts |
| `reading_speed` | `200` | Words per minute for reading time calculation |
| `related_count` | `3` | Number of related posts to find |
| `toc_depth` | `3` | Depth of Table of Contents (h2-h4) |
| `sort_pages_by` | `"weight"` | Default sort key (`weight`, `date`, `title`) |

### `[markdown]`

Configure the Markdown parsing engine.

```toml
[markdown]
parser = "mistune"       # "mistune" (fast, default) or "python-markdown" (full-featured)
```

**Note**: `mistune` is significantly faster (2–5x) and recommended for most sites. Bengal's MyST directives work with mistune.

### `[build]`

Build process settings.

```toml
[build]
output_dir = "public"
parallel = true          # Enable parallel processing (default: true)
incremental = true       # Enable incremental builds (default: true)
max_workers = null       # Auto-detect based on CPU cores
pretty_urls = true       # Generate /page/index.html instead of /page.html
minify_html = true       # Minify HTML output (default: true)
validate_links = true    # Check for broken internal links (default: true)
strict_mode = false      # Fail build on warnings (default: false)
```

**Note**: `max_workers` defaults to auto-detection based on your CPU cores (leaves 1 core for OS, minimum 4 workers). Set a specific number to override.

### `[features]`

Enable or disable built-in features.

```toml
[features]
rss = true               # Generate RSS feed
sitemap = true           # Generate sitemap.xml
search = true            # Enable client-side search
json = true              # Generate per-page JSON
llm_txt = true           # Generate LLM-friendly text files
syntax_highlighting = true  # Enable code syntax highlighting
```

### `[assets]`

Asset pipeline configuration.

```toml
[assets]
minify = true            # Minify CSS/JS
optimize = true          # Optimize images
fingerprint = true       # Add cache-busting hashes (style.abc123.css)
pipeline = false         # Enable Node.js asset pipeline (optional)

[assets.images]
quality = 85             # JPEG quality
strip_metadata = true    # Remove EXIF data
formats = ["webp"]       # Generate additional formats
```

### `[output_formats]`

Configure alternative output formats (JSON, LLM text).

```toml
[output_formats]
enabled = true
per_page = ["json"]               # Default: JSON only
site_wide = ["index_json"]        # Default: site index only

[output_formats.options]
excerpt_length = 200              # Excerpt length for site index
json_indent = null                # null for compact JSON, 2 for pretty
exclude_sections = []             # Sections to exclude from output formats
exclude_patterns = ["404.html", "search.html"]  # Files to exclude
```

### `[graph]`

Knowledge graph visualization.

```toml
[graph]
enabled = true           # Enable graph generation
path = "/graph/"         # URL path for graph page
```

### `[i18n]`

Internationalization settings.

```toml
[i18n]
strategy = null          # null (disabled), "subdir", or "domain"
default_language = "en"
default_in_subdir = false  # Put default language in subdir
```

### `[params]`

Arbitrary user parameters.

:::{warning}
**Security Warning**: Do not put secrets (API keys, passwords) in your configuration files if you commit them to public repositories. Bengal does not currently support environment variable substitution for arbitrary parameters.
:::

```toml
[params]
product_name = "Bengal"
analytics_id = "UA-12345-6"
social_twitter = "@bengal_ssg"
```
