
---
title: "server.build_handler"
type: python-module
source_file: "bengal/server/build_handler.py"
css_class: api-content
description: "File system event handler for automatic site rebuilds.  Watches for file changes and triggers incremental rebuilds with debouncing."
---

# server.build_handler

File system event handler for automatic site rebuilds.

Watches for file changes and triggers incremental rebuilds with debouncing.

---

## Classes

### `BuildHandler`

**Inherits from:** `FileSystemEventHandler`
File system event handler that triggers site rebuild with debouncing.

Watches for file changes and automatically rebuilds the site when changes
are detected. Uses debouncing to batch multiple rapid changes into a single
rebuild, preventing excessive rebuilds when multiple files are saved at once.

Features:
- Debounced rebuilds (0.2s delay to batch changes)
- Incremental builds for speed (5-10x faster)
- Parallel rendering
- Stale object reference prevention (clears ephemeral state)
- Build error recovery (errors don't crash server)
- Automatic cache invalidation for config/template changes

Ignored files:
- Output directory (public/)
- Build logs (.bengal-build.log)
- Cache files (.bengal-cache.json)
- Temp files (.tmp, ~, .swp, .swo)
- System files (.DS_Store, .git)
- Python cache (__pycache__, .pyc)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any, host: str = 'localhost', port: int = 5173) -> None
```

Initialize the build handler.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
  - `Any`
  - -
  - Site instance
* - `host`
  - `str`
  - `'localhost'`
  - Server host
* - `port`
  - `int`
  - `5173`
  - Server port
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `on_modified`
```python
def on_modified(self, event: FileSystemEvent) -> None
```

Handle file modification events with debouncing.

Multiple rapid file changes are batched together and trigger a single
rebuild after a short delay (DEBOUNCE_DELAY seconds).

Files in the output directory and matching ignore patterns are skipped
to prevent infinite rebuild loops.



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
* - `event`
  - `FileSystemEvent`
  - -
  - File system event
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`


```{note}
This method implements debouncing by canceling the previous timer and starting a new one on each file change.
```




---
