# Bengal SSG

A Python-based static site generator with modular architecture, incremental builds, and comprehensive template functions.

## Features

### Performance
- **Fast Full Builds**: ~0.3s for 100 pages, ~3.5s for 1000 pages (competitive with Eleventy, faster than Jekyll)
- **Incremental Builds**: 18-42x faster rebuilds on 10-100 page sites (SHA256 change detection, dependency tracking)
- **Parallel Processing**: 2-4x speedup for asset processing and post-processing tasks
- **Sub-linear Scaling**: 32x time increase for 1024x more files (excellent scaling efficiency)
- **Multiple Markdown Engines**: Mistune (42% faster) or python-markdown

#### SSG Comparison (100 pages, cold build)
| SSG | Build Time | Notes |
|-----|-----------|-------|
| Hugo | ~0.1-0.5s | Go - fastest |
| **Bengal** | **~0.3s** | **Python - competitive!** |
| Eleventy | ~1-3s | JavaScript |
| Jekyll | ~3-10s | Ruby |
| Gatsby | ~5-15s | React framework |

*Benchmark methodology: [CSS-Tricks SSG comparison](https://css-tricks.com/comparing-static-site-generator-build-times/)*

### Content & Templates
- **75 Template Functions**: Strings, collections, math, dates, URLs, content, data, files, images, SEO, taxonomies, pagination
- **Autodoc (NEW!)**: AST-based API documentation generation from Python source (175+ pages/sec, no imports needed)
- **Navigation System**: Automatic next/prev, breadcrumbs, hierarchical navigation
- **Menu System**: Config-driven hierarchical menus with active state detection
- **Cascade System**: Frontmatter inheritance from sections to child pages
- **Taxonomy System**: Automatic tag/category pages with pagination

### Development
- **Health Checks**: 9 validators for output quality, config, menus, links, navigation, taxonomy, rendering, cache, performance
- **Dev Server**: File watching with automatic rebuilds
- **Modular Architecture**: Clean separation of Site, Page, Section, Asset objects

### Output
- **SEO Features**: Sitemap generation, RSS feeds, link validation
- **Asset Handling**: Copy and organize static assets

## Installation

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

## Architecture

Bengal follows a modular design with clear separation of concerns:

- **Site Object**: Orchestrates the entire build process
- **Page Object**: Represents individual content pages with metadata and rendering
- **Section Object**: Manages content hierarchy and grouping
- **Asset Object**: Handles static files
- **Rendering Pipeline**: Parse → Build AST → Apply Templates → Render → Post-process
- **Cache System**: Tracks dependencies and file changes for incremental builds
- **Health System**: Validates build quality across 9 aspects

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation.

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
```

## Project Structure

```
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

## CLI Usage

```bash
# Full build
bengal build

# Incremental build (only changed files)
bengal build --incremental

# Parallel build (default)
bengal build --parallel

# Strict mode (fail on errors, recommended for CI)
bengal build --strict

# Generate API documentation from Python source
bengal autodoc --source mylib --output content/api

# Development server with file watching
bengal serve --port 5173

# Clean output directory
bengal clean
```

## API Documentation (Autodoc)

Bengal includes a powerful autodoc system for generating API documentation from Python source code:

```bash
# Generate docs for a module
bengal autodoc --source src/mylib --output content/api

# Use config file
bengal autodoc  # reads from bengal.toml

# Show statistics
bengal autodoc --stats --verbose
```

**Configuration** (`bengal.toml`):

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

include_private = false  # Include _private methods
include_special = false  # Include __special__ methods
```

**Features:**
- ⚡ **Fast**: AST-based extraction (no imports!) - 175+ pages/sec
- 🎨 **Flexible**: Fully customizable Jinja2 templates
- 📝 **Smart**: Parses Google, NumPy, and Sphinx docstring formats
- 🔒 **Safe**: No code execution, works with any dependencies
- 📊 **Rich**: Extracts args, returns, raises, examples, type hints, deprecations

See the [showcase site](examples/showcase) for a live example with full Bengal API docs!

## Development Status

Bengal SSG is functional and under active development.

**Implemented:**
- Core object model (Site, Page, Section, Asset)
- Rendering pipeline with Mistune and python-markdown support
- Incremental builds with dependency tracking
- Parallel processing for pages, assets, and post-processing
- 75 template functions across 15 modules
- **Autodoc system (AST-based API documentation generation)** ⭐ NEW
- Navigation system (next/prev, breadcrumbs, hierarchical)
- Menu system (config-driven, hierarchical)
- Cascade system (frontmatter inheritance)
- Taxonomy system (tags, categories, dynamic pages)
- Table of contents (auto-generated from headings)
- Health check system (9 validators)
- CLI with multiple build modes
- Development server with file watching
- SEO features (sitemap, RSS)

**Current Priorities:**
- Test coverage improvements (current: 64%, target: 85%)
- Documentation site
- Enhanced asset pipeline (minification, optimization)
- Plugin system with build hooks

**Test Coverage:**
- 475 passing tests
- 64% overall coverage (2,881 of 4,517 lines)
- High coverage: Cache (95%), Utils (96%), Postprocess (96%), Navigation (98%)
- Needs work: CLI (0%), Dev Server (0%), Health validators (13-98%)

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete roadmap and technical details.

## License

MIT License

