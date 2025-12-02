# Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/bengal.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A pythonic static site generator with incremental builds, parallel processing, and auto-generated API docs.

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

- **Incremental builds** with dependency tracking (18-42x faster than full builds)
- **Parallel processing** with free-threaded Python support
- **Jinja2 templates** with shortcodes and MyST Markdown
- **Auto-generated docs** from Python source and CLI applications
- **Environment-aware config** (auto-detects Netlify, Vercel, GitHub Actions)
- **Asset optimization** with fingerprinting

## Requirements

- Python 3.14+ (recommended: free-threaded build for 1.8x faster rendering)
- See [installation guide](https://bengal.dev/docs/getting-started/installation/) for setup

## Documentation

📚 **[bengal.dev](https://bengal.dev)**

- [Getting Started](https://bengal.dev/docs/getting-started/) — Installation, quickstarts by role
- [Guides](https://bengal.dev/docs/guides/) — Tutorials and how-tos
- [Reference](https://bengal.dev/docs/reference/) — Architecture, directives, configuration
- [CLI Reference](https://bengal.dev/cli/) — All commands and options
- [API Reference](https://bengal.dev/api/) — Python API documentation

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

See [configuration reference](https://bengal.dev/docs/reference/architecture/tooling/config/) for all options.

## Project Structure

```
mysite/
├── bengal.toml          # Configuration
├── content/             # Markdown content
├── templates/           # Custom templates (optional)
├── assets/              # Static assets
└── public/              # Generated output
```

## Development

```bash
git clone https://github.com/llane/bengal.git
cd bengal
pip install -e ".[server]"
```

See [contributor quickstart](https://bengal.dev/docs/getting-started/contributor-quickstart/) for development setup.

## License

MIT License
