
---
title: "report"
type: "python-module"
source_file: "bengal/health/report.py"
line_number: 1
description: "Health check report formatting and data structures. Provides structured reporting of health check results with multiple output formats."
---

# report
**Type:** Module
**Source:** [View source](bengal/health/report.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[health](/api/bengal/health/) ›report

Health check report formatting and data structures.

Provides structured reporting of health check results with multiple output formats.

## Classes




### `CheckStatus`


**Inherits from:**`Enum`Status of a health check.

Severity levels (from most to least critical):
- ERROR: Blocks builds, must fix
- WARNING: Don't block, but should fix
- SUGGESTION: Quality improvements (collapsed by default)
- INFO: Contextual information (hidden unless verbose)
- SUCCESS: Check passed












### `CheckResult`


Result of a single health check.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`status`
: Status level (success, info, warning, error)

`message`
: Human-readable description of the check result

`recommendation`
: Optional suggestion for how to fix/improve (shown for warnings/errors)

`details`
: Optional additional context (list of strings)

`validator`
: Name of validator that produced this result

`metadata`
: 

:::







## Methods



#### `success`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def success(cls, message: str, validator: str = '') -> CheckResult
```


Create a success result.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `validator` | `str` | `''` | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`CheckResult`



#### `info`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def info(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '', metadata: dict[str, Any] | None = None) -> CheckResult
```


Create an info result.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `recommendation` | `str \| None` | - | *No description provided.* |
| `details` | `list[str] \| None` | - | *No description provided.* |
| `validator` | `str` | `''` | *No description provided.* |
| `metadata` | `dict[str, Any] \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`CheckResult`



#### `suggestion`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def suggestion(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '', metadata: dict[str, Any] | None = None) -> CheckResult
```


Create a suggestion result (quality improvement, not a problem).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `recommendation` | `str \| None` | - | *No description provided.* |
| `details` | `list[str] \| None` | - | *No description provided.* |
| `validator` | `str` | `''` | *No description provided.* |
| `metadata` | `dict[str, Any] \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`CheckResult`



#### `warning`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def warning(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '', metadata: dict[str, Any] | None = None) -> CheckResult
```


Create a warning result.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `recommendation` | `str \| None` | - | *No description provided.* |
| `details` | `list[str] \| None` | - | *No description provided.* |
| `validator` | `str` | `''` | *No description provided.* |
| `metadata` | `dict[str, Any] \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`CheckResult`



#### `error`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def error(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '', metadata: dict[str, Any] | None = None) -> CheckResult
```


Create an error result.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `recommendation` | `str \| None` | - | *No description provided.* |
| `details` | `list[str] \| None` | - | *No description provided.* |
| `validator` | `str` | `''` | *No description provided.* |
| `metadata` | `dict[str, Any] \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`CheckResult`



#### `is_problem`

:::{div} api-badge-group
:::

```python
def is_problem(self) -> bool
```


Check if this is a warning or error (vs success/info/suggestion).



:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `is_actionable`

:::{div} api-badge-group
:::

```python
def is_actionable(self) -> bool
```


Check if this requires action (error, warning, or suggestion).



:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `to_cache_dict`

:::{div} api-badge-group
:::

```python
def to_cache_dict(self) -> dict[str, Any]
```


Serialize CheckResult to JSON-serializable dict for caching.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Dictionary with all fields as JSON-serializable types



#### `from_cache_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def from_cache_dict(cls, data: dict[str, Any]) -> CheckResult
```


Deserialize CheckResult from cached dict.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary from cache |







:::{rubric} Returns
:class: rubric-returns
:::


`CheckResult` - CheckResult instance




### `ValidatorStats`


Observability metrics for a validator run.

These stats help diagnose performance issues and validate
that optimizations (like caching) are working correctly.

This class follows the ComponentStats pattern from bengal.utils.observability
but maintains page-specific naming for validator contexts.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`pages_total`
: Total pages in site

`pages_processed`
: Pages actually validated

`pages_skipped`
: Dict of skip reasons and counts

`cache_hits`
: Number of cache hits (if applicable)

`cache_misses`
: Number of cache misses (if applicable)

`sub_timings`
: Dict of sub-operation names to duration_ms

`metrics`
: Custom metrics (component-specific)

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
def format_summary(self) -> str
```


Format stats for debug output.



:::{rubric} Returns
:class: rubric-returns
:::


`str`



#### `to_log_context`

:::{div} api-badge-group
:::

```python
def to_log_context(self) -> dict[str, int | float | str]
```


Convert to flat dict for structured logging.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, int | float | str]` - Flat dictionary suitable for structured logging kwargs.




### `ValidatorReport`


Report for a single validator's checks.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`validator_name`
: Name of the validator

`results`
: List of check results from this validator

`duration_ms`
: How long the validator took to run

`stats`
: Optional observability metrics

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `passed_count` @property

```python
def passed_count(self) -> int
```
Count of successful checks.

#### `info_count` @property

```python
def info_count(self) -> int
```
Count of info messages.

#### `warning_count` @property

```python
def warning_count(self) -> int
```
Count of warnings.

#### `suggestion_count` @property

```python
def suggestion_count(self) -> int
```
Count of suggestions (quality improvements).

#### `error_count` @property

```python
def error_count(self) -> int
```
Count of errors.

#### `has_problems` @property

```python
def has_problems(self) -> bool
```
Check if this validator found any warnings or errors.

#### `status_emoji` @property

```python
def status_emoji(self) -> str
```
Get emoji representing overall status.







### `HealthReport`


Complete health check report for a build.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`validator_reports`
: Reports from each validator

`timestamp`
: When the health check was run

`build_stats`
: Optional build statistics

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `total_passed` @property

```python
def total_passed(self) -> int
```
Total successful checks across all validators.

#### `total_info` @property

```python
def total_info(self) -> int
```
Total info messages across all validators.

#### `total_warnings` @property

```python
def total_warnings(self) -> int
```
Total warnings across all validators.

#### `total_suggestions` @property

```python
def total_suggestions(self) -> int
```
Total suggestions (quality improvements) across all validators.

#### `total_errors` @property

```python
def total_errors(self) -> int
```
Total errors across all validators.

#### `total_checks` @property

```python
def total_checks(self) -> int
```
Total number of checks run.




## Methods



#### `has_errors`

:::{div} api-badge-group
:::

```python
def has_errors(self) -> bool
```


Check if any errors were found.



:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `has_warnings`

:::{div} api-badge-group
:::

```python
def has_warnings(self) -> bool
```


Check if any warnings were found.



:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `has_problems`

:::{div} api-badge-group
:::

```python
def has_problems(self) -> bool
```


Check if any errors or warnings were found.



:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `build_quality_score`

:::{div} api-badge-group
:::

```python
def build_quality_score(self) -> int
```


Calculate build quality score (0-100).

Formula:
- Each passed check: +1 point
- Each info: +0.8 points
- Each suggestion: +0.9 points (quality improvement, not a problem)
- Each warning: +0.5 points
- Each error: +0 points



:::{rubric} Returns
:class: rubric-returns
:::


`int` - Score from 0-100 (100 = perfect)



#### `quality_rating`

:::{div} api-badge-group
:::

```python
def quality_rating(self) -> str
```


Get quality rating based on score.



:::{rubric} Returns
:class: rubric-returns
:::


`str`



#### `format_console`

:::{div} api-badge-group
:::

```python
def format_console(self, mode: str = 'auto', verbose: bool = False, show_suggestions: bool = False) -> str
```


Format report for console output.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `mode` | `str` | `'auto'` | Display mode - "auto", "quiet", "normal", "verbose" auto = quiet if no problems, normal if warnings/errors |
| `verbose` | `bool` | `False` | Legacy parameter, sets mode to "verbose" |
| `show_suggestions` | `bool` | `False` | Whether to show suggestions (quality improvements) |







:::{rubric} Returns
:class: rubric-returns
:::


`str` - Formatted string ready to print






#### `format_json`

:::{div} api-badge-group
:::

```python
def format_json(self) -> dict[str, Any]
```


Format report as JSON-serializable dictionary.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Dictionary suitable for json.dumps()



---
*Generated by Bengal autodoc from `bengal/health/report.py`*

