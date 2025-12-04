# AI-Friendly Docstring Standards for Bengal

## Purpose

This document defines standards for writing docstrings and comments that maximize value for AI assistants reading and understanding the codebase. These standards complement Python's PEP 257 and focus on providing context, relationships, and rationale that help AI assistants make better decisions.

## Core Principles

### 1. Context Over Description
- **Don't just describe WHAT** - Explain WHY and HOW it fits into the system
- **Include relationships** - Reference related modules, classes, or functions
- **Document decisions** - Explain non-obvious implementation choices
- **Provide examples** - Show usage patterns, especially for complex APIs

### 2. Structure for Scannability
- **Module docstrings**: Purpose, key concepts, related modules
- **Class docstrings**: Purpose, creation patterns, key attributes, relationships
- **Function docstrings**: Purpose, parameters, returns, exceptions, examples, related functions

### 3. AI-Optimized Information
- **Type information**: Complement type hints with semantic meaning
- **Edge cases**: Document what happens in edge cases
- **Performance notes**: Mention performance characteristics when relevant
- **Threading/concurrency**: Document thread-safety and concurrency patterns
- **Caching behavior**: Explain cache invalidation and lifecycle

## Docstring Format

### Module-Level Docstrings

```python
"""
[One-line purpose statement]

[2-3 sentence overview of the module's role in the system]

Key Concepts:
    - Concept 1: Brief explanation
    - Concept 2: Brief explanation

Related Modules:
    - bengal.module.related: What it provides/uses
    - bengal.module.other: Relationship

See Also:
    - plan/active/rfc-name.md: Related RFC or design doc
    - bengal/other/module.py: Related implementation
"""
```

**Example**:
```python
"""
Template engine using Jinja2.

Provides template rendering, template function registration, and optional
template profiling for performance analysis. Integrates with theme system
for template discovery and asset manifest for cache-busting.

Key Concepts:
    - Template inheritance: Child themes inherit parent templates
    - Bytecode caching: Compiled templates cached for faster subsequent renders
    - Template profiling: Optional timing data collection via --profile-templates

Related Modules:
    - bengal.rendering.template_profiler: Profiling implementation
    - bengal.rendering.template_functions: Template function registry
    - bengal.utils.theme_registry: Theme resolution and discovery

See Also:
    - plan/active/rfc-template-performance-optimization.md: Performance RFC
"""
```

### Class Docstrings

```python
"""
[One-line purpose statement]

[2-3 sentence overview of the class's role]

Creation:
    Recommended: ClassName.from_config(...)
        - When to use this pattern
        - What it handles automatically

    Direct instantiation: ClassName(...)
        - When to use this pattern
        - What you must handle manually

Attributes:
    attr1: Purpose and type (if not obvious from type hint)
    attr2: Purpose, when it's set, lifecycle

Relationships:
    - Uses: OtherClass for X
    - Used by: ConsumerClass for Y
    - Extends: BaseClass (if applicable)

Thread Safety:
    [If relevant: thread-safe, not thread-safe, requires external locking]

Examples:
    # Common usage pattern
    obj = ClassName.from_config(path)

    # Advanced usage
    obj = ClassName(param1=value, param2=value)
"""
```

**Example**:
```python
"""
Represents the entire website and orchestrates the build process.

The Site object is the central container for all content (pages, sections,
assets) and coordinates discovery, rendering, and output generation. It
maintains caches for expensive operations and provides query interfaces
for templates.

Creation:
    Recommended: Site.from_config(root_path)
        - Loads configuration from bengal.toml
        - Applies all settings automatically
        - Use for production builds and CLI

    Direct instantiation: Site(root_path=path, config=config)
        - For unit testing with controlled state
        - For programmatic config manipulation
        - Advanced use case only

Attributes:
    root_path: Root directory of the site (immutable after init)
    pages: All pages in the site (populated during discovery)
    sections: All sections in the site (populated during discovery)
    _regular_pages_cache: Cached filtered pages (invalidated when pages change)

Relationships:
    - Uses: Page, Section, Asset for content representation
    - Uses: Theme for template/asset resolution
    - Used by: BuildOrchestrator for build coordination
    - Used by: RenderingPipeline for page rendering

Thread Safety:
    Not thread-safe. Site objects should not be shared across threads.
    Each thread should have its own Site instance or use proper locking.

Examples:
    # Production/CLI (recommended):
    site = Site.from_config(Path('/path/to/site'))

    # Unit testing:
    site = Site(root_path=Path('/test'), config={})
    site.pages = [test_page1, test_page2]
"""
```

### Function/Method Docstrings

```python
"""
[One-line purpose statement]

[Optional: 1-2 sentence context about when/why to use this function]

Args:
    param1: Description including type semantics, defaults, edge cases
    param2: Description including when None is valid, etc.

Returns:
    Description including type semantics, what None means, etc.

Raises:
    ExceptionType: When and why this exception is raised

Performance:
    [If relevant: O(n) complexity, caching behavior, etc.]

Thread Safety:
    [If relevant: thread-safe, requires locking, etc.]

Examples:
    >>> # Simple usage
    >>> result = function(param1, param2)
    >>>
    >>> # Advanced usage with edge case
    >>> result = function(param1=None)  # Handles None case

See Also:
    - related_function(): Related function for X
    - bengal.module.other: Related module
"""
```

**Example**:
```python
"""
Check if a page is autodoc-generated.

Consolidates detection logic used across multiple validators and analysis
tools. Uses multiple signals (frontmatter, content, path) for reliable
detection even when some metadata is missing.

Args:
    page: Page object to check. Can be a Page, PageProxy, or any object
          with metadata/frontmatter and content attributes. Handles both
          'metadata' and 'frontmatter' attribute names.

Returns:
    True if page is autodoc-generated based on any detection signal.
    False if no autodoc indicators are found.

Performance:
    O(1) - Simple attribute checks and string containment tests.

Examples:
    >>> from bengal.utils.autodoc import is_autodoc_page
    >>> if is_autodoc_page(page):
    ...     # Skip autodoc pages in analysis
    ...     continue

See Also:
    - bengal.postprocess.output_formats.index_generator: Uses for search indexing
    - bengal.analysis.knowledge_graph: Uses for graph filtering
    - plan/active/rfc-code-quality-improvements.md: Consolidation RFC
"""
```

## Comment Standards

### Inline Comments

**Good inline comments explain WHY, not WHAT**:

```python
# Good: Explains decision/rationale
# Use pickle instead of JSON for performance with sets/complex structures
cache_data = pickle.dumps(cache)

# Good: Explains non-obvious behavior
# Thread-local storage: reuse pipelines per thread, not per page
_thread_local = threading.local()

# Bad: States the obvious
# Increment i by 1
i += 1

# Bad: Should be in docstring
# This function processes pages
def process_pages():
```

### TODO/FIXME/NOTE Comments

**Format for TODOs**:
```python
# TODO(scope): Description of what needs to be done
# TODO(cache): Add cache invalidation when config changes
# TODO(perf): Optimize O(n²) lookup to O(n) with hash map
```

**Format for FIXMEs**:
```python
# FIXME(issue): Description of bug/workaround
# FIXME(threading): Race condition possible here, needs locking
```

**Format for NOTES**:
```python
# NOTE: Important implementation detail or decision rationale
# NOTE: We check this even on full builds to populate the cache
```

**Cleanup Rules**:
- **Remove outdated TODOs** - If task is done or no longer relevant
- **Convert TODOs to issues** - If they represent real work items
- **Improve vague NOTES** - Add context about why the note matters
- **Resolve FIXMEs** - Fix the issue or document why it can't be fixed

## Cross-Reference Patterns

### File References
```python
# See: bengal/core/site.py:Site class for site container
# See: bengal/orchestration/build.py:BuildOrchestrator for build coordination
```

### RFC/Plan References
```python
# See: plan/active/rfc-name.md for design rationale
# See: plan/completed/feature-name.md for implementation history
```

### Related Code References
```python
# Related: bengal/utils/autodoc.py:is_autodoc_page() for detection logic
# Related: bengal/cache/build_cache.py:BuildCache for cache structure
```

## Examples of Improvements

### Before (Minimal)
```python
def process_pages(pages):
    """Process pages."""
    for page in pages:
        render(page)
```

### After (AI-Friendly)
```python
def process_pages(pages: list[Page]) -> None:
    """
    Process and render all pages in the provided list.

    Iterates through pages and renders each one. Pages are processed
    in order, which matters for dependency tracking and incremental builds.

    Args:
        pages: List of Page objects to render. Empty list is valid (no-op).

    Performance:
        O(n) where n is number of pages. Each page render is independent.

    See Also:
        - bengal.orchestration.render:render_page(): Individual page rendering
        - bengal.orchestration.incremental:IncrementalBuilder: For incremental processing
    """
    for page in pages:
        render(page)
```

## Implementation Plan

1. **Audit existing docstrings** - Categorize as good/poor/missing
2. **Create standards document** (this document)
3. **Improve module docstrings** - Add context and cross-references
4. **Improve class docstrings** - Add creation patterns and relationships
5. **Improve function docstrings** - Add context, examples, cross-references
6. **Clean up comments** - Remove outdated, improve inline comments
7. **Standardize TODO/FIXME** - Format consistently or resolve

## Success Criteria

✅ **AI assistants can**:
- Understand module purpose and relationships without reading implementation
- Know when to use which creation pattern for classes
- Understand function behavior, edge cases, and performance characteristics
- Find related code through cross-references
- Understand non-obvious implementation decisions

✅ **Code is**:
- Self-documenting through clear docstrings
- Cross-referenced for easy navigation
- Free of outdated comments
- Consistent in documentation style
