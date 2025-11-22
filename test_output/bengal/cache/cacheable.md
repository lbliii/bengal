# cacheable

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/cache/cacheable.py

Cacheable Protocol - Type-safe cache contracts for Bengal.

This module defines a Protocol that cacheable types can implement to ensure
type-safe serialization and deserialization. Any type that needs to be cached
to disk should implement this protocol.

The protocol enforces:
- Consistent serialization pattern (to_cache_dict/from_cache_dict)
- Type-safe round-trip (obj == T.from_cache_dict(obj.to_cache_dict()))
- JSON-compatible serialization (str, int, float, bool, None, list, dict)
- Compile-time validation via mypy

Design Philosophy:
    Unlike PageCore (which solves the live/cache/proxy split problem), the
    Cacheable protocol provides a lightweight contract for ANY type that needs
    caching, without requiring inheritance or base classes.

    Use Cacheable when:
    - Type needs to be persisted to disk (cache files, indexes)
    - Type should be serialized consistently across codebase
    - Type-safety for serialization is desired
    - No three-way split (live/cache/proxy) exists

    Use *Core base class (like PageCore) when:
    - Type has three-way split (Live → Cache → Proxy)
    - Templates access many properties (lazy loading matters)
    - Manual sync between representations causes bugs

See Also:
    - bengal/cache/cache_store.py - Generic cache helper using this protocol
    - bengal/core/page/page_core.py - PageCore (uses protocol)
    - bengal/cache/taxonomy_index.py - TagEntry (uses protocol)
    - architecture/cache.md - Cache architecture documentation
    - plan/active/rfc-cacheable-protocol.md - Design rationale

*Note: Template has undefined variables. This is fallback content.*
