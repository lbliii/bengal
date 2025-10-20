# Bengal SSG - Architecture Documentation

> **Note**: This architecture documentation has been reorganized into focused, manageable files in the `architecture/` directory for better maintainability and navigation.

## Quick Links

### Core Systems
- **[Overview](./architecture/overview.md)** - High-level architecture, diagrams, and cross-cutting concerns
- **[Object Model](./architecture/object-model.md)** - Site, Page, Section, Asset, Menu objects and relationships
- **[Cache System](./architecture/cache.md)** - Incremental builds, dependency tracking, inverted index pattern
- **[Rendering Pipeline](./architecture/rendering.md)** - Markdown parsing, templates, plugins, and output generation

### Content & Documentation
- **[Autodoc System](./architecture/autodoc.md)** - AST-based Python API documentation generation
- **[Discovery System](./architecture/discovery.md)** - Content and asset discovery processes

### Supporting Systems
- **[Fonts System](./architecture/fonts.md)** - Google Fonts self-hosting and CSS generation
- **[Configuration](./architecture/config.md)** - Configuration loading and management
- **[Post-Processing](./architecture/postprocess.md)** - Sitemap, RSS, link validation
- **[Development Server](./architecture/server.md)** - File watching, live reload, rebuild triggers
- **[Health Checks](./architecture/health.md)** - 14 validators for build quality assurance
- **[Analysis System](./architecture/analysis.md)** - Graph analysis, PageRank, community detection

### Interface & Tools
- **[CLI](./architecture/cli.md)** - Command-line interface structure and commands
- **[Utilities](./architecture/utils.md)** - Shared utility modules (text, dates, file I/O, pagination)

### Architecture Patterns
- **[Design Principles](./architecture/design-principles.md)** - Core architectural patterns and best practices
- **[Data Flow](./architecture/data-flow.md)** - Complete build pipeline visualization
- **[Performance](./architecture/performance.md)** - Performance characteristics, benchmarks, and optimizations
- **[File Organization](./architecture/file-organization.md)** - Directory structure and file management
- **[Extension Points](./architecture/extension-points.md)** - How to extend Bengal with custom functionality
- **[Testing](./architecture/testing.md)** - Testing strategy, coverage goals, and test infrastructure

## Key Features

### Core Capabilities
- **AST-based Python Autodoc**: Generate Python API documentation without importing code
- **Incremental Builds**: Faster rebuilds with intelligent caching (15-50x speedup)
- **Performance**: Parallel processing and optimizations (256 pages/sec on Python 3.14)
- **Rich Content Model**: Taxonomies, navigation, menus, and cascading metadata
- **Developer Experience**: Error messages, health checks, and file-watching dev server

### Build Performance (Python 3.14)
- **1,000 pages**: 3.90s full build (256 pps), ~0.5s incremental (~6x faster)
- **Parallel Processing**: 2-4x speedup on multi-core systems
- **Incremental Builds**: 15-50x faster for single-file changes

### Architecture Principles
1. **Modular Design**: Clear separation of concerns, no "God objects"
2. **Delegation Pattern**: Site delegates to specialized orchestrators
3. **Dependency Injection**: BuildContext for clean service passing
4. **Parallel-Friendly**: Thread-safe operations for concurrent processing
5. **Extensible**: Plugin architecture for custom parsers, validators, and post-processors

## Quick Start

For developers new to Bengal's codebase:

1. Start with **[Overview](./architecture/overview.md)** for the big picture
2. Read **[Object Model](./architecture/object-model.md)** to understand core data structures
3. Review **[Data Flow](./architecture/data-flow.md)** to see how builds work end-to-end
4. Dive into specific systems as needed based on your work

## Contributing

When working on Bengal:
- Follow the **[Design Principles](./architecture/design-principles.md)**
- Maintain test coverage per **[Testing](./architecture/testing.md)** guidelines
- Update relevant architecture docs when making significant changes
- Use **[Extension Points](./architecture/extension-points.md)** for custom functionality

## Documentation Maintenance

The architecture documentation is split into focused files for:
- **Easier navigation**: Find what you need quickly
- **Better maintainability**: Update specific systems without scrolling through 2700+ lines
- **Clearer organization**: Related content grouped together
- **Reduced cognitive load**: Digest documentation in manageable chunks

Last updated: 2025-10-19
