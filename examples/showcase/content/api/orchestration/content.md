
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
- **`self`**
- **`site`** (`'Site'`) - Site instance to populate with content





---
#### `discover`
```python
def discover(self) -> None
```

Discover all content and assets.
Main entry point called during build.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `discover_content`
```python
def discover_content(self, content_dir: Path | None = None) -> None
```

Discover all content (pages, sections) in the content directory.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content_dir`** (`Path | None`) = `None` - Content directory path (defaults to root_path/content)

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
- **`self`**
- **`assets_dir`** (`Path | None`) = `None` - Assets directory path (defaults to root_path/assets)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
