---
title: "orchestration.asset"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/asset.py"
---

# orchestration.asset

Asset processing orchestration for Bengal SSG.

Handles asset copying, minification, optimization, and fingerprinting.

**Source:** `../../bengal/orchestration/asset.py`

---

## Classes

### AssetOrchestrator


Handles asset processing.

Responsibilities:
    - Copy assets to output directory
    - Minify CSS/JavaScript
    - Optimize images
    - Add fingerprints to filenames
    - Parallel/sequential processing




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize asset orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance containing assets and configuration







---
#### process

```python
def process(self, assets: List['Asset'], parallel: bool = True) -> None
```

Process and copy assets to output directory.

**Parameters:**

- **self**
- **assets** (`List['Asset']`) - List of assets to process
- **parallel** (`bool`) = `True` - Whether to use parallel processing

**Returns:** `None`






---


