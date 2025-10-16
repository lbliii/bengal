
---
title: "discovery.content_discovery"
type: python-module
source_file: "bengal/discovery/content_discovery.py"
css_class: api-content
description: "Content discovery - finds and organizes pages and sections."
---

# discovery.content_discovery

Content discovery - finds and organizes pages and sections.

---

## Classes

### `ContentDiscovery`


Discovers and organizes content files into pages and sections.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, content_dir: Path, site: Any | None = None) -> None
```

Initialize content discovery.



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
* - `content_dir`
  - `Path`
  - -
  - Root content directory
* - `site`
  - `Any | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `discover`
```python
def discover(self, use_cache: bool = False, cache: Any | None = None) -> tuple[list[Section], list[Page]]
```

Discover all content in the content directory.

Supports optional lazy loading with PageProxy for incremental builds.



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
* - `use_cache`
  - `bool`
  - `False`
  - Whether to use PageDiscoveryCache for lazy loading
* - `cache`
  - `Any | None`
  - `None`
  - PageDiscoveryCache instance (if use_cache=True)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple[list[Section], list[Page]]` - Tuple of (sections, pages)


```{note}
When use_cache=True and cache is provided: - Unchanged pages are returned as PageProxy (metadata only, lazy load on demand) - Changed pages are fully parsed and returned as normal Page objects - This saves disk I/O and parsing time for unchanged pages
```

```{note}
When use_cache=False (default): - All pages are fully discovered and parsed (current behavior) - Backward compatible - no changes to calling code needed
```




---


