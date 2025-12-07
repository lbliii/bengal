
---
title: "health_check"
type: "python-module"
source_file: "bengal/health/health_check.py"
line_number: 1
description: "Main health check orchestrator. Coordinates all validators and produces unified health reports. Supports parallel execution of validators for improved performance."
---

# health_check
**Type:** Module
**Source:** [View source](bengal/health/health_check.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[health](/api/bengal/health/) ›health_check

Main health check orchestrator.

Coordinates all validators and produces unified health reports.
Supports parallel execution of validators for improved performance.

## Classes




### `HealthCheckStats`


Statistics about health check execution.

Provides observability into parallel execution performance.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`total_duration_ms`
: 

`execution_mode`
: 

`validator_count`
: 

`worker_count`
: 

`cpu_count`
: 

`sum_validator_duration_ms`
: 

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `speedup` @property

```python
def speedup(self) -> float
```
Calculate speedup from parallel execution.

Returns ratio of sum(individual durations) / total duration.
A speedup of 2.0 means parallel was 2x faster than sequential would be.

#### `efficiency` @property

```python
def efficiency(self) -> float
```
Calculate parallel efficiency (0.0 to 1.0).

efficiency = speedup / worker_count
1.0 = perfect scaling, 0.5 = 50% efficiency




## Methods



#### `format_summary`

:::{div} api-badge-group
:::

```python
def format_summary(self) -> str
```


Format a human-readable summary.



:::{rubric} Returns
:class: rubric-returns
:::


`str`




### `HealthCheck`


Orchestrates health check validators and produces unified health reports.

By default, registers all standard validators. You can disable auto-registration
by passing auto_register=False, then manually register validators.

Usage:
    # Default: auto-registers all validators
    health = HealthCheck(site)
    report = health.run()
    print(report.format_console())

    # Manual registration:
    health = HealthCheck(site, auto_register=False)
    health.register(ConfigValidator())
    health.register(OutputValidator())
    report = health.run()



**Attributes:**

:::{div} api-attributes
`last_stats`
: 

:::







## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, site: Site, auto_register: bool = True)
```


Initialize health check system.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | The Site object to validate |
| `auto_register` | `bool` | `True` | Whether to automatically register all default validators |









#### `register`

:::{div} api-badge-group
:::

```python
def register(self, validator: BaseValidator) -> None
```


Register a validator to be run.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `validator` | `BaseValidator` | - | Validator instance to register |







:::{rubric} Returns
:class: rubric-returns
:::


`None`




#### `run`

:::{div} api-badge-group
:::

```python
def run(self, build_stats: dict | None = None, verbose: bool = False, profile: BuildProfile = None, incremental: bool = False, context: list[Path] | None = None, cache: Any = None, build_context: Any = None, tier: str = 'build') -> HealthReport
```


Run all registered validators and produce a health report.

Validators run in parallel when there are 3+ enabled validators,
falling back to sequential execution for smaller workloads.


**Parameters**

::::{dropdown} 8 parameters (click to expand)
:open: true

**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `build_stats` | `dict \| None` | - | Optional build statistics to include in report |
| `verbose` | `bool` | `False` | Whether to show verbose output during validation |
| `profile` | `BuildProfile` | - | Build profile to use for filtering validators |
| `incremental` | `bool` | `False` | If True, only validate changed files (requires cache) |
| `context` | `list[Path] \| None` | - | Optional list of specific file paths to validate (overrides incremental) |
| `cache` | `Any` | - | Optional BuildCache instance for incremental validation and result caching |
| `build_context` | `Any` | - | Optional BuildContext with cached artifacts (e.g., knowledge graph, cached content) that validators can use to avoid redundant computation. When build_context has cached content, validators like DirectiveValidator skip disk I/O, reducing health check time from ~4.6s to <100ms. |
| `tier` | `str` | `'build'` | Validation tier to run: - "build": Fast validators only (<100ms) - default - "full": + Knowledge graph validators (~500ms) - "ci": All validators including external checks (~30s) |



::::






:::{rubric} Returns
:class: rubric-returns
:::


`HealthReport` - HealthReport with results from all validators









#### `run_and_print`

:::{div} api-badge-group
:::

```python
def run_and_print(self, build_stats: dict | None = None, verbose: bool = False) -> HealthReport
```


Run health checks and print console output.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `build_stats` | `dict \| None` | - | Optional build statistics |
| `verbose` | `bool` | `False` | Whether to show all checks (not just problems) |







:::{rubric} Returns
:class: rubric-returns
:::


`HealthReport` - HealthReport



#### `__repr__`

:::{div} api-badge-group
:::

```python
def __repr__(self) -> str
```


*No description provided.*



:::{rubric} Returns
:class: rubric-returns
:::


`str`



---
*Generated by Bengal autodoc from `bengal/health/health_check.py`*

