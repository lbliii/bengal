---
title: Configuration System
nav_title: Config
description: Format-agnostic configuration loading
weight: 20
---

# Configuration System

Bengal provides flexible, format-agnostic configuration with clear architectural boundaries.

## Three-Layer Architecture

| Layer | File | Purpose | Template Access |
|-------|------|---------|-----------------|
| **Identity** | `site.yaml` | Title, author, menus, taxonomies | `{{ site.title }}` |
| **Processing** | `content.yaml` | Excerpt length, TOC depth, sorting | `{{ page.excerpt }}` |
| **Variables** | `params.yaml` | Custom user data | `{{ site.config.params.* }}` |

## Config Detection

Bengal auto-detects configuration files in order:

1. `bengal.toml` / `bengal.yaml`
2. `config.toml` / `config.yaml`
3. `config/` directory structure

## Directory Structure (Recommended)

```tree
config/
├── _default/
│   ├── site.yaml      # Identity
│   ├── content.yaml   # Processing
│   ├── params.yaml    # Variables
│   └── build.yaml     # Build settings
├── environments/
│   ├── local.yaml     # Dev overrides
│   └── production.yaml
└── profiles/
    ├── writer.yaml    # Fast builds, quiet output
    └── dev.yaml       # Full observability
```

## Example Configuration

```yaml
# config/_default/site.yaml
site:
  title: "My Site"
  baseurl: "https://example.com"
  menu:
    main:
      - name: "Home"
        url: "/"

# config/_default/content.yaml
content:
  excerpt_length: 200      # → page.excerpt
  reading_speed: 250       # → page.reading_time
  toc_depth: 3             # → page.toc
  sort_pages_by: "weight"

# config/_default/params.yaml
params:
  product_name: "Bengal"
  version: "1.0.0"
```

## Environment Detection

Bengal auto-detects deployment environments:

| Platform | Detection | Environment |
|----------|-----------|-------------|
| Netlify | `NETLIFY=true` | `CONTEXT` value |
| Vercel | `VERCEL=1` | `VERCEL_ENV` value |
| GitHub Actions | `GITHUB_ACTIONS=true` | `production` |
| Manual | `BENGAL_ENV=<env>` | Explicit override |
| Default | — | `local` |

```bash
bengal build --environment production
bengal serve --environment local  # Default for serve
```

## Build Profiles

```bash
bengal build --profile writer   # Fast builds, quiet output
bengal build --profile dev      # Full observability
```

## Configuration Precedence

Merged lowest to highest:

1. `config/_default/*.yaml`
2. `config/environments/<env>.yaml`
3. `config/profiles/<profile>.yaml`
4. Environment variable overrides

## CLI Commands

```bash
bengal config show                    # Show merged config
bengal config show --origin           # Show which file contributed each key
bengal config doctor                  # Diagnose issues
bengal config diff local production   # Compare environments
bengal config init                    # Initialize directory structure
```

## Content Processing Settings

| Setting | Affects | Template Access |
|---------|---------|-----------------|
| `excerpt_length` | `page.excerpt` | `{{ page.excerpt }}` |
| `reading_speed` | `page.reading_time` | `{{ page.reading_time }}` |
| `toc_depth` | `page.toc` | `{{ page.toc | safe }}` |
| `related_count` | `page.related_posts` | `{% for p in page.related_posts %}` |
| `default_type` | Section type detection | (internal) |
| `sort_pages_by` | `section.pages` order | `{% for p in section.pages %}` |

## Usage

```python
from bengal.config import load_config

config = load_config()  # Auto-detect
config = load_config(Path('my-config.toml'))  # Specific file

title = config['title']
parallel = config['build']['parallel']
```
