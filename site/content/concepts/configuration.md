---
title: Configuration
description: Complete configuration reference for Bengal
weight: 10
---

Bengal provides a flexible configuration system that supports TOML, YAML, and directory-based organization.

## Configuration Structure

Bengal configuration follows a **Three-Layer Architecture** to separate concerns:

1. **`site`** (Identity & Metadata)
   - Who you are: title, author, baseurl
   - Structure: menus, taxonomies
   - *Does NOT control content processing.*

2. **`content`** (Processing Pipeline)
   - How Bengal computes content: excerpts, reading time, TOC depth
   - *This is the API that themes rely on.*

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
| `reading_speed` | `250` | Words per minute for reading time calculation |
| `related_count` | `3` | Number of related posts to find |
| `toc_depth` | `3` | Depth of Table of Contents (h1-h3) |
| `sort_pages_by` | `"weight"` | Default sort key (`weight`, `date`, `title`) |

### `[build]`

Build process settings.

```toml
[build]
output_dir = "public"
markdown_engine = "mistune"
parallel = true          # Enable parallel processing
incremental = false      # Enable incremental builds
max_workers = 4          # Max parallel workers
pretty_urls = true       # Generate /page/index.html instead of /page.html
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
per_page = ["json", "llm_txt"]
site_wide = ["index_json", "llm_full"]

[output_formats.options]
include_html_content = true
json_indent = 2
```

### `[params]`

Arbitrary user parameters.

```toml
[params]
product_name = "Bengal"
analytics_id = "UA-12345-6"
social_twitter = "@bengal_ssg"
```

