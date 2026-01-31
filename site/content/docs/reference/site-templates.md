---
title: Site Templates Reference
nav_title: Site Templates
description: Complete reference for Bengal's site scaffolding and template system
weight: 25
draft: false
tags: [reference, templates, scaffolding, cli]
keywords: [templates, scaffolding, new site, init, skeleton]
category: reference
---

# Site Templates Reference

Bengal provides a template system for scaffolding new sites with predefined structures. This reference covers all CLI commands and template options.

## CLI Commands Overview

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `bengal new site` | Create new site from template | Starting a new project |
| `bengal init` | Add sections to existing site | Expanding site structure |
| `bengal config init` | Initialize config directory | Converting single-file to directory config |

---

## `bengal new site`

Create a new Bengal site from a template.

### Syntax

```bash
bengal new site [NAME] [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `NAME` | No | Site directory name (prompted if omitted) |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--template` | `default` | Site template (see templates below) |
| `--theme` | `default` | Theme to use |
| `--no-init` | `false` | Skip structure initialization wizard |
| `--init-preset` | - | Preset name for non-interactive mode |

### Examples

```bash
# Interactive mode (prompts for all options)
bengal new site

# Create docs site with explicit name
bengal new site my-docs --template docs

# Non-interactive with preset
bengal new site my-blog --template blog --no-init
```

### What Gets Created

All templates create:
- `config/` directory with environment-aware configuration
- `content/` directory with template-specific pages
- `.gitignore` for Bengal-specific files

---

## `bengal init`

Initialize content sections in an existing Bengal site. Uses the skeleton system under the hood.

### Syntax

```bash
bengal init [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--sections`, `-s` | Multiple | `blog` | Section names to create |
| `--with-content` | Flag | `false` | Generate sample pages |
| `--pages-per-section` | Integer | `3` | Sample pages per section |
| `--dry-run` | Flag | `false` | Preview without creating |
| `--force` | Flag | `false` | Overwrite existing sections |

### Examples

```bash
# Default: create blog section
bengal init

# Multiple sections
bengal init --sections blog --sections projects --sections about

# Short form
bengal init -s docs -s tutorials -s api

# With sample content
bengal init --sections blog --with-content --pages-per-section 10

# Preview first
bengal init --sections docs --dry-run
```

### Section Type Inference

Section names are mapped to content types:

| Name Pattern | Type | Description |
|--------------|------|-------------|
| `blog`, `posts`, `articles`, `news` | `blog` | Date-sorted content |
| `docs`, `documentation`, `guides`, `reference`, `tutorials` | `doc` | Weight-sorted content |
| All others | `section` | Standard section |

### Generated Files

For each section, Bengal creates:

```tree
content/<section>/
├── _index.md          # Section index (always created)
├── <page-1>.md        # Sample pages (with --with-content)
├── <page-2>.md
└── <page-3>.md
```

Sample page names are context-aware:
- Blog: `welcome-post`, `getting-started`, `tips-and-tricks`
- Docs: `introduction`, `quickstart`, `installation`
- Projects: `project-alpha`, `project-beta`, `project-gamma`

---

## `bengal config init`

Initialize configuration directory structure in an existing project.

### Syntax

```bash
bengal config init [SOURCE] [OPTIONS]
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `SOURCE` | `.` | Directory to initialize |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--type` | `directory` | Config structure (`directory` or `file`) |
| `--template` | `docs` | Config preset (`docs`, `blog`, `minimal`) |
| `--force` | `false` | Overwrite existing config files |

### Examples

```bash
# Create config directory in current project
bengal config init

# Use blog preset
bengal config init --template blog

# Single file instead of directory
bengal config init --type file
```

### Directory Structure Created

```tree
config/
├── _default/
│   ├── site.yaml      # Site identity
│   ├── build.yaml     # Build settings
│   └── features.yaml  # Feature toggles
├── environments/
│   ├── local.yaml     # Dev overrides
│   └── production.yaml
└── profiles/
    ├── writer.yaml    # Writer workflow
    └── dev.yaml       # Developer workflow
```

---

## Built-in Templates

### `default`

Minimal starter with single index page.

**Structure:**
```tree
content/
└── index.md
```

**Best for:** Minimal sites, custom builds from scratch.

---

### `docs`

Full documentation site with common sections.

**Structure:**
```tree
content/
├── index.md
├── getting-started/
│   ├── _index.md
│   ├── installation.md
│   └── quickstart.md
├── guides/
│   └── _index.md
└── api/
    └── _index.md
```

**Config preset:** Enables search, TOC depth 3, doc-style sorting.

**Best for:** Technical documentation, knowledge bases, API docs.

---

### `blog`

Blog with posts section and about page.

**Structure:**
```tree
content/
├── index.md
├── about.md
└── posts/
    ├── first-post.md
    └── second-post.md
```

**Config preset:** Enables RSS, date-sorted posts, excerpt generation.

**Best for:** Personal blogs, news sites, journals.

---

### `portfolio`

Project showcase with contact page.

**Structure:**
```tree
content/
├── index.md
├── about.md
├── contact.md
└── projects/
    ├── index.md
    ├── project-1.md
    └── project-2.md
```

**Best for:** Developer portfolios, agency sites, project showcases.

---

### `resume`

CV/Resume with structured data.

**Structure:**
```tree
content/
└── _index.md

data/
└── resume.yaml    # Structured resume data
```

**Best for:** Personal CVs, professional profiles.

---

### `landing`

Marketing landing page with legal pages.

**Structure:**
```tree
content/
├── index.md
├── privacy.md
└── terms.md
```

**Best for:** Product landing pages, marketing sites.

---

### `changelog`

Version history with structured data.

**Structure:**
```tree
content/
└── _index.md

data/
└── changelog.yaml
```

**Best for:** Release notes, version history.

---

### `product`

Product showcase with catalog and pricing.

**Structure:**
```tree
content/
├── _index.md
├── contact.md
├── features.md
├── pricing.md
└── products/
    ├── _index.md
    ├── product-1.md
    └── product-2.md

data/
└── products.yaml
```

**Config preset:** Enables product catalog, structured data for products.

**Best for:** Product websites, e-commerce showcases, SaaS landing pages.

---

## Template Architecture

### How Templates Work

Templates are defined in `bengal/scaffolds/<name>/`:

```tree
bengal/scaffolds/docs/
├── __init__.py
├── template.py       # TEMPLATE = SiteTemplate(...)
└── pages/
    ├── index.md
    └── getting-started/
        └── _index.md
```

### SiteTemplate Class

```python
@dataclass
class SiteTemplate:
    id: str                    # Template identifier
    name: str                  # Display name
    description: str           # One-line summary
    files: list[TemplateFile]  # Files to create
    additional_dirs: list[str] # Extra directories
    menu_sections: list[str]   # Menu seed sections
```

### TemplateFile Class

```python
@dataclass
class TemplateFile:
    relative_path: str    # Path under target_dir
    content: str          # File contents
    target_dir: str       # "content", "data", "templates"
```

---

## Config Directory Structure

All templates create this config structure:

```yaml
# config/_default/site.yaml
site:
  title: "My Site"
  description: "Built with Bengal"
  language: "en"

# config/_default/build.yaml
build:
  parallel: true
  incremental: true
  minify_html: true

# config/_default/features.yaml
features:
  rss: true
  sitemap: true
  search: true
  json: true
  llm_txt: true
```

### Environment-Specific Config

```yaml
# config/environments/local.yaml
build:
  debug: true
  strict_mode: false

# config/environments/production.yaml
site:
  baseurl: "https://example.com"
build:
  strict_mode: true
```

---

## Related Documentation

- [Configuration](/docs/building/configuration/) - How config works
- [Configuration System](/docs/reference/architecture/tooling/config/) - Architecture details
- [Scaffold Tutorial](/docs/get-started/scaffold-your-site/) - Step-by-step guide
