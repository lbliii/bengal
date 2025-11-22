# query_index

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cache/query_index.py

Query Index - Base class for queryable indexes.

Provides O(1) lookups for common page queries by pre-computing indexes
at build time. Similar to TaxonomyIndex but generalized for any page attribute.

Architecture:
- Build indexes once during build phase (O(n) cost)
- Persist to disk for incremental builds
- Template access is O(1) hash lookup
- Incrementally update only changed pages

Example:
    # Built-in indexes
    site.indexes.section.get('blog')        # O(1) - all blog posts
    site.indexes.author.get('Jane Smith')   # O(1) - posts by Jane

    # Custom indexes
    site.indexes.status.get('published')    # O(1) - published posts

*Note: Template has undefined variables. This is fallback content.*
