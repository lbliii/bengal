---
title: "orchestration.incremental"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/incremental.py"
---

# orchestration.incremental

Incremental build orchestration for Bengal SSG.

Handles cache management, change detection, and determining what needs rebuilding.

**Source:** `../../bengal/orchestration/incremental.py`

---

## Classes

### IncrementalOrchestrator


Handles incremental build logic.

Responsibilities:
    - Cache initialization and management
    - Change detection (content, assets, templates)
    - Dependency tracking
    - Taxonomy change detection
    - Determining what needs rebuilding




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize incremental orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance for incremental builds







---
#### initialize

```python
def initialize(self, enabled: bool = False) -> Tuple['BuildCache', 'DependencyTracker']
```

Initialize cache and tracker.

**Parameters:**

- **self**
- **enabled** (`bool`) = `False` - Whether incremental builds are enabled

**Returns:** `Tuple['BuildCache', 'DependencyTracker']` - Tuple of (cache, tracker)






---
#### check_config_changed

```python
def check_config_changed(self) -> bool
```

Check if config file has changed (requires full rebuild).

**Parameters:**

- **self**

**Returns:** `bool` - True if config changed






---
#### find_work

```python
def find_work(self, verbose: bool = False) -> Tuple[List['Page'], List['Asset'], Dict[str, List]]
```

Find pages/assets that need rebuilding.

**Parameters:**

- **self**
- **verbose** (`bool`) = `False` - Whether to collect detailed change information

**Returns:** `Tuple[List['Page'], List['Asset'], Dict[str, List]]` - Tuple of (pages_to_build, assets_to_process, change_summary)






---
#### save_cache

```python
def save_cache(self, pages_built: List['Page'], assets_processed: List['Asset']) -> None
```

Update cache with processed files.

**Parameters:**

- **self**
- **pages_built** (`List['Page']`) - Pages that were built
- **assets_processed** (`List['Asset']`) - Assets that were processed

**Returns:** `None`






---


