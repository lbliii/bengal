# Changelog

All notable changes to Bengal SSG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Incremental build system
- Plugin architecture with hooks
- Performance benchmarks
- Comprehensive documentation site

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

