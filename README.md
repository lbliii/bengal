# Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/bengal.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A pythonic static site generator.

## Features

- Markdown-based content with front matter
- Incremental builds with dependency tracking
- Parallel processing with ThreadPoolExecutor
- Template engine with Jinja2
- Automatic navigation and breadcrumbs
- Taxonomy system (tags, categories)
- Menu system with hierarchical navigation
- Development server with file watching
- API documentation generation from Python source
- SEO features (sitemap, RSS feeds)
- Health validation system

## Installing Python 3.14

Bengal works best with Python 3.14. Here's how to install it:

### Using pyenv (recommended for managing versions)

```bash
# Install pyenv (see https://github.com/pyenv/pyenv for full instructions)
brew install pyenv  # On macOS with Homebrew
# or: curl https://pyenv.run | bash

pyenv install 3.14.0
pyenv global 3.14.0

# Initialize pyenv in your shell profile (add these lines to ~/.zshrc or ~/.bash_profile):
# export PYENV_ROOT="$HOME/.pyenv"
# export PATH="$PYENV_ROOT/bin:$PATH"
# eval "$(pyenv init --path)"
# eval "$(pyenv init -)"
# eval "$(pyenv virtualenv-init -)"
#
# Then reload your shell:
# source ~/.zshrc  # or source ~/.bash_profile
#
# Verify with: python --version (should show 3.14.0)
```

### Official Installer

Download from [python.org/downloads](https://www.python.org/downloads/release/python-3140/).

### Create a Virtual Environment

Always use a virtual environment:

```bash
python -m venv bengal-env
source bengal-env/bin/activate  # On Windows: bengal-env\Scripts\activate
```

## Requirements

Python 3.14 or later

Recommended: Python 3.14t (free-threaded) for up to 1.8x faster rendering. See [INSTALL_FREE_THREADED.md](INSTALL_FREE_THREADED.md) for setup instructions.

## Cloning and Installation

To install the latest development version:

```bash
git clone https://github.com/llane/bengal.git
cd bengal
```

**Using uv (recommended):**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Bengal in editable mode for development
uv pip install -e .

# Or with dev server support (file watching auto-reload)
uv pip install -e ".[server]"
```

**Using pip:**

```bash
pip install -e .

# All features included by default (hot reload, minification, etc.)
```

For the released version (once available on PyPI):

```bash
pip install bengal
```

**Optional Dependencies:**
- `css` - Advanced CSS optimization (uses `lightningcss`)

**Note**: python-markdown parser is available if manually installed (`pip install markdown`). Bengal defaults to mistune for better performance

## Quick Start

```bash
# Create a new site. An interactive wizard will guide you through presets for different site types:
# - Blog (personal/professional writing)
# - Documentation (technical docs/guides)
# - Portfolio (showcase your work)
# - Business (company/product site)
# - Resume (professional CV site)
# - Blank or Custom
bengal new site mysite
cd mysite

# The wizard creates structure with sample content. You can then:
# Create additional pages
bengal new page my-first-post

# Build the site
bengal site build

# For maximum speed (recommended)
PYTHON_GIL=0 bengal site build --fast

# Start development server with file watching
bengal site serve
```

**💡 Tip:** Add `fast_mode = true` to the `[build]` section in your `bengal.toml` to enable fast mode by default.

## Build Profiles

Bengal provides different build profiles for different use cases:

- **Default**: Minimal output focused on errors and warnings
- **Theme Developer** (`--theme-dev`): Extra template and navigation validation
- **Developer** (`--dev`): Full debug output with memory profiling and performance metrics

## Architecture

Bengal uses a modular architecture with clear separation between Site, Page, Section, and Asset objects. The rendering pipeline processes Markdown content through templates and applies post-processing steps. An incremental build system tracks file changes and dependencies to rebuild what's necessary.

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## Configuration

Create a `bengal.toml` or `bengal.yaml` in your project root. Bengal uses sensible defaults for most settings, so you only need to configure what you want to change:

```toml
[site]
title = "My Bengal Site"
baseurl = "https://example.com"
description = "Site description"
language = "en"
author = "Your Name"

[build]
output_dir = "public"
content_dir = "content"
fast_mode = true                    # Maximum speed (recommended)
cache_templates = true              # Cache compiled templates (10-15% faster)
auto_regenerate_autodoc = false     # Auto-regenerate docs when source changes

# Optional: Disable default features if needed
# incremental = false               # Force full rebuilds
# minify_html = false               # Keep HTML unminified for debugging
# parallel = false                  # Disable parallel processing
# generate_sitemap = false          # Skip sitemap
# generate_rss = false              # Skip RSS feed

# Theme Configuration
[theme]
name = "default"                    # Theme name (default, or custom theme in themes/ dir)
default_appearance = "system"       # Options: "light", "dark", "system" (follows OS)
default_palette = ""                # Color palette (empty = default, or palette name)

# Font Configuration - Auto-downloads and self-hosts Google Fonts
[fonts]
primary = "Inter:400,600,700"           # Body text
heading = "Playfair Display:700"        # Headings
code = "JetBrains Mono:400"             # Code blocks

# Assets
[assets]
minify = true
fingerprint = true
optimize = true

# Optional: Node-based asset pipeline (requires Node v22 LTS)
# pipeline = true
# scss = true
# postcss = true
# bundle_js = true

# Markdown Configuration
[markdown]
parser = "mistune"
table_of_contents = true
gfm = true                          # GitHub Flavored Markdown

# Taxonomies (tags, categories, etc.)
[taxonomies]
tags = "tags"
categories = "categories"

# Menu Configuration
[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 2

# Search Page (special page, auto-enabled if template exists)
[search]
enabled = true
path = "/search/"
template = "search.html"

# API Documentation Generation
[autodoc.python]
enabled = true
source_dirs = ["src"]
output_dir = "content/api"
docstring_style = "auto"            # Options: auto, google, numpy, sphinx

exclude = [
    "*/tests/*",
    "*/__pycache__/*",
]

include_private = false             # Include _private methods
include_special = false             # Include __special__ methods

# CLI Documentation Generation
[autodoc.cli]
enabled = true
app_module = "myapp.cli:main"       # module_path:attribute format
output_dir = "content/cli"
framework = "click"                 # Options: click, argparse, typer
```

### HTML Output Formatting

Control whitespace and comments in generated HTML. Defaults keep output compact and safe.

```toml
# Backwards-compatibility: simple boolean toggle
# minify_html = true   # Enabled by default; set false to keep more whitespace

# Advanced controls (overrides minify_html when set)
[html_output]
mode = "minify"            # Options: "minify", "pretty", "raw"
remove_comments = true     # Strip HTML comments (keeps IE conditionals)
collapse_blank_lines = true
```

- "minify": collapses inter-tag whitespace and blank lines, keeps protected regions (`pre`, `code`, `textarea`, `script`, `style`) intact.
- "pretty": removes consecutive blank lines and trailing whitespace between tags for stable diffs.
- "raw": no formatting.

Per-page escape hatch: add `no_format: true` in a page's front matter to skip formatting for that page.

**Default Features** (enabled automatically, no config needed):

- ✅ Parallel builds
- ✅ Incremental builds (18-42x faster!)
- ✅ HTML minification (15-25% smaller)
- ✅ Asset optimization and fingerprinting
- ✅ Sitemap and RSS generation
- ✅ JSON + LLM text output formats
- ✅ Link validation
- ✅ Build quality checks

## Project Structure

```text
mysite/
├── bengal.toml          # Site configuration
├── content/             # Your content files
│   ├── index.md
│   └── posts/
│       └── first-post.md
├── templates/           # Custom templates
│   ├── base.html
│   └── partials/
├── assets/              # Static assets
│   ├── css/
│   ├── js/
│   └── images/
└── public/              # Generated output
```

## Commands

Bengal commands are organized into logical groups for better discoverability. Use `bengal --help` to see all command groups, or `bengal <group> --help` to see commands within a group (e.g., `bengal site --help`).

### Site Management (`bengal site`)

```bash
# Build site
bengal site build

# Build with options
bengal site build --fast                  # Quiet output + guaranteed parallel
PYTHON_GIL=0 bengal site build --fast    # Maximum speed (no GIL warnings)
bengal site build --incremental           # Rebuild changed files
bengal site build --strict                # Fail on errors (for CI)

# Development server (default: 5173)
bengal site serve --port 5173

# Clean output
bengal site clean
```

### Creating New Content (`bengal new`)

```bash
# Create a new site
bengal new site mysite

# Create a new page
bengal new page my-page --section blog

# Create a new layout template
bengal new layout article

# Create a new partial template
bengal new partial sidebar

# Create a new theme
bengal new theme my-theme
```

### Project Management (`bengal project`)

```bash
# Initialize project structure
bengal project init

# Set working profile (dev, themer, writer, ai)
bengal project profile dev

# Validate configuration
bengal project validate

# Show project info and statistics
bengal project info

# View/manage configuration
bengal project config
bengal project config site.title "My New Title" --set
```

### Developer Utilities (`bengal utils`)

```bash
# Generate API documentation
bengal utils autodoc --source mylib --output content/api

# Theme management
bengal utils theme list
bengal utils theme info <slug>
bengal utils theme discover
bengal utils theme install bengal-theme-starter
bengal utils theme new mybrand --mode site --output .

# Asset management
bengal utils assets minify
bengal utils assets optimize

# Performance analysis
bengal utils perf analyze

# Graph analysis
bengal utils graph analyze --stats --tree
bengal utils graph pagerank
bengal utils graph communities
bengal utils graph bridges
bengal utils graph suggest
```

## Themes

Bengal supports three types of themes: project themes (under `themes/`), installed themes (via pip/uv), and bundled themes.

```bash
# List available themes (project | installed | bundled)
bengal utils theme list

# Show info about a theme slug (paths, version)
bengal utils theme info <slug>

# Discover swizzlable templates/partials in active theme chain
bengal utils theme discover

# Install a theme via uv/pip (warns if name is non-canonical)
bengal utils theme install bengal-theme-starter

# Scaffold a new theme
## Site-local theme under themes/<slug>
bengal utils theme new mybrand --mode site --output .
## Installable package scaffold in current directory
bengal utils theme new mybrand --mode package --output .

# Or use bengal new theme for quick site-local themes
bengal new theme mybrand
```

Configuration to select and customize a theme:

```toml
[theme]
name = "mybrand"                  # Uses project themes/mybrand, installed bengal-theme-mybrand, or bundled
default_appearance = "system"     # Options: "light", "dark", "system" (follows OS preference)
default_palette = ""              # Color palette name (empty = default)
```

**Legacy configuration** (still supported):

```toml
[build]
theme = "mybrand"  # Simple string format still works for backwards compatibility
```

Naming convention for installable themes (recommended): `bengal-theme-<slug>`.

## API Documentation (Autodoc)

Bengal can automatically generate API documentation from Python source code and CLI applications using AST parsing.

### Python API Documentation

Configure in `bengal.toml`:

```toml
[autodoc.python]
enabled = true
source_dirs = ["src/mylib"]
output_dir = "content/api"
docstring_style = "auto"  # Options: auto, google, numpy, sphinx

exclude = [
    "*/tests/*",
    "*/__pycache__/*",
]

include_private = false   # Include _private methods
include_special = false   # Include __special__ methods
```

Or generate on-demand:

```bash
bengal utils autodoc --source mylib --output content/api
```

### CLI Documentation

Automatically document Click, Argparse, or Typer CLI applications:

```toml
[autodoc.cli]
enabled = true
app_module = "myapp.cli:main"  # module_path:attribute format
output_dir = "content/cli"
framework = "click"            # Options: click, argparse, typer
include_hidden = false         # Include hidden commands
```

### Autodoc Features

- **AST-based extraction** - No imports required, works with any Python code
- **Multiple docstring formats** - Supports Google, NumPy, and Sphinx styles
- **Auto-regeneration** - Set `auto_regenerate_autodoc = true` in `[build]` to automatically update docs when source changes
- **CLI frameworks** - Built-in support for Click, Argparse, and Typer
- **Smart filtering** - Exclude tests, caches, and private members

## Development Status

Bengal is functional and under active development.

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details.

## License

MIT License
