
---
title: "observability"
type: "python-module"
source_file: "bengal/utils/observability.py"
line_number: 1
description: "Observability utilities for systematic stats collection across Bengal\'s build pipeline. Provides standardized stats collection and formatting for debugging performance issues, cache effectiveness, and..."
---

# observability
**Type:** Module
**Source:** [View source](bengal/utils/observability.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›observability

Observability utilities for systematic stats collection across Bengal's build pipeline.

Provides standardized stats collection and formatting for debugging performance issues,
cache effectiveness, and processing bottlenecks.

This module implements the observability improvements from RFC: rfc-observability-improvements.md

Key Concepts:
    - ComponentStats: Standardized stats container with counts, cache metrics, and sub-timings
    - HasStats: Protocol for components that expose observability stats
    - Consistent formatting for CLI output and structured logging

Usage:
    >>> from bengal.utils.observability import ComponentStats, HasStats
    >>> stats = ComponentStats(items_total=100, items_processed=80)
    >>> stats.items_skipped["filtered"] = 20
    >>> print(stats.format_summary("MyComponent"))
    MyComponent: processed=80/100 | skipped=[filtered=20]

Related:
    - bengal/health/report.py: ValidatorStats (extends ComponentStats pattern)
    - bengal/orchestration/build/finalization.py: CLI output integration
    - plan/active/rfc-observability-improvements.md: Design rationale

## Classes




### `HasStats`


**Inherits from:**`Protocol`Protocol for components that expose observability stats.

Components implementing this protocol can have their stats displayed
automatically when phases exceed performance thresholds.



**Attributes:**

:::{div} api-attributes
`last_stats`
: 

:::










### `ComponentStats`


Standardized stats container for any build component.

Provides a uniform interface for tracking:
- Processing counts (total, processed, skipped by reason)
- Cache effectiveness (hits, misses, hit rate)
- Sub-operation timings (analyze, render, validate, etc.)
- Custom metrics (component-specific values)


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`items_total`
: Total items to process

`items_processed`
: Items actually processed

`items_skipped`
: Dict of skip reasons and counts (e.g., {"autodoc": 450, "draft": 3})

`cache_hits`
: Number of cache hits (if applicable)

`cache_misses`
: Number of cache misses (if applicable)

`sub_timings`
: Dict of sub-operation names to duration_ms

`metrics`
: Custom metrics (component-specific, e.g., {"pages_per_sec": 375})

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `cache_hit_rate` @property

```python
def cache_hit_rate(self) -> float
```
Cache hit rate as percentage (0-100).

#### `skip_rate` @property

```python
def skip_rate(self) -> float
```
Skip rate as percentage (0-100).

#### `total_skipped` @property

```python
def total_skipped(self) -> int
```
Total number of skipped items across all reasons.




## Methods



#### `format_summary`

:::{div} api-badge-group
:::

```python
def format_summary(self, name: str = '') -> str
```


Format stats for CLI output.

Produces a compact, informative summary suitable for terminal display.
Only includes sections with actual data.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | `''` | Component name prefix (e.g., "Directives", "Links") |







:::{rubric} Returns
:class: rubric-returns
:::


`str` - Formatted string like "processed=80/100 | skipped=[autodoc=450] | cache=80/80 (100%)"
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> stats = ComponentStats(items_total=100, items_processed=80)
    >>> stats.format_summary("Test")
    "Test: processed=80/100"
```




#### `to_log_context`

:::{div} api-badge-group
:::

```python
def to_log_context(self) -> dict[str, int | float | str]
```


Convert to flat dict for structured logging.

Flattens nested data structures for log aggregation systems.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, int | float | str]` - Flat dictionary suitable for structured logging kwargs.
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> stats = ComponentStats(items_total=100, cache_hits=80)
    >>> stats.to_log_context()
    {'items_total': 100, 'items_processed': 0, 'cache_hits': 80, ...}
```

## Functions



### `format_phase_stats`


```python
def format_phase_stats(phase_name: str, duration_ms: float, component: HasStats | None, slow_threshold_ms: float = 1000) -> str | None
```



Format stats for a slow phase, if applicable.

Returns formatted stats string only if the phase exceeded the threshold
AND the component has stats available.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_name` | `str` | - | Name of the phase (e.g., "Directives", "Links") |
| `duration_ms` | `float` | - | How long the phase took |
| `component` | `HasStats \| None` | - | Component with HasStats protocol (or None) |
| `slow_threshold_ms` | `float` | `1000` | Threshold for considering a phase "slow" |







**Returns**


`str | None` - Formatted stats string, or None if phase was fast or no stats available.
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> validator = DirectiveValidator()
    >>> validator.validate(site)  # Sets last_stats
    >>> stats_str = format_phase_stats("Directives", 7554, validator)
    >>> if stats_str:
    ...     print(f"   📊 {stats_str}")
```



---
*Generated by Bengal autodoc from `bengal/utils/observability.py`*

