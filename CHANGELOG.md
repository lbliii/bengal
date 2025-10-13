# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-13

### Initial Alpha Release

Bengal 0.1.0 is an alpha release of a high-performance static site generator optimized for Python 3.13+.

#### Core Features

**Build System**
- Parallel processing with ThreadPoolExecutor for fast builds
- Incremental builds with dependency tracking (15-50x speedup)
- Streaming builds for memory efficiency on large sites
- Smart caching with automatic invalidation
- Build profiles: writer, theme-dev, developer

**Content & Organization**
- Markdown content with YAML/TOML front matter
- Hierarchical sections with automatic navigation
- Taxonomy system (tags, categories)
- Related posts with tag-based similarity
- Menu system with nested navigation
- Breadcrumb generation

**Templates & Rendering**
- Jinja2 template engine with custom filters and tests
- Template caching and reuse
- Theme system with swizzling support
- Partial templates and components
- Syntax highlighting with Pygments (cached)

**API Documentation**
- AST-based Python documentation generation (no imports)
- Support for Google, NumPy, and Sphinx docstring formats
- Automatic cross-reference resolution
- Configurable visibility (private, special methods)

**Assets & Optimization**
- Asset fingerprinting for cache busting
- CSS and JavaScript minification
- Image optimization
- Parallel asset processing
- Optional Node.js pipeline (SCSS, PostCSS, esbuild)

**SEO & Discovery**
- Automatic sitemap.xml generation
- RSS feed generation
- JSON search index
- LLM-friendly text output formats
- Meta tag optimization

**Developer Experience**
- CLI scaffolding (`bengal new site`, `bengal new page`)
- Development server with hot reload
- File watching with automatic rebuilds
- Rich console output with progress tracking
- Health validation system
- Performance profiling tools

#### Requirements

- **Python 3.13+** (3.14t recommended for 1.8x speedup)
- See `pyproject.toml` for dependencies

---

## Project Status

**v0.1.0 is an alpha release** suitable for:
- ✅ Early adopters and experimenters
- ✅ Documentation sites (100-5,000 pages)
- ✅ Blogs and content sites
- ✅ Projects needing AST-based API docs
- ✅ Python 3.13+ projects

**Not yet recommended for:**
- ❌ Mission-critical production without testing

---

## Links

- [Documentation](https://github.com/lbliii/bengal)
- [Issue Tracker](https://github.com/lbliii/bengal/issues)
- [Contributing Guide](CONTRIBUTING.md)
- [Getting Started](GETTING_STARTED.md)
