---
title: "orchestration.build"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/build.py"
---

# orchestration.build

Build orchestration for Bengal SSG.

Main coordinator that delegates build phases to specialized orchestrators.

**Source:** `../../bengal/orchestration/build.py`

---

## Classes

### BuildOrchestrator


Main build coordinator that orchestrates the entire build process.

Delegates to specialized orchestrators for each phase:
    - ContentOrchestrator: Discovery and setup
    - TaxonomyOrchestrator: Taxonomies and dynamic pages
    - MenuOrchestrator: Navigation menus
    - RenderOrchestrator: Page rendering
    - AssetOrchestrator: Asset processing
    - PostprocessOrchestrator: Sitemap, RSS, validation
    - IncrementalOrchestrator: Change detection and caching




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize build orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance to build







---
#### build

```python
def build(self, parallel: bool = True, incremental: bool = False, verbose: bool = False) -> BuildStats
```

Execute full build pipeline.

**Parameters:**

- **self**
- **parallel** (`bool`) = `True` - Whether to use parallel processing
- **incremental** (`bool`) = `False` - Whether to perform incremental build (only changed files)
- **verbose** (`bool`) = `False` - Whether to show detailed build information

**Returns:** `BuildStats` - BuildStats object with build statistics






---


