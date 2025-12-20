# Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/bengal.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**A high-performance static site generator built for Python 3.14+**

```bash
pip install bengal
bengal new site mysite && cd mysite && bengal serve
```

---

## Why Bengal?

- **Fast** — Parallel builds, incremental rebuilds, Zstandard-compressed cache
- **Modern** — Python 3.14+ with free-threading support, type-safe throughout
- **Batteries included** — Auto-generated API docs, content validation, knowledge graph analysis
- **Extensible** — Remote content sources, custom directives, flexible theming

---

## Quick Start

```bash
# Install
pip install bengal

# Create and run
bengal new site mysite
cd mysite
bengal serve
```

Open `localhost:5173`. Edit `content/`, see changes instantly.

### Common Commands

```bash
bengal build              # Production build
bengal serve              # Dev server with live reload
bengal validate           # Health checks
bengal new page about     # Create page
bengal graph report       # Site structure analysis
```

Short aliases: `bengal b` (build), `bengal s` (serve), `bengal v` (validate)

---

## Features

### Content Authoring

**Markdown with directives** — Tabs, admonitions, dropdowns, code blocks, cards, and more:

~~~markdown
:::{note} Pro tip
You can nest **any markdown** inside directives.
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

**Frontmatter** for metadata, visibility control, and custom templates:

```yaml
---
title: My Page
date: 2025-12-01
hidden: true           # Exclude from nav, search, sitemap
template: custom.html  # Custom template
---
```

### Auto-Generated Documentation

Generate docs from source code—no imports required:

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
pip install bengal[github]     # GitHub source
pip install bengal[notion]     # Notion source
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

| Feature | Description |
|---------|-------------|
| **Parallel builds** | Utilizes all CPU cores |
| **Incremental rebuilds** | Only rebuild changed files |
| **Zstd cache** | 12-14x compression, 10x faster I/O |
| **Memory-optimized** | Streaming mode for 5K+ page sites |

### Site Analysis

```bash
bengal graph report    # Full connectivity analysis
bengal graph orphans   # Find unlinked pages
bengal graph suggest   # Link recommendations
bengal analyze         # Unified site analysis
```

### Health Checks

```bash
bengal validate                    # Run all checks
bengal validate --watch            # Continuous validation
bengal health linkcheck            # Check all links
bengal fix                         # Auto-fix common issues
```

---

## Configuration

Bengal uses a directory-based config system with environment and profile support:

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

**Minimal `bengal.toml`:**

```toml
[site]
title = "My Site"
baseurl = "https://example.com"
```

**Environment-aware builds:**

```bash
bengal build -e production    # Uses production config
bengal serve -e local         # Uses local config (default)
```

**Build profiles:**

```bash
bengal build --profile writer     # Fast, clean output
bengal build --profile theme-dev  # Template debugging
bengal build --profile dev        # Full observability
```

---

## Project Structure

```
mysite/
├── content/          # Markdown pages
│   ├── index.md
│   └── docs/
├── templates/        # Custom Jinja2 templates (optional)
├── assets/           # Static files (CSS, JS, images)
├── data/             # YAML/JSON data files
├── config/           # Configuration directory
└── public/           # Build output
```

---

## Theming

Bengal ships with a modern, accessible default theme featuring:

- Dark mode with system preference detection
- Responsive design with mobile navigation
- Syntax highlighting with copy buttons
- Table of contents with scroll spy
- Full-text search (Lunr.js)
- Semantic design tokens

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

- **Python 3.14+** (takes advantage of free-threading and modern features)
- Works on Linux, macOS, Windows

---

## Philosophy

Bengal prioritizes **correctness and clarity over backwards compatibility**.

Each release represents the best solution we know how to deliver. When existing behavior no longer reflects the best design, it may be changed or removed. Upgrades require reading release notes and making any necessary changes.

- **Fail loudly** — Breaking changes produce clear errors, not silent degradation
- **User control** — You choose when to upgrade; we choose what changes
- **No hidden layers** — No compatibility shims, fallbacks, or deprecated code paths

This approach keeps the codebase healthy and allows rapid evolution. If you need multi-year stability guarantees, pin your version.

See the full [Project Philosophy](https://lbliii.github.io/bengal/docs/about/philosophy/) for details.

---

## Documentation

📚 Full documentation at **[lbliii.github.io/bengal](https://lbliii.github.io/bengal/)**

---

## Development

```bash
git clone https://github.com/lbliii/bengal.git
cd bengal
uv sync --group dev    # Install with dev dependencies
pytest                 # Run tests
```

---

## License

MIT
