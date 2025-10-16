
---
title: "orchestration.incremental"
type: python-module
source_file: "bengal/orchestration/incremental.py"
css_class: api-content
description: "Incremental build orchestration for Bengal SSG.  Handles cache management, change detection, and determining what needs rebuilding."
---

# orchestration.incremental

Incremental build orchestration for Bengal SSG.

Handles cache management, change detection, and determining what needs rebuilding.

---

## Classes

### `IncrementalOrchestrator`


Handles incremental build logic.

Responsibilities:
    - Cache initialization and management
    - Change detection (content, assets, templates)
    - Dependency tracking
    - Taxonomy change detection
    - Determining what needs rebuilding




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize incremental orchestrator.



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
* - `self`
  - -
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - Site instance for incremental builds
:::

::::




---
#### `initialize`
```python
def initialize(self, enabled: bool = False) -> tuple['BuildCache', 'DependencyTracker']
```

Initialize cache and tracker.



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
* - `self`
  - -
  - -
  - -
* - `enabled`
  - `bool`
  - `False`
  - Whether incremental builds are enabled
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple['BuildCache', 'DependencyTracker']` - Tuple of (cache, tracker)




---
#### `check_config_changed`
```python
def check_config_changed(self) -> bool
```

Check if config file has changed (requires full rebuild).



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

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if config changed




---
#### `find_work_early`
```python
def find_work_early(self, verbose: bool = False) -> tuple[list['Page'], list['Asset'], dict[str, list]]
```

Find pages/assets that need rebuilding (early version - before taxonomy generation).

This is called BEFORE taxonomies/menus are generated, so it only checks content/asset changes.
Generated pages (tags, etc.) will be determined later based on affected tags.



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
* - `self`
  - -
  - -
  - -
* - `verbose`
  - `bool`
  - `False`
  - Whether to collect detailed change information
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple[list['Page'], list['Asset'], dict[str, list]]` - Tuple of (pages_to_build, assets_to_process, change_summary)




---
#### `find_work`
```python
def find_work(self, verbose: bool = False) -> tuple[list['Page'], list['Asset'], dict[str, list]]
```

Find pages/assets that need rebuilding (legacy version - after taxonomy generation).

This is the old method that expects generated pages to already exist.
Kept for backward compatibility but should be replaced with find_work_early().



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
* - `self`
  - -
  - -
  - -
* - `verbose`
  - `bool`
  - `False`
  - Whether to collect detailed change information
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`tuple[list['Page'], list['Asset'], dict[str, list]]` - Tuple of (pages_to_build, assets_to_process, change_summary)




---
#### `process`
```python
def process(self, change_type: str, changed_paths: set) -> None
```

Bridge-style process for testing incremental invalidation.

⚠️  TEST BRIDGE ONLY
========================
This method is a lightweight adapter used in tests to simulate an
incremental pass without invoking the entire site build orchestrator.

**Not for production use:**
- Writes placeholder output ("Updated") for verification only
- Does not perform full rendering or asset processing
- Skips postprocessing (RSS, sitemap, etc.)
- Use run() or full_build() for production builds

**Primarily consumed by:**
- tests/integration/test_full_to_incremental_sequence.py
- bengal/orchestration/full_to_incremental.py (test bridge helper)
- Test scenarios validating cache invalidation logic



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
* - `change_type`
  - `str`
  - -
  - One of "content", "template", or "config"
* - `changed_paths`
  - `set`
  - -
  - Set of paths that changed (ignored for "config")
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`RuntimeError`**: If tracker not initialized (call initialize() first)



---
#### `full_rebuild`
```python
def full_rebuild(self, pages: list, context: BuildContext)
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
* - `pages`
  - `list`
  - -
  - -
* - `context`
  - `BuildContext`
  - -
  - -
:::

::::




---
#### `save_cache`
```python
def save_cache(self, pages_built: list['Page'], assets_processed: list['Asset']) -> None
```

Update cache with processed files.



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
* - `pages_built`
  - `list['Page']`
  - -
  - Pages that were built
* - `assets_processed`
  - `list['Asset']`
  - -
  - Assets that were processed
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
