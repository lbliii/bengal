# Bengal - Product Overview

Bengal is a high-performance static site generator (SSG) built in Python with a focus on developer experience and build speed.

## Core Features

- **Markdown-based content** with YAML front matter
- **Incremental builds** with intelligent dependency tracking (18-42x faster rebuilds)
- **Parallel processing** using ThreadPoolExecutor for maximum performance
- **Jinja2 templating** with rich template functions and filters
- **AST-based autodoc** generation for Python APIs and CLI tools
- **Development server** with file watching and live reload
- **SEO optimization** with automatic sitemap and RSS generation
- **Theme system** with inheritance and customization
- **Health validation** system for build quality assurance

## Target Use Cases

- **Documentation sites** - Technical docs with API generation
- **Blogs** - Personal and professional writing platforms
- **Portfolio sites** - Showcase work and projects
- **Business sites** - Company and product websites
- **Resume sites** - Professional CV presentations

## Performance Focus

Bengal is optimized for Python 3.14+ with free-threading support, delivering up to 1.8x faster rendering. The incremental build system with dependency tracking makes it suitable for large sites while maintaining fast development cycles.

## Architecture Philosophy

Modular design with clear separation of concerns, avoiding "God objects" while maintaining high performance. Uses dependency injection through BuildContext and standardized interfaces for extensibility.
