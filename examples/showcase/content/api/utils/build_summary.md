
---
title: "utils.build_summary"
type: python-module
source_file: "bengal/utils/build_summary.py"
css_class: api-content
description: "Rich build summary dashboard with performance insights.  Displays comprehensive build statistics with: - Timing breakdown - Performance grade - Smart suggestions - Cache statistics - Resource usage"
---

# utils.build_summary

Rich build summary dashboard with performance insights.

Displays comprehensive build statistics with:
- Timing breakdown
- Performance grade
- Smart suggestions
- Cache statistics
- Resource usage

---


## Functions

### `create_timing_breakdown_table`
```python
def create_timing_breakdown_table(stats: BuildStats) -> Table
```

Create a detailed timing breakdown table.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics

:::{rubric} Returns
:class: rubric-returns
:::
`Table` - Rich Table with phase timing breakdown




---
### `create_performance_panel`
```python
def create_performance_panel(stats: BuildStats, advisor: PerformanceAdvisor) -> Panel
```

Create performance grade and insights panel.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics
- **`advisor`** (`PerformanceAdvisor`) - Performance advisor with analysis

:::{rubric} Returns
:class: rubric-returns
:::
`Panel` - Rich Panel with performance insights




---
### `create_suggestions_panel`
```python
def create_suggestions_panel(advisor: PerformanceAdvisor) -> Panel | None
```

Create smart suggestions panel.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`advisor`** (`PerformanceAdvisor`) - Performance advisor with analysis

:::{rubric} Returns
:class: rubric-returns
:::
`Panel | None` - Rich Panel with suggestions, or None if no suggestions




---
### `create_cache_stats_panel`
```python
def create_cache_stats_panel(stats: BuildStats) -> Panel | None
```

Create cache statistics panel (if available).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics

:::{rubric} Returns
:class: rubric-returns
:::
`Panel | None` - Rich Panel with cache stats, or None if not applicable




---
### `create_content_stats_table`
```python
def create_content_stats_table(stats: BuildStats) -> Table
```

Create content statistics table.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics

:::{rubric} Returns
:class: rubric-returns
:::
`Table` - Rich Table with content stats




---
### `display_build_summary`
```python
def display_build_summary(stats: BuildStats, environment: dict[str, Any] | None = None) -> None
```

Display comprehensive build summary with rich formatting.

This is the main entry point for Phase 2 build summaries.
Shows timing breakdown, performance analysis, and smart suggestions.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics
- **`environment`** (`dict[str, Any] | None`) = `None` - Environment info (from detect_environment())

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `display_simple_summary`
```python
def display_simple_summary(stats: BuildStats) -> None
```

Display simple summary for writer persona (minimal output).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
