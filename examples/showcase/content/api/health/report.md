
---
title: "health.report"
type: python-module
source_file: "bengal/health/report.py"
css_class: api-content
description: "Health check report formatting and data structures.  Provides structured reporting of health check results with multiple output formats."
---

# health.report

Health check report formatting and data structures.

Provides structured reporting of health check results with multiple output formats.

---

## Classes

### `CheckStatus`

**Inherits from:** `Enum`
Status of a health check.





### `CheckResult`


Result of a single health check.

Attributes:
    status: Status level (success, info, warning, error)
    message: Human-readable description of the check result
    recommendation: Optional suggestion for how to fix/improve (shown for warnings/errors)
    details: Optional additional context (list of strings)
    validator: Name of validator that produced this result

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`status`** (`CheckStatus`)- **`message`** (`str`)- **`recommendation`** (`str | None`)- **`details`** (`list[str] | None`)- **`validator`** (`str`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `success` @classmethod
```python
def success(cls, message: str, validator: str = '') -> 'CheckResult'
```

Create a success result.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`cls`**
- **`message`** (`str`)
- **`validator`** (`str`) = `''`

:::{rubric} Returns
:class: rubric-returns
:::
`'CheckResult'`




---
#### `info` @classmethod
```python
def info(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '') -> 'CheckResult'
```

Create an info result.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cls` | - | - | - |
| `message` | `str` | - | - |
| `recommendation` | `str | None` | `None` | - |
| `details` | `list[str] | None` | `None` | - |
| `validator` | `str` | `''` | - |

:::{rubric} Returns
:class: rubric-returns
:::
`'CheckResult'`




---
#### `warning` @classmethod
```python
def warning(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '') -> 'CheckResult'
```

Create a warning result.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cls` | - | - | - |
| `message` | `str` | - | - |
| `recommendation` | `str | None` | `None` | - |
| `details` | `list[str] | None` | `None` | - |
| `validator` | `str` | `''` | - |

:::{rubric} Returns
:class: rubric-returns
:::
`'CheckResult'`




---
#### `error` @classmethod
```python
def error(cls, message: str, recommendation: str | None = None, details: list[str] | None = None, validator: str = '') -> 'CheckResult'
```

Create an error result.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `cls` | - | - | - |
| `message` | `str` | - | - |
| `recommendation` | `str | None` | `None` | - |
| `details` | `list[str] | None` | `None` | - |
| `validator` | `str` | `''` | - |

:::{rubric} Returns
:class: rubric-returns
:::
`'CheckResult'`




---
#### `is_problem`
```python
def is_problem(self) -> bool
```

Check if this is a warning or error (vs success/info).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool`




---

### `ValidatorReport`


Report for a single validator's checks.

Attributes:
    validator_name: Name of the validator
    results: List of check results from this validator
    duration_ms: How long the validator took to run

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`validator_name`** (`str`)- **`results`** (`list[CheckResult]`)- **`duration_ms`** (`float`)

:::{rubric} Properties
:class: rubric-properties
:::
#### `passed_count` @property

```python
@property
def passed_count(self) -> int
```

Count of successful checks.
#### `info_count` @property

```python
@property
def info_count(self) -> int
```

Count of info messages.
#### `warning_count` @property

```python
@property
def warning_count(self) -> int
```

Count of warnings.
#### `error_count` @property

```python
@property
def error_count(self) -> int
```

Count of errors.
#### `has_problems` @property

```python
@property
def has_problems(self) -> bool
```

Check if this validator found any warnings or errors.
#### `status_emoji` @property

```python
@property
def status_emoji(self) -> str
```

Get emoji representing overall status.

:::{rubric} Methods
:class: rubric-methods
:::
#### `passed_count`
```python
def passed_count(self) -> int
```

Count of successful checks.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `info_count`
```python
def info_count(self) -> int
```

Count of info messages.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `warning_count`
```python
def warning_count(self) -> int
```

Count of warnings.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `error_count`
```python
def error_count(self) -> int
```

Count of errors.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `has_problems`
```python
def has_problems(self) -> bool
```

Check if this validator found any warnings or errors.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool`




---
#### `status_emoji`
```python
def status_emoji(self) -> str
```

Get emoji representing overall status.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---

### `HealthReport`


Complete health check report for a build.

Attributes:
    validator_reports: Reports from each validator
    timestamp: When the health check was run
    build_stats: Optional build statistics

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`validator_reports`** (`list[ValidatorReport]`)- **`timestamp`** (`datetime`)- **`build_stats`** (`dict[str, Any] | None`)

:::{rubric} Properties
:class: rubric-properties
:::
#### `total_passed` @property

```python
@property
def total_passed(self) -> int
```

Total successful checks across all validators.
#### `total_info` @property

```python
@property
def total_info(self) -> int
```

Total info messages across all validators.
#### `total_warnings` @property

```python
@property
def total_warnings(self) -> int
```

Total warnings across all validators.
#### `total_errors` @property

```python
@property
def total_errors(self) -> int
```

Total errors across all validators.
#### `total_checks` @property

```python
@property
def total_checks(self) -> int
```

Total number of checks run.

:::{rubric} Methods
:class: rubric-methods
:::
#### `total_passed`
```python
def total_passed(self) -> int
```

Total successful checks across all validators.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `total_info`
```python
def total_info(self) -> int
```

Total info messages across all validators.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `total_warnings`
```python
def total_warnings(self) -> int
```

Total warnings across all validators.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `total_errors`
```python
def total_errors(self) -> int
```

Total errors across all validators.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `total_checks`
```python
def total_checks(self) -> int
```

Total number of checks run.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int`




---
#### `has_errors`
```python
def has_errors(self) -> bool
```

Check if any errors were found.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool`




---
#### `has_warnings`
```python
def has_warnings(self) -> bool
```

Check if any warnings were found.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool`




---
#### `has_problems`
```python
def has_problems(self) -> bool
```

Check if any errors or warnings were found.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`bool`




---
#### `build_quality_score`
```python
def build_quality_score(self) -> int
```

Calculate build quality score (0-100).

Formula:
- Each passed check: +1 point
- Each info: +0.8 points
- Each warning: +0.5 points
- Each error: +0 points



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`int` - Score from 0-100 (100 = perfect)




---
#### `quality_rating`
```python
def quality_rating(self) -> str
```

Get quality rating based on score.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
#### `format_console`
```python
def format_console(self, mode: str = 'auto', verbose: bool = False) -> str
```

Format report for console output.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`mode`** (`str`) = `'auto'` - Display mode - "auto", "quiet", "normal", "verbose" auto = quiet if no problems, normal if warnings/errors
- **`verbose`** (`bool`) = `False` - Legacy parameter, sets mode to "verbose"

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Formatted string ready to print




---
#### `format_json`
```python
def format_json(self) -> dict[str, Any]
```

Format report as JSON-serializable dictionary.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Dictionary suitable for json.dumps()




---
