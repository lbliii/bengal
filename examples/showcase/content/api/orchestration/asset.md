
---
title: "orchestration.asset"
type: python-module
source_file: "bengal/orchestration/asset.py"
css_class: api-content
description: "Asset processing orchestration for Bengal SSG.  Handles asset copying, minification, optimization, and fingerprinting."
---

# orchestration.asset

Asset processing orchestration for Bengal SSG.

Handles asset copying, minification, optimization, and fingerprinting.

---

## Classes

### `AssetOrchestrator`


Handles asset processing.

Responsibilities:
    - Copy assets to output directory
    - Minify CSS/JavaScript
    - Optimize images
    - Add fingerprints to filenames
    - Parallel/sequential processing




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize asset orchestrator.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`'Site'`) - Site instance containing assets and configuration





---
#### `process`
```python
def process(self, assets: list['Asset'], parallel: bool = True, progress_manager = None) -> None
```

Process and copy assets to output directory.

CSS entry points (style.css) are bundled to resolve @imports.
CSS modules are skipped (they're bundled into entry points).
All other assets are processed normally.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`assets`** (`list['Asset']`) - List of assets to process
- **`parallel`** (`bool`) = `True` - Whether to use parallel processing
- **`progress_manager`** = `None` - Live progress manager (optional)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
