
---
title: "orchestration.content"
type: python-module
source_file: "bengal/orchestration/content.py"
css_class: api-content
description: "Content discovery and setup orchestration for Bengal SSG.  Handles content and asset discovery, page/section reference setup, and cascading frontmatter."
---

# orchestration.content

Content discovery and setup orchestration for Bengal SSG.

Handles content and asset discovery, page/section reference setup,
and cascading frontmatter.

---

## Classes

### `ContentOrchestrator`


Handles content and asset discovery.

Responsibilities:
    - Discover content (pages and sections)
    - Discover assets (site and theme)
    - Set up page/section references for navigation
    - Apply cascading frontmatter from sections to pages




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize content orchestrator.



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
  - Site instance to populate with content
:::

::::




---
#### `discover`
```python
def discover(self, incremental: bool = False, cache: Any | None = None) -> None
```

Discover all content and assets.

Main entry point called during build.



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
* - `incremental`
  - `bool`
  - `False`
  - Whether this is an incremental build (enables lazy loading)
* - `cache`
  - `Any | None`
  - `None`
  - PageDiscoveryCache instance (required if incremental=True)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `discover_content`
```python
def discover_content(self, content_dir: Path | None = None, incremental: bool = False, cache: Any | None = None) -> None
```

Discover all content (pages, sections) in the content directory.

Supports optional lazy loading with PageProxy for incremental builds.



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
* - `content_dir`
  - `Path | None`
  - `None`
  - Content directory path (defaults to root_path/content)
* - `incremental`
  - `bool`
  - `False`
  - Whether this is an incremental build (enables lazy loading)
* - `cache`
  - `Any | None`
  - `None`
  - PageDiscoveryCache instance (required if incremental=True)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `discover_assets`
```python
def discover_assets(self, assets_dir: Path | None = None) -> None
```

Discover all assets in the assets directory and theme assets.



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
* - `assets_dir`
  - `Path | None`
  - `None`
  - Assets directory path (defaults to root_path/assets)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


