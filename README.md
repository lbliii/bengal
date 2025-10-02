# Bengal SSG

A high-performance static site generator designed to outperform Hugo, Sphinx, and MkDocs through modular architecture, speed, and maintainability.

## Features

- **Lightning Fast**: Incremental builds and parallel processing
- **Modular Architecture**: Clean separation of Site, Page, Section, and Asset components
- **Template System**: Powerful templates with nested partials and shortcodes
- **Plugin System**: Extensible hooks for pre/post build customization
- **Asset Pipeline**: Built-in optimization, minification, and fingerprinting
- **SEO Optimized**: Sitemap, RSS feeds, link validation, and canonical URLs
- **Versioned Content**: Support for multiple versions of documentation
- **Developer Friendly**: Hot reload dev server and comprehensive debugging tools

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

# Start development server with hot reload
bengal serve
```

## Architecture

Bengal follows a modular design with clear separation of concerns:

- **Site Object**: Orchestrates the entire build process
- **Page Object**: Represents individual content pages with metadata and rendering
- **Section Object**: Manages content hierarchy and grouping
- **Asset Object**: Handles static files with optimization and versioning
- **Rendering Pipeline**: Parse → Build AST → Apply Templates → Render → Post-process

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

## Development Status

Bengal SSG is under active development. Current roadmap:

- [x] Core object model
- [x] Basic rendering pipeline
- [x] CLI foundation
- [ ] Incremental builds
- [ ] Plugin system
- [ ] Asset pipeline
- [ ] SEO features
- [ ] Hot reload server

## License

MIT License

