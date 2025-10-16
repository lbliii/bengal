
---
title: "rendering.pygments_cache"
type: python-module
source_file: "bengal/rendering/pygments_cache.py"
css_class: api-content
description: "Pygments lexer caching to dramatically improve syntax highlighting performance.  Problem: pygments.lexers.guess_lexer() triggers expensive plugin discovery via importlib.metadata on EVERY code bloc..."
---

# rendering.pygments_cache

Pygments lexer caching to dramatically improve syntax highlighting performance.

Problem: pygments.lexers.guess_lexer() triggers expensive plugin discovery
via importlib.metadata on EVERY code block, causing 60+ seconds overhead
on large sites with many code blocks.

Solution: Cache lexers by language name to avoid repeated plugin discovery.

Performance Impact (measured on 826-page site):
- Before: 86s (73% in Pygments plugin discovery)
- After: ~29s (3× faster)

---

## Classes

### `PygmentsPatch`


Monkey-patch adapter for Pygments used in tests.

Provides a context manager and static methods to apply/restore a
patch that routes markdown.codehilite lookups through our cached
helpers, without changing public APIs.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__enter__`
```python
def __enter__(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::




---
#### `__exit__`
```python
def __exit__(self, exc_type, tb)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `exc_type`
  - -
  - -
  - -
* - `tb`
  - -
  - -
  - -
:::

::::




---
#### `apply` @classmethod
```python
def apply(cls) -> bool
```

Apply monkey patches; idempotent. Returns True if applied.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `restore` @classmethod
```python
def restore(cls) -> bool
```

Restore original functions; returns True if restoration occurred.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---
#### `is_patched` @classmethod
```python
def is_patched(cls) -> bool
```

Return current patch state.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `cls`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool`




---


## Functions

### `get_lexer_cached`
```python
def get_lexer_cached(language: str | None = None, code: str = '') -> any
```

Get a Pygments lexer with aggressive caching.

Strategy:
1. If language specified: cache by language name (fast path)
2. If no language: hash code sample and cache guess result
3. Fallback: return text lexer if all else fails



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `language`
  - `str | None`
  - `None`
  - Optional language name (e.g., 'python', 'javascript')
* - `code`
  - `str`
  - `''`
  - Code content (used for guessing if language not specified)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`any` - Pygments lexer instance

Performance:
    - Cached lookup: ~0.001ms
    - Uncached lookup: ~30ms (plugin discovery)
    - Cache hit rate: >95% after first few pages




---
### `clear_cache`
```python
def clear_cache()
```

Clear the lexer cache. Useful for testing or memory management.







---
### `get_cache_stats`
```python
def get_cache_stats() -> dict
```

Get cache statistics for monitoring.



:::{rubric} Returns
:class: rubric-returns
:::
`dict` - Dict with hits, misses, guess_calls, hit_rate




---
### `log_cache_stats`
```python
def log_cache_stats()
```

Log cache statistics. Call at end of build for visibility.







---
