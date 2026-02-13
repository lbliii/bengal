# ᓚᘏᗢ Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://pypi.org/project/bengal/)

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
- **Extensible** — Pluggable engines for templates, Markdown, and syntax highlighting

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
  🛒 Product         - Product site with listings and features
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
| `default` | Basic site structure | Home page only |
| `blog` | Personal/professional blog | blog, about |
| `docs` | Technical documentation | getting-started, guides, reference |
| `portfolio` | Showcase work | about, projects, blog, contact |
| `product` | Product site with listings | products, features, pricing, contact |
| `resume` | Professional CV | Single resume page |
| `landing` | Single-page landing | Home, privacy, terms |
| `changelog` | Release notes timeline | Changelog with versions |

</details>

<details>
<summary><strong>Add Sections to Existing Sites</strong> — Expand without recreating</summary>

Add new content sections to an existing Bengal site:

```bash
# Add multiple sections
bengal init --sections docs --sections tutorials

# Add sections with sample content
bengal init --sections blog --with-content --pages-per-section 5

# Preview without creating files
bengal init --sections api --dry-run
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

| Feature | Description | Docs |
|---------|-------------|------|
| **Directives** | Tabs, admonitions, cards, dropdowns, code blocks | [Content →](https://lbliii.github.io/bengal/docs/content/) |
| **Autodoc** | Generate API docs from Python, CLI, OpenAPI | [Autodoc →](https://lbliii.github.io/bengal/docs/content/sources/autodoc/) |
| **Remote Sources** | Pull content from GitHub, Notion, REST APIs | [Sources →](https://lbliii.github.io/bengal/docs/content/sources/) |
| **Image Processing** | Resize, crop, format conversion (WebP/AVIF), srcset generation | [Images →](https://lbliii.github.io/bengal/docs/theming/templating/image-processing/) |
| **Content Collections** | Type-safe frontmatter with dataclass/Pydantic schemas | [Collections →](https://lbliii.github.io/bengal/docs/content/collections/) |
| **Theming** | Dark mode, responsive, syntax highlighting, search | [Theming →](https://lbliii.github.io/bengal/docs/theming/) |
| **Validation** | Health checks, broken link detection, auto-fix | [Building →](https://lbliii.github.io/bengal/docs/building/) |
| **Performance** | Parallel builds, incremental rebuilds, streaming | [Large Sites →](https://lbliii.github.io/bengal/docs/building/performance/large-sites/) |
| **Zero-Config Deploy** | Auto-detects GitHub Pages, Netlify, Vercel | [Deployment →](https://lbliii.github.io/bengal/docs/building/deployment/) |

📚 **Full documentation**: [lbliii.github.io/bengal](https://lbliii.github.io/bengal/)

---

## Configuration

<details>
<summary><strong>Single-file</strong> — Simple projects</summary>

```toml
# bengal.toml
[site]
title = "My Site"
baseurl = "https://example.com"
```

</details>

<details>
<summary><strong>Directory-based</strong> — Multi-environment projects</summary>

```
config/
├── _default/           # Base configuration
│   ├── site.yaml
│   └── build.yaml
├── environments/       # Environment overrides
│   └── production.yaml
└── profiles/           # Build profiles
    └── dev.yaml
```

```bash
bengal build -e production    # Production environment
bengal build --profile dev    # Development profile
```

</details>

📖 **Configuration guide**: [Configuration →](https://lbliii.github.io/bengal/docs/building/configuration/)

---

## Project Structure

```
mysite/
├── content/          # Markdown pages
├── templates/        # Custom templates (optional)
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

## Pluggable Engines

Bengal follows a "bring your own" pattern — swap engines without changing your content.

<details>
<summary><strong>Template Engines</strong></summary>

| Engine | Description | Install |
|--------|-------------|---------|
| **Kida** (default) | Bengal's native engine. 2-5x faster than Jinja2, free-threading safe, Jinja2-compatible syntax | Built-in |
| **Jinja2** | Industry-standard with extensive ecosystem | Built-in |

```yaml
# config/_default/site.yaml
template_engine: kida  # or jinja2
```

</details>

<details>
<summary><strong>Markdown Parsers</strong></summary>

| Parser | Description | Best For |
|--------|-------------|----------|
| **Patitas** (default) | Bengal's native parser. Typed AST, O(n) parsing, thread-safe | Python 3.14+, large sites |
| **Mistune** | Fast, modern parser | General use |
| **Python-Markdown** | Full-featured, extensive extensions | Complex edge cases |

```yaml
# config/_default/content.yaml
markdown:
  parser: patitas  # default, or mistune (legacy), python-markdown
```

</details>

<details>
<summary><strong>Syntax Highlighters</strong></summary>

| Backend | Description | Performance |
|---------|-------------|-------------|
| **[Rosettes](https://github.com/lbliii/rosettes)** (default) | Lock-free, 55+ languages, O(n) guaranteed | 3.4x faster than Pygments |

```yaml
# config/_default/theme.yaml
highlighting:
  backend: rosettes
```

Rosettes is now a standalone package: [`pip install rosettes`](https://pypi.org/project/rosettes/)

Custom backends can be registered via `register_backend()`.

</details>

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

## The Bengal Ecosystem

A structured reactive stack — every layer written in pure Python for 3.14t free-threading.

| | | | |
|--:|---|---|---|
| **ᓚᘏᗢ** | **Bengal** | Static site generator ← You are here | [Docs](https://lbliii.github.io/bengal/) |
| **∿∿** | [Purr](https://github.com/lbliii/purr) | Content runtime | — |
| **⌁⌁** | [Chirp](https://github.com/lbliii/chirp) | Web framework | [Docs](https://lbliii.github.io/chirp/) |
| **=^..^=** | [Pounce](https://github.com/lbliii/pounce) | ASGI server | [Docs](https://lbliii.github.io/pounce/) |
| **)彡** | [Kida](https://github.com/lbliii/kida) | Template engine | [Docs](https://lbliii.github.io/kida/) |
| **ฅᨐฅ** | [Patitas](https://github.com/lbliii/patitas) | Markdown parser | [Docs](https://lbliii.github.io/patitas/) |
| **⌾⌾⌾** | [Rosettes](https://github.com/lbliii/rosettes) | Syntax highlighter | [Docs](https://lbliii.github.io/rosettes/) |

Python-native. Free-threading ready. No npm required.

---

## License

MIT
