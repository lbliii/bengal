# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Cascading Frontmatter**: Hugo-style cascade functionality
  - Define metadata in section `_index.md` that automatically applies to child pages
  - Nested cascade accumulation through section hierarchies
  - Page values override cascade (sensible precedence)
  - Full test coverage (13 unit tests, 4 integration tests)
  - Documentation and examples included
- **Content Variable Substitution**: Use Jinja2 variables directly in markdown content
  - Pre-process content through Jinja2 before markdown parsing
  - Access `page.metadata`, `site`, and `config` in your markdown
  - Enables technical writers to use cascaded values inline: `{{ page.metadata.version }}`
  - Graceful error handling for template syntax errors
- **Content Organization Documentation**: New comprehensive guide
  - Explains `index.md` vs `_index.md` conventions
  - Best practices for structuring pages and sections
  - Examples for blogs, documentation sites, and product pages
  - Navigation and content discovery patterns

### Improved
- **Phase 1 Brittleness Fixes** (October 3, 2025)
  - **Robust URL Generation**: Replaced hardcoded output directory list with dynamic `site.output_dir` reference
    - Handles custom output directories correctly
    - Proper fallback with helpful warnings
    - Works with absolute and relative paths
  - **Configuration Validation**: Added lightweight validator (no external dependencies)
    - Type validation with sensible coercion (`"true"` → `True`, `"8"` → `8`)
    - Range validation (max_workers >= 0, port 1-65535, etc.)
    - Clear error messages guide users to fixes
    - Supports both flat and nested config formats
  - **Frontmatter Parsing**: Improved error recovery
    - Preserves content even when frontmatter YAML is invalid
    - Adds error metadata instead of losing everything
    - Encoding fallback (UTF-8 → latin-1) for compatibility
    - Clear warnings help users fix syntax errors
  - **Menu Building**: Added validation and cycle detection
    - Detects and warns about orphaned menu items (missing parents)
    - Prevents infinite loops from circular references
    - Graceful degradation (orphans become root items)
  - **Generated Pages**: Virtual path namespacing
    - Uses dedicated `.bengal/generated/` namespace
    - Eliminates conflicts with real content files
    - Better incremental build handling
    - Added to `.gitignore`

### Planned
- Incremental build system
- Plugin architecture with hooks
- Performance benchmarks
- Comprehensive documentation site
- Phase 2 hardening (type-safe accessors, constants module, etc.)

## [0.1.0] - 2025-10-02

### Added
- Initial release of Bengal SSG
- Core object model (Site, Page, Section, Asset)
- Rendering pipeline with Jinja2 templates
- Markdown parser with extensions (code highlighting, tables, TOC)
- CLI interface with commands:
  - `bengal build` - Build static site
  - `bengal serve` - Development server with hot reload
  - `bengal clean` - Clean output directory
  - `bengal new site/page` - Create new site or page
- Configuration system supporting TOML and YAML
- Content discovery with automatic section organization
- Asset pipeline with theme support
- Post-processing features:
  - XML sitemap generation
  - RSS feed generation
  - Link validation
- Production-ready default theme:
  - Responsive design (mobile, tablet, desktop)
  - Dark/light mode toggle with localStorage persistence
  - Mobile navigation menu
  - Modern CSS architecture (variables, reset, typography, utilities)
  - Component library (buttons, cards, tags, code blocks)
  - Syntax highlighting for code
- Pagination system:
  - Generic Paginator utility class
  - Automatic pagination for archive pages
  - Automatic pagination for tag pages
  - Configurable items per page
- Taxonomy support:
  - Automatic collection of tags and categories
  - Dynamic generation of tag index pages
  - Individual tag pages with post listings
- Navigation features:
  - Breadcrumb navigation (auto-generated from URLs)
  - 404 error page with helpful navigation
- SEO optimization:
  - Open Graph meta tags
  - Twitter Card meta tags
  - Canonical URLs
  - Clean URL structure (no `/index.html`)
- Accessibility features:
  - ARIA labels and semantic HTML
  - Skip-to-content link
  - Proper heading hierarchy
- Comprehensive documentation:
  - Architecture overview
  - Getting started guide
  - Quick reference
  - Contributing guidelines
  - API documentation
- Example site (quickstart) demonstrating features

[unreleased]: https://github.com/bengal-ssg/bengal/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bengal-ssg/bengal/releases/tag/v0.1.0

