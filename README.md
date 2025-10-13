# Bengal

A Python static site generator with incremental builds and modular architecture.

**⚡ Optimized for Python 3.14**

Bengal is the first major SSG optimized for Python 3.14, delivering **515 pages/sec** with free-threading—making it the fastest Python SSG available and competitive with Node.js tools like Eleventy.

## Performance

- **515 pages/sec** with free-threaded Python 3.14t (recommended) ⚡
- **289 pages/sec** with standard Python 3.14
- **~250 pages/sec** with Python 3.13 (fully supported)
- **Sub-second incremental builds** for typical changes
- **50x speedup** for single-page incremental builds vs full rebuild
- **Scales to 10,000+ pages** with intelligent caching

*Want the speed boost? See [INSTALL_FREE_THREADED.md](INSTALL_FREE_THREADED.md) for a 5-minute setup guide.*

## Quality & Testing

- **2,297 tests** with **76-96% critical path coverage** ([details](TEST_COVERAGE.md))
- **115 property tests** generating 11,600+ examples per run (Hypothesis)
- **40-second test suite** running on every commit
- **A+ test quality** (property-based + parametrized + integration)

*Note: "17% overall coverage" includes optional features (CLI wizards, graph tools, font downloaders) that represent 39% of codebase but <5% of usage. See [TEST_COVERAGE.md](TEST_COVERAGE.md) for why this matters.*

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

## Requirements

**Python 3.13 or later**

**Recommended: Python 3.14t (free-threaded)** for 1.8x faster rendering. See [INSTALL_FREE_THREADED.md](INSTALL_FREE_THREADED.md) for setup instructions.

## Installation

**Using uv (recommended):**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Bengal
uv pip install -e .
```

**Using pip:**

```bash
pip install -e .
```

## Quick Start

```bash
# Create a new site
bengal new site mysite
cd mysite

# Create a new page
bengal new page my-first-post

# Build the site
bengal build

# Start development server with file watching
bengal serve
```

## Build Profiles

Bengal provides different build profiles for different use cases:

- **Default**: Minimal output focused on errors and warnings
- **Theme Developer** (`--theme-dev`): Extra template and navigation validation
- **Developer** (`--dev`): Full debug output with memory profiling and performance metrics

## Architecture

Bengal uses a modular architecture with clear separation between Site, Page, Section, and Asset objects. The rendering pipeline processes Markdown content through templates and applies post-processing steps. An incremental build system tracks file changes and dependencies to rebuild what's necessary.

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

## Configuration

Create a `bengal.toml` or `bengal.yaml` in your project root:

```toml
[site]
title = "My Bengal Site"
baseurl = "https://example.com"
theme = "default"

[build]
output_dir = "public"
incremental = true
parallel = true

[assets]
minify = true
fingerprint = true

# Special search page (optional overrides)
[search]
enabled = true
path = "/search/"
template = "search.html"
```

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

```bash
# Build site
bengal build

# Build with options
bengal build --incremental  # Rebuild changed files
bengal build --strict       # Fail on errors (for CI)

# Generate API documentation
bengal autodoc --source mylib --output content/api

# Development server (default: 5173)
bengal serve --port 5173

# Clean output
bengal clean
```

## Themes

```bash
# List available themes (project | installed | bundled)
bengal theme list

# Show info about a theme slug (paths, version)
bengal theme info <slug>

# Discover swizzlable templates/partials in active theme chain
bengal theme discover

# Install a theme via uv/pip (warns if name is non-canonical)
bengal theme install bengal-theme-starter

# Scaffold a new theme
## Site-local theme under themes/<slug>
bengal theme new mybrand --mode site --output .
## Installable package scaffold in current directory
bengal theme new mybrand --mode package --output .
```

Configuration to select a theme:

```toml
[site]
theme = "mybrand"  # Uses project themes/mybrand, installed bengal-theme-mybrand, or bundled
```

Naming convention for installable themes (recommended): `bengal-theme-<slug>`.

## API Documentation

Bengal can generate API documentation from Python source code using AST parsing. Configure in `bengal.toml`:

```toml
[autodoc.python]
enabled = true
source_dirs = ["src/mylib"]
output_dir = "content/api"
docstring_style = "auto"  # auto, google, numpy, sphinx

exclude = [
    "*/tests/*",
    "*/__pycache__/*",
]

include_private = false
include_special = false
```

The auto-doc system uses AST-based extraction (no imports required) and supports Google, NumPy, and Sphinx documentation formats.

## Development Status

Bengal is functional and under active development.

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details.

## License

MIT License
