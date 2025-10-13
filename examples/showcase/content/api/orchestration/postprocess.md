
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
- **`self`**
- **`site`** (`'Site'`) - Site instance with rendered pages and configuration





---
#### `run`
```python
def run(self, parallel: bool = True, progress_manager = None) -> None
```

Perform post-processing tasks (sitemap, RSS, output formats, link validation, etc.).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`parallel`** (`bool`) = `True` - Whether to run tasks in parallel
- **`progress_manager`** = `None` - Live progress manager (optional)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
