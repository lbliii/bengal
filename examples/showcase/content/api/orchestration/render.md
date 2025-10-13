
---
title: "orchestration.render"
type: python-module
source_file: "bengal/orchestration/render.py"
css_class: api-content
description: "Rendering orchestration for Bengal SSG.  Handles page rendering in both sequential and parallel modes."
---

# orchestration.render

Rendering orchestration for Bengal SSG.

Handles page rendering in both sequential and parallel modes.

---

## Classes

### `RenderOrchestrator`


Handles page rendering.

Responsibilities:
    - Sequential page rendering
    - Parallel page rendering with thread-local pipelines
    - Pipeline creation and management




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Site)
```

Initialize render orchestrator.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`Site`) - Site instance containing pages and configuration





---
#### `process`
```python
def process(self, pages: list[Page], parallel: bool = True, quiet: bool = False, tracker: DependencyTracker | None = None, stats: BuildStats | None = None, progress_manager: Any | None = None) -> None
```

Render pages (parallel or sequential).



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `pages` | `list[Page]` | - | List of pages to render |
| `parallel` | `bool` | `True` | Whether to use parallel rendering |
| `quiet` | `bool` | `False` | Whether to suppress progress output (minimal output mode) |
| `tracker` | `DependencyTracker | None` | `None` | Dependency tracker for incremental builds |
| `stats` | `BuildStats | None` | `None` | Build statistics tracker |
| `progress_manager` | `Any | None` | `None` | Live progress manager (optional) |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
