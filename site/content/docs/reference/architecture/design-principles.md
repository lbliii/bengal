---
title: Design Principles
nav_title: Principles
description: Core patterns and philosophies guiding Bengal's architecture.
weight: 50
category: core
tags:
- core
- design-principles
- architecture
- patterns
- best-practices
- performance
keywords:
- design principles
- architecture patterns
- best practices
- performance
- extensibility
---

# Design Principles

## North Star

Bengal exists to make free-threaded Python worth deploying for content tooling.
The architectural bias is simple: keep the stack pure Python, make parallelism
real, and keep performance measurable. A feature that makes documentation sites
more capable but pulls the build toward opaque toolchains, mutable shared state,
or hard-to-measure behavior is working against the project.

## Current Architecture Spine

- **Core holds state.** `bengal/core/` models describe sites, pages, sections,
  assets, metadata, registries, and cacheable facts. Core does not write files,
  log directly, or own rendering behavior.
- **Rendering derives presentation.** Markdown/parser behavior, HTML extraction,
  excerpts, meta descriptions, TOC structures, shortcode/link extraction, and
  template-ready URLs live under `bengal/rendering/`.
- **Page is a compatibility surface.** Template-facing Page properties remain
  stable for themes and plugins, but the work behind `content`, `html`,
  `plain_text`, `toc_items`, `excerpt`, `meta_description`, `href`, `_path`,
  `absolute_href`, `extract_links()`, and `HasShortcode()` delegates to
  rendering-side helpers.
- **Orchestration coordinates.** Discovery, build phases, rendering batches,
  provenance, cache policy, and output writing belong outside core.
- **Pipeline records stay immutable.** `SourcePage`, `ParsedPage`, and
  `RenderedPage` are records passed between phases. They are not convenience
  bags for late mutation.

## 1. Avoiding Stack Overflow
- **Iterative Traversal**: Section hierarchy uses `walk()` method instead of deep recursion
- **Configurable Limits**: Can set max recursion depth if needed
- **Tail Call Patterns**: Where recursion is used, structured for optimization

## 2. Avoiding God Objects
- **Single Responsibility**: Each class has one clear purpose
- **Composition over Inheritance**: Objects compose other objects rather than inheriting
- **Clear Dependencies**: Site → Sections → Pages (one direction)
- **Compatibility Shims, Not Behavior Sinks**: Domain objects can keep stable
  properties for callers, but extraction/rendering/URL work should live in the
  subsystem that owns that behavior.

## 3. Performance Optimization
- **Parallel Processing** (implemented):
  - Pages rendered in parallel using ThreadPoolExecutor
  - Assets processed in parallel for 5+ assets (2-4x speedup measured)
  - Post-processing: Sitemap, RSS, link validation run concurrently (2x speedup measured)
  - Smart thresholds avoid thread overhead for tiny workloads
  - Thread-safe error handling and output
  - Configurable via single `parallel` flag (default: true)
  - Configurable worker count (`max_workers`, default: auto-detect)
- **Incremental Builds** (implemented):
  - SHA256 file hashing for change detection
  - Dependency graph tracking (pages → templates/partials)
  - Template change detection (rebuilds only affected pages)
  - Granular taxonomy tracking (only rebuilds affected tag pages)
  - Verbose mode for debugging (`--verbose` flag)
  - 18-42x faster for single-file changes (measured on 10-100 page sites)
  - Automatic caching with Zstandard-compressed `.bengal/cache.json.zst` (92-93% smaller)
- **Caching**: Build cache persists between builds
- **Lazy Loading**: Parse content only when needed

## 4. Extensibility
- **Custom Content Types**: Multiple markdown parsers supported (Patitas default, Mistune legacy, python-markdown)
- **Template Flexibility**: Custom templates override defaults
- **Theme System**: Self-contained themes with templates and assets
- **Directives System**: Extensible MyST directives for custom markdown components
- **Plugin System**: 9 supported hook surfaces exposed through the plugin contract

## 5. Data Flow Principles

### Immutability Where Possible
- Pipeline records are immutable across `SourcePage → ParsedPage → RenderedPage`
- Cacheable page facts live in frozen `PageCore`
- Templates should behave like pure functions of context wherever possible

### Explicit State Management
- BuildContext carries shared state explicitly
- No hidden global state
- Clear data flow through pipeline phases

### Single Source of Truth
- Site is the root data container
- Cache stores paths, not object references
- References reconstructed each build

## 6. Error Handling

### Graceful Degradation
- Missing templates → fallback to defaults
- Invalid frontmatter → log warning, use defaults
- Broken links → report but continue build
- Cache corruption → load fresh cache

### User-Friendly Messages
- Rich tracebacks with context
- Specific error messages (not generic)
- Suggestions for common mistakes
- File and line number context

### Fail-Fast in Strict Mode
- Template errors stop build (strict mode)
- Validation failures stop build (strict mode)
- Development mode continues with warnings

## 7. Testing Strategy

### Comprehensive Coverage
- Unit tests for core utilities
- Integration tests for workflows
- Performance benchmarks
- Example sites as e2e tests

### Test Organization
- `tests/unit/` - Component tests
- `tests/integration/` - Workflow tests
- `tests/performance/` - Benchmarks
- `tests/roots/` - Fixture sites

### Continuous Validation
- Health check system validates builds
- Linter catches common issues
- Type checking with ty

## 8. Documentation

### Architecture Documentation
- Each subsystem has dedicated doc
- Design decisions explained
- Examples and diagrams
- Performance characteristics noted

### Code Documentation
- Docstrings for all public APIs
- Type hints throughout
- Complex logic has explanatory comments
- README files for complex subsystems

### User Documentation
- Getting started guide
- Command reference
- Configuration guide
- Architecture overview for contributors

## 9. Configuration Philosophy

### Convention Over Configuration
- Sensible defaults for everything
- Zero-config builds possible
- Progressive disclosure of complexity

### Explicit is Better Than Implicit
- No magic behavior
- Clear configuration keys
- Validation with helpful messages

### Flexible But Not Overwhelming
- Common use cases: minimal config
- Advanced use cases: full control
- Validation prevents mistakes

## 10. Build Philosophy

### Fast by Default
- Parallel processing enabled by default
- Incremental builds available
- Smart thresholds avoid overhead
- Python 3.14+ for optimal performance
- Free-threaded safety matters whenever shared rendering, cache, or effect state
  is introduced

### Predictable and Reproducible
- Same input → same output
- No hidden state between builds
- Atomic file operations
- Deterministic ordering

### Progressive Enhancement
- Basic builds work immediately
- Advanced features opt-in
- Graceful fallbacks
- No required external tools

## Core Architectural Patterns

### Delegation Pattern
```python
# Site delegates to orchestrators
class Site:
    def build(self):
        return BuildOrchestrator.build(self)

# Orchestrators delegate to specialized classes
class BuildOrchestrator:
    def build(site):
        ContentOrchestrator.discover(site)
        RenderOrchestrator.process(site)
        # ...
```

### Strategy Pattern
```python
# Content types use strategy pattern
class ContentStrategy(ABC):
    @abstractmethod
    def get_template(self, page): pass

class BlogStrategy(ContentStrategy):
    def get_template(self, page):
        return 'blog/post.html'
```

### Registry Pattern
```python
# Template functions and content types use registry
class ContentTypeRegistry:
    _strategies = {}

    @classmethod
    def register(cls, name, strategy):
        cls._strategies[name] = strategy
```

### Builder Pattern
```python
# MenuBuilder constructs complex menu hierarchies
builder = MenuBuilder('main')
builder.add_from_config(items)
builder.add_from_pages(pages)
menu = builder.build_hierarchy()
```

### Factory Pattern
```python
# Parser factory creates appropriate parser
def create_markdown_parser(engine='patitas'):
    if engine == 'patitas':
        return PatitasParser()  # Default: thread-safe, O(n)
    elif engine == 'mistune':
        return MistuneParser()  # Legacy option
    elif engine == 'python-markdown':
        return PythonMarkdownParser()
```

## Performance Design Principles

### Measure, Don't Guess
- Comprehensive benchmarks
- Real-world test sites
- Profile builds regularly
- Document performance characteristics

### Optimize Hot Paths
- Markdown parsing (40-50% of build time)
- Template rendering (30-40% of build time)
- File I/O (10-20% of build time)
- Other operations (<10% of build time)

### Parallel Where Beneficial
- Pages: Parallel above 5 pages
- Assets: Parallel above 5 assets
- Post-processing: Always parallel
- Discovery: Parallel for large sites

### Cache Aggressively
- Parsed markdown AST
- Template bytecode
- File hashes
- Taxonomy indexes

## Future-Proofing

### Designed for Extension
- Plugin system planned
- Hook points identified
- Minimal breaking changes
- Deprecation warnings

### Performance Headroom
- Python 3.14 JIT: 24% faster
- Python 3.14t free-threading: 81% faster
- Further optimization possible
- Architecture supports distributed builds

### Clean Interfaces
- Stable public APIs
- Clear module boundaries
- Minimal coupling
- Easy to refactor internals

## Related Documentation

- [Architecture Overview](./) - High-level architecture
- [Orchestration](core/orchestration.md) - Build coordination
- [Performance](../../../building/performance/) - Benchmarks and hot paths
- [Testing](meta/testing.md) - Test strategy
