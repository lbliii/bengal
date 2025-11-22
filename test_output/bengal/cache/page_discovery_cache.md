# page_discovery_cache

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cache/page_discovery_cache.py

Page Discovery Cache for incremental builds.

Caches page metadata (title, date, tags, section, slug) to enable lazy loading
of full page content. This allows incremental builds to skip discovery of
unchanged pages and only load full content when needed.

Architecture:
- Metadata: source_path → PageMetadata (minimal data needed for navigation/filtering)
- Lazy Loading: Full content loaded on first access via PageProxy
- Storage: .bengal/page_metadata.json (compact format)
- Validation: Hash-based validation to detect stale cache entries

Performance Impact:
- Full page discovery skipped for unchanged pages (~80ms saved per 100 pages)
- Lazy loading ensures correctness (full content available when needed)
- Incremental builds only load changed pages fresh

*Note: Template has undefined variables. This is fallback content.*
