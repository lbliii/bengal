
---
title: "report"
type: "python-module"
source_file: "bengal/bengal/health/report.py"
line_number: 1
description: "Health check report formatting and data structures. Provides structured reporting of health check results with multiple output formats."
---

# report
**Type:** Module
**Source:** [View source](bengal/bengal/health/report.py#L1)



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

| Name | Type | Description |
|:-----|:-----|:------------|
| `status` | - | Status level (success, info, warning, error) |
| `message` | - | Human-readable description of the check result |
| `recommendation` | - | Optional suggestion for how to fix/improve (shown for warnings/errors) |
| `details` | - | Optional additional context (list of strings) |
| `validator` | - | Name of validator that produced this result |
| `metadata` | - | *No description provided.* |







## Methods



#### `success` @classmethod
```python
def success(cls, message: str, validator: str = '') -> CheckResult
```


Create a success result.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |
| `validator` | `str` | `''` | *No description provided.* |







**Returns**


`CheckResult`



#### `info` @classmethod
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







**Returns**


`CheckResult`



#### `suggestion` @classmethod
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







**Returns**


`CheckResult`



#### `warning` @classmethod
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







**Returns**


`CheckResult`



#### `error` @classmethod
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







**Returns**


`CheckResult`



#### `is_problem`
```python
def is_problem(self) -> bool
```


Check if this is a warning or error (vs success/info/suggestion).



**Returns**


`bool`



#### `is_actionable`
```python
def is_actionable(self) -> bool
```


Check if this requires action (error, warning, or suggestion).



**Returns**


`bool`



#### `to_cache_dict`
```python
def to_cache_dict(self) -> dict[str, Any]
```


Serialize CheckResult to JSON-serializable dict for caching.



**Returns**


`dict[str, Any]` - Dictionary with all fields as JSON-serializable types



#### `from_cache_dict` @classmethod
```python
def from_cache_dict(cls, data: dict[str, Any]) -> CheckResult
```


Deserialize CheckResult from cached dict.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | Dictionary from cache |







**Returns**


`CheckResult` - CheckResult instance




### `ValidatorReport`


Report for a single validator's checks.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `validator_name` | - | Name of the validator |
| `results` | - | List of check results from this validator |
| `duration_ms` | - | How long the validator took to run |




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




## Methods



#### `passed_count`
```python
def passed_count(self) -> int
```


Count of successful checks.



**Returns**


`int`



#### `info_count`
```python
def info_count(self) -> int
```


Count of info messages.



**Returns**


`int`



#### `warning_count`
```python
def warning_count(self) -> int
```


Count of warnings.



**Returns**


`int`



#### `suggestion_count`
```python
def suggestion_count(self) -> int
```


Count of suggestions (quality improvements).



**Returns**


`int`



#### `error_count`
```python
def error_count(self) -> int
```


Count of errors.



**Returns**


`int`



#### `has_problems`
```python
def has_problems(self) -> bool
```


Check if this validator found any warnings or errors.



**Returns**


`bool`



#### `status_emoji`
```python
def status_emoji(self) -> str
```


Get emoji representing overall status.



**Returns**


`str`




### `HealthReport`


Complete health check report for a build.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `validator_reports` | - | Reports from each validator |
| `timestamp` | - | When the health check was run |
| `build_stats` | - | Optional build statistics |




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



#### `total_passed`
```python
def total_passed(self) -> int
```


Total successful checks across all validators.



**Returns**


`int`



#### `total_info`
```python
def total_info(self) -> int
```


Total info messages across all validators.



**Returns**


`int`



#### `total_warnings`
```python
def total_warnings(self) -> int
```


Total warnings across all validators.



**Returns**


`int`



#### `total_suggestions`
```python
def total_suggestions(self) -> int
```


Total suggestions (quality improvements) across all validators.



**Returns**


`int`



#### `total_errors`
```python
def total_errors(self) -> int
```


Total errors across all validators.



**Returns**


`int`



#### `total_checks`
```python
def total_checks(self) -> int
```


Total number of checks run.



**Returns**


`int`



#### `has_errors`
```python
def has_errors(self) -> bool
```


Check if any errors were found.



**Returns**


`bool`



#### `has_warnings`
```python
def has_warnings(self) -> bool
```


Check if any warnings were found.



**Returns**


`bool`



#### `has_problems`
```python
def has_problems(self) -> bool
```


Check if any errors or warnings were found.



**Returns**


`bool`



#### `build_quality_score`
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



**Returns**


`int` - Score from 0-100 (100 = perfect)



#### `quality_rating`
```python
def quality_rating(self) -> str
```


Get quality rating based on score.



**Returns**


`str`



#### `format_console`
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







**Returns**


`str` - Formatted string ready to print






#### `format_json`
```python
def format_json(self) -> dict[str, Any]
```


Format report as JSON-serializable dictionary.



**Returns**


`dict[str, Any]` - Dictionary suitable for json.dumps()



---
*Generated by Bengal autodoc from `bengal/bengal/health/report.py`*

