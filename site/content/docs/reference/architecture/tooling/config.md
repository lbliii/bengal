---
title: Configuration System
nav_title: Config
description: Flexible, format-agnostic configuration loading
weight: 20
category: tooling
tags: [tooling, config, configuration, yaml, toml, loading, architecture]
keywords: [configuration, config, YAML, TOML, loading, site config, content config, params]
---

# Configuration System

Bengal's configuration system provides flexible, format-agnostic loading of site configuration with clear architectural boundaries.

## Design Philosophy

Bengal's configuration follows the **Separation of Concerns** principle with three distinct layers:

```mermaid
graph LR
    subgraph "Configuration Architecture"
        Site[site.yaml<br/>Identity & Metadata]
        Content[content.yaml<br/>Processing Pipeline]
        Params[params.yaml<br/>User Variables]

        Site -->|"site.config.title"| Templates[Templates]
        Content -->|"page.excerpt<br/>page.reading_time<br/>section.pages"| CoreModel[Content Model]
        Params -->|"site.config.params.*"| Templates
        CoreModel -->|"computed properties"| Templates
    end
```

### Three-Layer Architecture

1. **`site.yaml` - Identity & Metadata**
   - Who you are: title, author, baseurl
   - Site structure: menus, taxonomies
   - **Does NOT** control content processing or theme behavior

2. **`content.yaml` - Processing Pipeline (Bengal's Core API)**
   - How Bengal computes content
   - Theme-independent processing: `page.excerpt`, `page.reading_time`, `page.toc`
   - Section organization: sorting, filtering, type detection
   - **This is Bengal's API to theme developers**

3. **`params.yaml` - User Variables**
   - Custom site-specific data
   - Accessible in templates/markdown: `{{ site.config.params.product_name }}`
   - Not processed by Bengal, just passed through

### Why This Architecture?

**Aligns with Design Principles:**
- ✅ **Single Responsibility**: Each config file has one clear purpose
- ✅ **Separation of Concerns**: Identity vs. Processing vs. Data
- ✅ **Theme Independence**: Content processing separate from presentation
- ✅ **Explicit is Better Than Implicit**: Clear what each setting controls
- ✅ **Composition Over Inheritance**: Content model composes from config

:::{example-label} Theme Switch Scenario
:::

```yaml
# When switching themes, you DON'T touch:
content:
  excerpt_length: 200      # Bengal still computes 200-char excerpts
  reading_speed: 250       # Bengal still calculates at 250 WPM
  default_type: "doc"      # Sections still default to doc type

# New theme just displays what Bengal computed:
# {{ page.excerpt }} - still 200 chars
# {{ page.reading_time }} - still calculated at 250 WPM
```

## Config Loader (`bengal/config/loader.py`)

### Purpose
Load and manage site configuration from TOML, YAML, or directory structures

### Features
- Supports TOML and YAML formats
- Supports directory-based config (config/_default/, config/environments/)
- Auto-detects config files
- Provides sensible defaults
- Flattens nested configuration for easy access
- **Uses Utilities**: Delegates to `bengal.utils.file_io` for robust file loading with error handling

### Auto-Detection Order
1. `bengal.toml`
2. `bengal.yaml` / `bengal.yml`
3. `config.toml`
4. `config.yaml` / `config.yml`

### Configuration Structure (Single File - bengal.toml)

```toml
# bengal.toml - All-in-one configuration

[site]
title = "My Site"
description = "A Bengal SSG site"
baseurl = "https://example.com"
language = "en"

[content]
# Bengal's content processing pipeline
default_type = "doc"
excerpt_length = 200
reading_speed = 250
related_count = 3
toc_depth = 3

[params]
# User custom variables
product_name = "My Product"
api_url = "https://api.example.com"

[build]
output_dir = "public"
markdown_engine = "mistune"
parallel = true
incremental = false

[theme]
name = "default"

[site.taxonomies]
- tags
- categories

[site.menu.main]
[[site.menu.main]]
name = "Home"
url = "/"
weight = 1
```

### Configuration Structure (Directory - Recommended)

```tree
config/
├── _default/
│   ├── site.yaml      # Identity: title, author, menus, taxonomies
│   ├── content.yaml   # Processing: excerpt_length, toc_depth, sorting
│   ├── params.yaml    # Variables: product_name, api_url, custom data
│   ├── build.yaml     # Build: parallel, incremental, output_dir
│   └── features.yaml  # Features: analytics, search, comments
├── environments/
│   ├── local.yaml     # Dev overrides
│   └── production.yaml # Prod overrides
└── profiles/
    ├── writer.yaml    # Workflow: fast builds, no validation
    └── dev.yaml       # Workflow: full observability
```

:::{example-label} site.yaml (Identity)
:::

```yaml
site:
  title: "My Site"
  author: "Your Name"
  baseurl: "https://example.com"

  menu:
    main:
      - name: "Home"
        url: "/"
        weight: 1

  taxonomies:
    - tags
    - categories
```

:::{example-label} content.yaml (Bengal's API)
:::

```yaml
content:
  # What Bengal computes
  default_type: "doc"
  excerpt_length: 200      # → page.excerpt (200 chars)
  reading_speed: 250       # → page.reading_time (at 250 WPM)
  related_count: 3         # → page.related_posts (3 items)
  toc_depth: 3             # → page.toc (h1-h3)

  # How Bengal organizes
  sort_pages_by: "weight"
  sort_order: "asc"
```

:::{example-label} params.yaml (User Data)
:::

```yaml
params:
  product_name: "Bengal"
  version: "1.0.0"
  api_url: "https://api.example.com"

  # Accessible in templates:
  # {{ site.config.params.product_name }}
  # {{ site.config.params.api_url }}
```

### Environment-Aware Configuration

Bengal automatically detects deployment environments and applies environment-specific overrides.

**Environment Detection Order:**
1. `BENGAL_ENV` (explicit override, highest priority)
2. Netlify: Detects `NETLIFY=true` + `CONTEXT` (production/preview)
3. Vercel: Detects `VERCEL=1` + `VERCEL_ENV` (production/preview/development)
4. GitHub Actions: Detects `GITHUB_ACTIONS=true` (assumes production)
5. Default: Falls back to `local`

:::{example-label} environments/production.yaml
:::

```yaml
site:
  baseurl: "https://example.com"  # Production URL

build:
  minify_html: true
  fingerprint_assets: true
```

:::{example-label} environments/local.yaml
:::

```yaml
site:
  baseurl: "http://localhost:5173"  # Local dev URL

build:
  minify_html: false  # Faster builds during development
  fingerprint_assets: false
```

**Usage:**
```bash
# Use environment-specific config
bengal build --environment production
bengal serve --environment local  # Default for serve
```

### Build Profiles

Profiles provide persona-based configuration for optimized workflows.

**Available Profiles:**
- `writer`: Fast builds, quiet output (minimal logging)
- `theme-dev`: Template debugging (verbose template errors)
- `dev`: Full observability (all logging, validation enabled)

:::{example-label} profiles/writer.yaml
:::

```yaml
build:
  parallel: true
  quiet: true  # Minimal output

features:
  validation: false  # Skip validation for speed
```

:::{example-label} profiles/dev.yaml
:::

```yaml
build:
  parallel: true
  verbose: true  # Full output

features:
  validation: true
  health_checks: true
```

**Usage:**
```bash
# Use build profiles
bengal build --profile writer     # Fast builds, quiet output
bengal build --profile dev        # Full observability
```

### Configuration Precedence

Configuration is merged in this order (lowest to highest priority):

1. **`config/_default/*.yaml`** (base configuration)
2. **`config/environments/<env>.yaml`** (environment overrides)
3. **`config/profiles/<profile>.yaml`** (profile settings)
4. **Environment variable overrides** (GitHub Actions, Netlify, Vercel)

Later layers override earlier ones. Feature toggles are expanded after all merges.

### Smart Feature Toggles

Feature toggles provide simple flags that expand into detailed configuration.

:::{example-label} features.yaml
:::

```yaml
features:
  rss: true      # Expands to full RSS feed configuration
  search: true   # Expands to search index configuration
  json: true     # Expands to JSON API configuration
```

These simple flags are automatically expanded into full configuration via `bengal/config/feature_mappings.py`, reducing boilerplate while maintaining flexibility.

### CLI Introspection

Bengal provides CLI commands for configuration introspection and management:

```bash
# Show merged configuration
bengal config show

# Show with environment/profile
bengal config show --environment production --profile writer

# Show config origin (which file contributed each key)
bengal config show --origin

# Show specific section
bengal config show --section build

# Diagnose config issues
bengal config doctor

# Compare configurations
bengal config diff --environment local production

# Initialize config directory structure
bengal config init
```

### Default Configuration

If no config file found, Bengal provides sensible defaults:

```python
{
    'title': 'My Site',
    'base_url': '',
    'output_dir': 'public',
    'content_dir': 'content',
    'assets_dir': 'assets',
    'templates_dir': 'templates',
    'theme': 'default',
    'build': {
        'parallel': True,
        'incremental': False,
        'markdown_engine': 'mistune',
    },
    'taxonomies': {
        'tags': 'tags',
        'categories': 'categories',
    },
}
```

### Usage

```python
from bengal.config import load_config

# Auto-detect and load
config = load_config()

# Load from specific path
config = load_config(Path('my-config.toml'))

# Access values
title = config['title']
parallel = config['build']['parallel']
```

### Content Configuration Details

**What `content.yaml` Controls:**

These settings configure **Bengal's content model**, not theme presentation:

| Setting | Affects | Template Access |
|---------|---------|-----------------|
| `excerpt_length` | `Page.excerpt` property | `{{ page.excerpt }}` |
| `reading_speed` | `Page.reading_time` property | `{{ page.reading_time }}` |
| `summary_length` | `Page.meta_description` property | `{{ page.meta_description }}` |
| `related_count` | `Page.related_posts` property | `{% for post in page.related_posts %}` |
| `related_threshold` | Related posts algorithm | (internal) |
| `toc_depth` | `Page.toc` generation | `{{ page.toc \| safe }}` |
| `toc_min_headings` | When TOC is generated | (internal) |
| `default_type` | `Section` content type detection | (internal) |
| `sort_pages_by` | `Section.pages` ordering | `{% for page in section.pages %}` |

**Key Insight**: Bengal computes these properties during build. Themes just display them.

### Configuration Validation

The ConfigValidator (part of health check system) validates:
- Required fields present
- Valid values for enums
- Path existence
- Type correctness
- Common misconfigurations
- Separation of concerns (warns if mixing concerns)
