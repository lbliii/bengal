
---
title: "orchestration.streaming"
type: python-module
source_file: "bengal/orchestration/streaming.py"
css_class: api-content
description: "Streaming build orchestration for memory-optimized builds.  Uses knowledge graph analysis to process pages in optimal order for memory efficiency. Hub-first strategy: Keep highly connected pages in..."
---

# orchestration.streaming

Streaming build orchestration for memory-optimized builds.

Uses knowledge graph analysis to process pages in optimal order for memory efficiency.
Hub-first strategy: Keep highly connected pages in memory, stream leaves.

---

## Classes

### `StreamingRenderOrchestrator`


Memory-optimized page rendering using knowledge graph analysis.

Strategy:
1. Build knowledge graph to identify connectivity
2. Process hubs first (keep in memory - they're needed often)
3. Stream leaves in batches (release immediately after rendering)
4. Result: 80-90% memory reduction for large sites

Best for: Sites with 5K+ pages




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Site)
```

Initialize streaming render orchestrator.



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
  - `Site`
  - -
  - Site instance containing pages
:::

::::




---
#### `process`
```python
def process(self, pages: list[Page], parallel: bool = True, quiet: bool = False, tracker: DependencyTracker | None = None, stats: BuildStats | None = None, batch_size: int = 100, progress_manager: Any | None = None, reporter: Any | None = None, build_context: Any | None = None) -> None
```

Render pages in memory-optimized batches using connectivity analysis.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 10 parameters (click to expand)
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
* - `pages`
  - `list[Page]`
  - -
  - List of pages to render
* - `parallel`
  - `bool`
  - `True`
  - Whether to use parallel rendering
* - `quiet`
  - `bool`
  - `False`
  - Whether to suppress progress output (minimal output mode)
* - `tracker`
  - `DependencyTracker | None`
  - `None`
  - Dependency tracker for incremental builds
* - `stats`
  - `BuildStats | None`
  - `None`
  - Build statistics tracker
* - `batch_size`
  - `int`
  - `100`
  - Number of leaves to process per batch
* - `progress_manager`
  - `Any | None`
  - `None`
  - Optional progress manager to use for unified progress display
* - `reporter`
  - `Any | None`
  - `None`
  - -
* - `build_context`
  - `Any | None`
  - `None`
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


