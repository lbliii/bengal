---
title: "orchestration.postprocess"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/postprocess.py"
---

# orchestration.postprocess

Post-processing orchestration for Bengal SSG.

Handles post-build tasks like sitemap generation, RSS feeds, and link validation.

**Source:** `../../bengal/orchestration/postprocess.py`

---

## Classes

### PostprocessOrchestrator


Handles post-processing tasks.

Responsibilities:
    - Sitemap generation
    - RSS feed generation
    - Link validation
    - Parallel/sequential execution of tasks




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize postprocess orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance with rendered pages and configuration







---
#### run

```python
def run(self, parallel: bool = True) -> None
```

Perform post-processing tasks (sitemap, RSS, output formats, link validation, etc.).

**Parameters:**

- **self**
- **parallel** (`bool`) = `True` - Whether to run tasks in parallel

**Returns:** `None`






---


