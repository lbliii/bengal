
---
title: "directives.cache"
type: python-module
source_file: "bengal/rendering/plugins/directives/cache.py"
css_class: api-content
description: "Directive content caching for performance optimization.  Caches parsed directive content by content hash to avoid expensive re-parsing of identical directive blocks."
---

# directives.cache

Directive content caching for performance optimization.

Caches parsed directive content by content hash to avoid expensive
re-parsing of identical directive blocks.

---

## Classes

### `DirectiveCache`


LRU cache for parsed directive content.

Uses content hash to detect changes and reuse parsed AST.
Implements LRU eviction to limit memory usage.

Expected impact: 30-50% speedup on pages with repeated directive patterns.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, max_size: int = 1000)
```

Initialize directive cache.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`max_size`** (`int`) = `1000` - Maximum number of cached items (default 1000)





---
#### `get`
```python
def get(self, directive_type: str, content: str) -> Any | None
```

Get cached parsed content.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`directive_type`** (`str`) - Type of directive
- **`content`** (`str`) - Directive content

:::{rubric} Returns
:class: rubric-returns
:::
`Any | None` - Cached parsed result or None if not found




---
#### `put`
```python
def put(self, directive_type: str, content: str, parsed: Any) -> None
```

Cache parsed content.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`directive_type`** (`str`) - Type of directive
- **`content`** (`str`) - Directive content
- **`parsed`** (`Any`) - Parsed result to cache

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `clear`
```python
def clear(self) -> None
```

Clear the cache.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `enable`
```python
def enable(self) -> None
```

Enable caching.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `disable`
```python
def disable(self) -> None
```

Disable caching.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `stats`
```python
def stats(self) -> dict[str, Any]
```

Get cache statistics.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Dictionary with cache statistics:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - hit_rate: Cache hit rate (0.0 to 1.0)
    - size: Current cache size
    - max_size: Maximum cache size
    - enabled: Whether caching is enabled




---
#### `reset_stats`
```python
def reset_stats(self) -> None
```

Reset hit/miss statistics without clearing cache.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `__repr__`
```python
def __repr__(self) -> str
```

String representation.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---


## Functions

### `get_cache`
```python
def get_cache() -> DirectiveCache
```

Get the global directive cache instance.



:::{rubric} Returns
:class: rubric-returns
:::
`DirectiveCache` - Global DirectiveCache instance




---
### `configure_cache`
```python
def configure_cache(max_size: int | None = None, enabled: bool | None = None) -> None
```

Configure the global directive cache.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`max_size`** (`int | None`) = `None` - Maximum cache size (None to keep current)
- **`enabled`** (`bool | None`) = `None` - Whether to enable caching (None to keep current)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `clear_cache`
```python
def clear_cache() -> None
```

Clear the global directive cache.



:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `get_cache_stats`
```python
def get_cache_stats() -> dict[str, Any]
```

Get statistics from the global directive cache.



:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Cache statistics dictionary




---
