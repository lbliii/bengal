
---
title: "orchestration.postprocess"
type: python-module
source_file: "bengal/orchestration/postprocess.py"
css_class: api-content
description: "Post-processing orchestration for Bengal SSG.  Handles post-build tasks like sitemap generation, RSS feeds, and link validation."
---

# orchestration.postprocess

Post-processing orchestration for Bengal SSG.

Handles post-build tasks like sitemap generation, RSS feeds, and link validation.

---

## Classes

### `PostprocessOrchestrator`


Handles post-processing tasks.

Responsibilities:
    - Sitemap generation
    - RSS feed generation
    - Link validation
    - Parallel/sequential execution of tasks




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize postprocess orchestrator.



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
  - Site instance with rendered pages and configuration
:::

::::




---
#### `run`
```python
def run(self, parallel: bool = True, progress_manager = None, build_context = None, incremental: bool = False) -> None
```

Perform post-processing tasks (sitemap, RSS, output formats, link validation, etc.).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 5 parameters (click to expand)
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
* - `parallel`
  - `bool`
  - `True`
  - Whether to run tasks in parallel
* - `progress_manager`
  - -
  - `None`
  - Live progress manager (optional)
* - `build_context`
  - -
  - `None`
  - -
* - `incremental`
  - `bool`
  - `False`
  - Whether this is an incremental build (can skip some tasks)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


