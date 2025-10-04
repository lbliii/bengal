---
title: "orchestration.render"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/render.py"
---

# orchestration.render

Rendering orchestration for Bengal SSG.

Handles page rendering in both sequential and parallel modes.

**Source:** `../../bengal/orchestration/render.py`

---

## Classes

### RenderOrchestrator


Handles page rendering.

Responsibilities:
    - Sequential page rendering
    - Parallel page rendering with thread-local pipelines
    - Pipeline creation and management




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize render orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance containing pages and configuration







---
#### process

```python
def process(self, pages: List['Page'], parallel: bool = True, tracker: Optional['DependencyTracker'] = None, stats: Optional['BuildStats'] = None) -> None
```

Render pages (parallel or sequential).

**Parameters:**

- **self**
- **pages** (`List['Page']`) - List of pages to render
- **parallel** (`bool`) = `True` - Whether to use parallel rendering
- **tracker** (`Optional['DependencyTracker']`) = `None` - Dependency tracker for incremental builds
- **stats** (`Optional['BuildStats']`) = `None` - Build statistics tracker

**Returns:** `None`






---


