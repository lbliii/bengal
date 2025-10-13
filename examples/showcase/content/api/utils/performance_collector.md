
---
title: "utils.performance_collector"
type: python-module
source_file: "bengal/utils/performance_collector.py"
css_class: api-content
description: "Performance metrics collection for Bengal SSG.  Collects and persists build performance metrics including timing and memory usage. This is Phase 1 of the continuous performance tracking system.  Ex..."
---

# utils.performance_collector

Performance metrics collection for Bengal SSG.

Collects and persists build performance metrics including timing and memory usage.
This is Phase 1 of the continuous performance tracking system.

Example:
    from bengal.utils.performance_collector import PerformanceCollector

    collector = PerformanceCollector()
    collector.start_build()

    # ... run build ...

    stats = collector.end_build(build_stats)
    collector.save(stats)

---

## Classes

### `PerformanceCollector`


Collects and persists build performance metrics.

Phase 1 implementation: Basic timing and memory collection.
Future phases will add per-phase tracking, git info, and top allocators.

Usage:
    collector = PerformanceCollector()
    collector.start_build()

    # ... execute build ...

    stats = collector.end_build(build_stats)
    collector.save(stats)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, metrics_dir: Path | None = None)
```

Initialize performance collector.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`metrics_dir`** (`Path | None`) = `None` - Directory to store metrics (default: .bengal-metrics)





---
#### `start_build`
```python
def start_build(self)
```

Start collecting metrics for a build.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `end_build`
```python
def end_build(self, stats)
```

End collection and update stats with memory metrics.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`stats`** - BuildStats object to update with memory information





---
#### `save`
```python
def save(self, stats)
```

Save metrics to disk for historical tracking.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`stats`** - BuildStats object to persist





---
#### `get_summary`
```python
def get_summary(self, stats) -> str
```

Generate a one-line summary of build metrics.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`stats`** - BuildStats object

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Formatted summary string




---


## Functions

### `format_memory`
```python
def format_memory(mb: float) -> str
```

Format memory size for display.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`mb`** (`float`) - Memory in megabytes

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Formatted string (e.g., "125.3 MB" or "1.2 GB")




---
