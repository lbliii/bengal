---
title: "directives.cache"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/cache.py"
---

# directives.cache

Directive content caching for performance optimization.

Caches parsed directive content by content hash to avoid expensive
re-parsing of identical directive blocks.

**Source:** `../../bengal/rendering/plugins/directives/cache.py`

---

## Classes

### DirectiveCache


LRU cache for parsed directive content.

Uses content hash to detect changes and reuse parsed AST.
Implements LRU eviction to limit memory usage.

Expected impact: 30-50% speedup on pages with repeated directive patterns.




**Methods:**

#### __init__

```python
def __init__(self, max_size: int = 1000)
```

Initialize directive cache.

**Parameters:**

- **self**
- **max_size** (`int`) = `1000` - Maximum number of cached items (default 1000)







---
#### get

```python
def get(self, directive_type: str, content: str) -> Optional[Any]
```

Get cached parsed content.

**Parameters:**

- **self**
- **directive_type** (`str`) - Type of directive
- **content** (`str`) - Directive content

**Returns:** `Optional[Any]` - Cached parsed result or None if not found






---
#### put

```python
def put(self, directive_type: str, content: str, parsed: Any) -> None
```

Cache parsed content.

**Parameters:**

- **self**
- **directive_type** (`str`) - Type of directive
- **content** (`str`) - Directive content
- **parsed** (`Any`) - Parsed result to cache

**Returns:** `None`






---
#### clear

```python
def clear(self) -> None
```

Clear the cache.

**Parameters:**

- **self**

**Returns:** `None`






---
#### enable

```python
def enable(self) -> None
```

Enable caching.

**Parameters:**

- **self**

**Returns:** `None`






---
#### disable

```python
def disable(self) -> None
```

Disable caching.

**Parameters:**

- **self**

**Returns:** `None`






---
#### stats

```python
def stats(self) -> Dict[str, Any]
```

Get cache statistics.

**Parameters:**

- **self**

**Returns:** `Dict[str, Any]` - Dictionary with cache statistics:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - hit_rate: Cache hit rate (0.0 to 1.0)
    - size: Current cache size
    - max_size: Maximum cache size
    - enabled: Whether caching is enabled






---
#### reset_stats

```python
def reset_stats(self) -> None
```

Reset hit/miss statistics without clearing cache.

**Parameters:**

- **self**

**Returns:** `None`






---
#### __repr__

```python
def __repr__(self) -> str
```

String representation.

**Parameters:**

- **self**

**Returns:** `str`






---


## Functions

### get_cache

```python
def get_cache() -> DirectiveCache
```

Get the global directive cache instance.


**Returns:** `DirectiveCache` - Global DirectiveCache instance





---
### configure_cache

```python
def configure_cache(max_size: Optional[int] = None, enabled: Optional[bool] = None) -> None
```

Configure the global directive cache.

**Parameters:**

- **max_size** (`Optional[int]`) = `None` - Maximum cache size (None to keep current)
- **enabled** (`Optional[bool]`) = `None` - Whether to enable caching (None to keep current)

**Returns:** `None`





---
### clear_cache

```python
def clear_cache() -> None
```

Clear the global directive cache.


**Returns:** `None`





---
### get_cache_stats

```python
def get_cache_stats() -> Dict[str, Any]
```

Get statistics from the global directive cache.


**Returns:** `Dict[str, Any]` - Cache statistics dictionary





---
