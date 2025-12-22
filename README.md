# Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**A high-performance static site generator for Python 3.14+**

```bash
pip install bengal
bengal new site mysite && cd mysite && bengal serve
```

---

## Why Bengal?

- **Fast** — Parallel builds, incremental rebuilds, Zstandard-compressed caching
- **Modern** — Python 3.14+ with free-threading support, fully typed
- **Batteries included** — Auto-generated API docs, content validation, site analysis
- **Extensible** — Remote content sources, custom directives, flexible theming

---

## Quick Commands

| Command | Description |
|---------|-------------|
| `bengal build` | Production build |
| `bengal serve` | Dev server with live reload |
| `bengal validate` | Health checks and validation |
| `bengal fix` | Auto-fix common issues |
| `bengal graph report` | Site structure analysis |

Aliases: `b` (build), `s` (serve), `v` (validate)

---

## Site Scaffolding

<details>
<summary><strong>Interactive Wizard</strong> — Guided setup with presets</summary>

Run without arguments for a guided experience:

```bash
bengal new site
```

The wizard prompts for site name, base URL, and presents preset options:

```
🎯 What kind of site are you building?
  📝 Blog            - Personal or professional blog
  📚 Documentation   - Technical docs or guides
  💼 Portfolio       - Showcase your work
  🏢 Business        - Company or product site
  📄 Resume          - Professional resume/CV site
  📦 Blank           - Empty site, no initial structure
  ⚙️  Custom         - Define your own structure
```

Each preset creates a complete site with appropriate sections, sample content, and configuration.

</details>

<details>
<summary><strong>Direct Template Selection</strong> — Skip prompts with explicit options</summary>

Create sites non-interactively with `--template`:

```bash
bengal new site my-docs --template docs
bengal new site my-blog --template blog
bengal new site portfolio --template portfolio
```

**Available templates:**

| Template | Description | Sections Created |
|----------|-------------|------------------|
| `default` | Minimal starter | Home page only |
| `blog` | Personal/professional blog | blog, about |
| `docs` | Technical documentation | getting-started, guides, api |
| `portfolio` | Showcase work | about, projects, blog, contact |
| `product` | Product/company site | products, features, pricing, contact |
| `landing` | Single-page landing | Home, privacy, terms |
| `resume` | Professional CV | Single resume page |
| `changelog` | Release notes | Changelog with YAML data |

</details>

<details>
<summary><strong>Add Sections to Existing Sites</strong> — Expand without recreating</summary>

Add new content sections to an existing Bengal site:

```bash
# Add multiple sections
bengal project init --sections docs --sections tutorials

# Add sections with sample content
bengal project init --sections blog --with-content --pages-per-section 5

# Preview without creating files
bengal project init --sections api --dry-run
```

**Section type inference:**

| Name Pattern | Inferred Type | Behavior |
|--------------|---------------|----------|
| blog, posts, articles, news | `blog` | Date-sorted, post-style |
| docs, documentation, guides, tutorials | `doc` | Weight-sorted, doc-style |
| projects, portfolio | `section` | Standard section |
| about, contact | `section` | Standard section |

</details>

<details>
<summary><strong>Custom Skeleton Manifests</strong> — YAML-defined site structures</summary>

For complex or repeatable scaffolding, define structures in YAML manifests:

```bash
# Preview what would be created
bengal project skeleton apply my-structure.yaml --dry-run

# Apply the skeleton
bengal project skeleton apply my-structure.yaml

# Overwrite existing files
bengal project skeleton apply my-structure.yaml --force
```

**Example manifest** (`docs-skeleton.yaml`):

```yaml
name: Documentation Site
description: Technical docs with navigation sections
version: "1.0"

cascade:
  type: doc  # Applied to all pages

structure:
  - path: _index.md
    props:
      title: Documentation
      description: Project documentation
      weight: 100
    content: |
      # Documentation
      Welcome! Start with our [Quick Start](getting-started/quickstart/).

  - path: getting-started/_index.md
    props:
      title: Getting Started
      weight: 10
    cascade:
      type: doc
    pages:
      - path: installation.md
        props:
          title: Installation
          weight: 20
        content: |
          # Installation
          ```bash
          pip install your-package
          ```

      - path: quickstart.md
        props:
          title: Quick Start
          weight: 30
        content: |
          # Quick Start
          Your first project in 5 minutes.

  - path: api/_index.md
    props:
      title: API Reference
      weight: 30
    content: |
      # API Reference
      Complete API documentation.
```

**Component Model:**
- `path` — File or directory path
- `type` — Component identity (blog, doc, landing)
- `variant` — Visual style variant
- `props` — Frontmatter data (title, weight, etc.)
- `content` — Markdown body content
- `pages` — Child components (makes this a section)
- `cascade` — Values inherited by all descendants

</details>

---

## Features

### Content Authoring

Markdown with directives — tabs, admonitions, code blocks, cards, and more:

~~~markdown
:::{note} Pro tip
Nest **any markdown** inside directives.
:::

:::{tabs}
### Python
```python
print("Hello")
```
### JavaScript
```js
console.log("Hello")
```
:::
~~~

Frontmatter for metadata and visibility control:

```yaml
---
title: My Page
date: 2025-12-01
hidden: true           # Exclude from nav, search, sitemap
template: custom.html  # Custom template
---
```

### Auto-Generated Documentation

Generate docs from source code without imports:

```yaml
# config/_default/autodoc.yaml
python:
  enabled: true
  source_dirs: [mypackage]

cli:
  enabled: true
  app_module: mypackage.cli:main

openapi:
  enabled: true
  spec_file: openapi.yaml
```

### Remote Content Sources

Pull content from GitHub, Notion, or REST APIs:

```bash
pip install bengal[github]      # GitHub source
pip install bengal[notion]      # Notion source
pip install bengal[all-sources] # All remote sources
```

```python
# collections.py
from bengal.content_layer import github_loader

collections = {
    "external-docs": define_collection(
        schema=Doc,
        loader=github_loader(repo="myorg/docs", path="content/"),
    ),
}
```

### Build Performance

| Site Size | Strategy | Typical Build Time |
|-----------|----------|-------------------|
| <500 pages | Default | 1-3s |
| 500-5K pages | `--incremental` | 3-15s |
| 5K+ pages | `--memory-optimized` | 15-60s |

```bash
bengal build --incremental   # Only rebuild changed files
bengal build --parallel      # Use all CPU cores (default)
bengal build --memory-optimized  # Streaming for large sites
```

### Site Analysis & Validation

```bash
bengal graph report    # Full connectivity analysis
bengal graph orphans   # Find unlinked pages
bengal validate        # Run health checks
bengal validate --watch # Continuous validation
bengal fix             # Auto-fix common issues
```

---

## Configuration

Directory-based config with environment and profile support:

```
mysite/
├── bengal.toml              # Simple single-file (optional)
└── config/
    ├── _default/            # Base configuration
    │   ├── site.yaml
    │   ├── build.yaml
    │   └── autodoc.yaml
    ├── environments/        # Environment overrides
    │   └── production.yaml
    └── profiles/            # Build profiles
        └── dev.yaml
```

**Minimal config:**

```toml
[site]
title = "My Site"
baseurl = "https://example.com"
```

**Environment and profile builds:**

```bash
bengal build -e production       # Production environment
bengal build --profile writer    # Fast, clean output
bengal build --profile dev       # Full observability
```

---

## Project Structure

```
mysite/
├── content/          # Markdown pages
├── templates/        # Custom Jinja2 templates (optional)
├── assets/           # Static files (CSS, JS, images)
├── data/             # YAML/JSON data files
├── config/           # Configuration directory
└── public/           # Build output
```

---

## Theming

Bengal ships with a modern, accessible default theme:

- Dark mode with system preference detection
- Responsive design with mobile navigation
- Syntax highlighting with copy buttons
- Table of contents with scroll spy
- Full-text search (Lunr.js)

**Customize templates:**

```html
{# templates/page.html #}
{% extends "base.html" %}

{% block content %}
<article class="prose">
  <h1>{{ page.title }}</h1>
  {{ content | safe }}
</article>
{% endblock %}
```

---

## Requirements

- **Python 3.14+** (uses free-threading and PEP 784 compression)
- Linux, macOS, Windows

---

## Philosophy

Bengal prioritizes **correctness and clarity over backwards compatibility**.

Each release represents the best solution we know how to deliver. When existing behavior no longer reflects the best design, it changes. Upgrades may require reading release notes and making adjustments.

- **Fail loudly** — Breaking changes produce clear errors
- **User control** — You choose when to upgrade; we choose what changes
- **No hidden layers** — No compatibility shims or deprecated code paths

If you need multi-year stability, pin your version.

---

## Documentation

📚 **[lbliii.github.io/bengal](https://lbliii.github.io/bengal/)**

---

## Development

```bash
git clone https://github.com/lbliii/bengal.git
cd bengal
uv sync --group dev
pytest
```

---

## License

MIT
