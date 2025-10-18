# Bengal

A Python static site generator.

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
```

**Using pip:**

```bash
pip install -e .
```

For the released version (once available on PyPI):

```bash
pip install bengal
# or with uv: uv pip install bengal
```

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
fast_mode = true        # Maximum speed (recommended)

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
