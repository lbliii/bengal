# Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/bengal.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Build static sites in Python, without the compromises.**

Bengal combines Python-native developer experience with production-grade performance. Everything is Python—templates, plugins, config. Fast incremental builds. Flexible content system. Modern by default.

## Why Bengal?

- **Zero Context Switching** — Everything is Python. No Go templates or Ruby gems to learn.
- **Fast Enough, Built Right** — Parallel processing and free-threading ensure builds complete in seconds.
- **Modern by Default** — Python 3.14+, incremental builds, interactive CLI, great defaults.
- **Flexible Content** — Not just docs, not just blogs—build mixed-content sites in one tool.

## Quick Start

```bash
# Install
pip install bengal

# Create a new site (interactive wizard)
bengal new site mysite
cd mysite

# Build and serve
bengal site build
bengal site serve
```

**For maximum speed** (Python 3.14+):

```bash
PYTHON_GIL=0 bengal site build --fast
```

## Features

- **Incremental builds** — Only rebuild what changed (18-42x faster than full builds)
- **Parallel processing** — Free-threaded Python support for large sites
- **Jinja2 templates** — Industry-standard templating, readable and extensible
- **Auto-generated docs** — API docs from Python source, CLI docs from applications
- **Environment-aware** — Auto-detects Netlify, Vercel, GitHub Actions
- **Asset optimization** — Fingerprinting and minification built-in

## When to Use Bengal

**Choose Bengal if:**
- You're a Python developer (or team)
- You want mixed-content sites (docs + blog + landing pages)
- You value developer experience over raw speed
- You need incremental builds for fast iteration

**Consider alternatives if:**
- You have 50,000+ pages → Use [Hugo](https://gohugo.io) (raw speed wins)
- You need React/Vue SPAs → Use [Next.js](https://nextjs.org) or [Astro](https://astro.build)
- You're building docs-only → Use [MkDocs](https://www.mkdocs.org) with Material theme

We want you to be happy, even if it means using another tool.

## Requirements

- Python 3.14+ (recommended: free-threaded build for 1.8x faster rendering)
- See [installation guide](https://lbliii.github.io/bengal/docs/get-started/installation/) for setup

## Documentation

📚 **[bengal.dev](https://lbliii.github.io/bengal/)**

- [Get Started](https://lbliii.github.io/bengal/docs/get-started/) — Installation, quickstarts by role
- [Tutorials](https://lbliii.github.io/bengal/docs/tutorials/) — Hands-on learning journeys
- [Reference](https://lbliii.github.io/bengal/docs/reference/) — Architecture, configuration, directives
- [CLI Reference](https://lbliii.github.io/bengal/cli/) — All commands and options
- [API Reference](https://lbliii.github.io/bengal/api/) — Python API documentation

## Commands

```bash
bengal new site mysite          # Create site with interactive wizard
bengal new page my-post         # Create a new page
bengal site build               # Build the site
bengal site serve               # Start dev server with live reload
bengal validate                 # Run health checks
bengal --help                   # See all commands
```

## Configuration

Create `bengal.toml` in your project root:

```toml
[site]
title = "My Site"
baseurl = "https://example.com"

[build]
fast_mode = true

[theme]
name = "default"
```

See [configuration reference](https://lbliii.github.io/bengal/docs/reference/architecture/tooling/config/) for all options.

## Project Structure

```
mysite/
├── bengal.toml          # Configuration
├── content/             # Markdown content
├── templates/           # Custom templates (optional)
├── assets/              # Static assets
└── public/              # Generated output
```

## Comparison

| Feature | Bengal | Hugo | MkDocs |
|---------|--------|------|--------|
| **Language** | Python | Go | Python |
| **Templating** | Jinja2 | Go Templates | Jinja2 |
| **Speed** | Fast (~200 pages/s) | Instant | Fast |
| **Mixed Content** | ✅ Docs + Blog + Pages | ✅ | ❌ Docs only |
| **Best For** | Python devs, mixed sites | Massive sites (50k+) | Documentation |

Hugo is the speed king for massive sites. Bengal is fast enough for most sites and gives you Python-native extensibility Hugo can't match.

## Development

```bash
git clone https://github.com/llane/bengal.git
cd bengal
pip install -e ".[server]"
```

See [contributor quickstart](https://lbliii.github.io/bengal/docs/get-started/quickstart-contributor/) for development setup.

## License

MIT License
