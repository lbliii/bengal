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

## Quick Start

```bash
pip install bengal
bengal new site mysite
cd mysite
bengal serve
```

Open `localhost:5173`. Edit files in `content/`, changes appear instantly.

**Commands:**

| Command | Description |
|---------|-------------|
| `bengal build` | Production build |
| `bengal serve` | Dev server with live reload |
| `bengal validate` | Health checks and validation |
| `bengal fix` | Auto-fix common issues |
| `bengal graph report` | Site structure analysis |

Aliases: `b` (build), `s` (serve), `v` (validate)

---

## What's New in 0.1.5

**Performance:**
- **NavTree architecture** — Pre-computed navigation with O(1) template access
- **Zstandard caching** — 12-14x compression, 10x faster cache I/O (PEP 784)
- **Parallel health checks** — 50-70% faster validation

**Developer Experience:**
- **Directive system v2** — Named closers, typed options, nesting contracts
- **Dev server modernization** — Process isolation, Rust-based file watching
- **Media embed directives** — YouTube, Vimeo, Gist, CodePen, Asciinema

**Robustness:**
- **Proactive template validation** — Syntax errors caught before build
- **Autodoc incremental builds** — Only regenerate changed source files
- **Build-integrated validation** — Tiered health checks during builds

See the [full changelog](changelog.md) for details.

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

| Feature | Benefit |
|---------|---------|
| Parallel builds | Utilizes all CPU cores |
| Incremental rebuilds | Only rebuild changed files |
| Zstd cache | 12-14x compression, 10x faster I/O |
| Memory-optimized | Streaming mode for 5K+ page sites |

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
