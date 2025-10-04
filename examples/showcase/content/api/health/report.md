---
title: "health.report"
layout: api-reference
type: python-module
source_file: "../../bengal/health/report.py"
---

# health.report

Health check report formatting and data structures.

Provides structured reporting of health check results with multiple output formats.

**Source:** `../../bengal/health/report.py`

---

## Classes

### CheckStatus

**Inherits from:** `Enum`
Status of a health check.





### CheckResult


Result of a single health check.

Attributes:
    status: Status level (success, info, warning, error)
    message: Human-readable description of the check result
    recommendation: Optional suggestion for how to fix/improve (shown for warnings/errors)
    details: Optional additional context (list of strings)
    validator: Name of validator that produced this result

::: info
This is a dataclass.
:::

**Attributes:**

- **status** (`CheckStatus`)- **message** (`str`)- **recommendation** (`Optional[str]`)- **details** (`Optional[List[str]]`)- **validator** (`str`)

**Methods:**

#### success

```python
def success(cls, message: str, validator: str = '') -> 'CheckResult'
```

Create a success result.

**Parameters:**

- **cls**
- **message** (`str`)
- **validator** (`str`) = `''`

**Returns:** `'CheckResult'`






---
#### info

```python
def info(cls, message: str, recommendation: Optional[str] = None, validator: str = '') -> 'CheckResult'
```

Create an info result.

**Parameters:**

- **cls**
- **message** (`str`)
- **recommendation** (`Optional[str]`) = `None`
- **validator** (`str`) = `''`

**Returns:** `'CheckResult'`






---
#### warning

```python
def warning(cls, message: str, recommendation: Optional[str] = None, details: Optional[List[str]] = None, validator: str = '') -> 'CheckResult'
```

Create a warning result.

**Parameters:**

- **cls**
- **message** (`str`)
- **recommendation** (`Optional[str]`) = `None`
- **details** (`Optional[List[str]]`) = `None`
- **validator** (`str`) = `''`

**Returns:** `'CheckResult'`






---
#### error

```python
def error(cls, message: str, recommendation: Optional[str] = None, details: Optional[List[str]] = None, validator: str = '') -> 'CheckResult'
```

Create an error result.

**Parameters:**

- **cls**
- **message** (`str`)
- **recommendation** (`Optional[str]`) = `None`
- **details** (`Optional[List[str]]`) = `None`
- **validator** (`str`) = `''`

**Returns:** `'CheckResult'`






---
#### is_problem

```python
def is_problem(self) -> bool
```

Check if this is a warning or error (vs success/info).

**Parameters:**

- **self**

**Returns:** `bool`






---

### ValidatorReport


Report for a single validator's checks.

Attributes:
    validator_name: Name of the validator
    results: List of check results from this validator
    duration_ms: How long the validator took to run

::: info
This is a dataclass.
:::

**Attributes:**

- **validator_name** (`str`)- **results** (`List[CheckResult]`)- **duration_ms** (`float`)
**Properties:**

#### passed_count

```python
@property
def passed_count(self) -> int
```

Count of successful checks.
#### info_count

```python
@property
def info_count(self) -> int
```

Count of info messages.
#### warning_count

```python
@property
def warning_count(self) -> int
```

Count of warnings.
#### error_count

```python
@property
def error_count(self) -> int
```

Count of errors.
#### has_problems

```python
@property
def has_problems(self) -> bool
```

Check if this validator found any warnings or errors.
#### status_emoji

```python
@property
def status_emoji(self) -> str
```

Get emoji representing overall status.

**Methods:**

#### passed_count

```python
def passed_count(self) -> int
```

Count of successful checks.

**Parameters:**

- **self**

**Returns:** `int`






---
#### info_count

```python
def info_count(self) -> int
```

Count of info messages.

**Parameters:**

- **self**

**Returns:** `int`






---
#### warning_count

```python
def warning_count(self) -> int
```

Count of warnings.

**Parameters:**

- **self**

**Returns:** `int`






---
#### error_count

```python
def error_count(self) -> int
```

Count of errors.

**Parameters:**

- **self**

**Returns:** `int`






---
#### has_problems

```python
def has_problems(self) -> bool
```

Check if this validator found any warnings or errors.

**Parameters:**

- **self**

**Returns:** `bool`






---
#### status_emoji

```python
def status_emoji(self) -> str
```

Get emoji representing overall status.

**Parameters:**

- **self**

**Returns:** `str`






---

### HealthReport


Complete health check report for a build.

Attributes:
    validator_reports: Reports from each validator
    timestamp: When the health check was run
    build_stats: Optional build statistics

::: info
This is a dataclass.
:::

**Attributes:**

- **validator_reports** (`List[ValidatorReport]`)- **timestamp** (`datetime`)- **build_stats** (`Optional[Dict[str, Any]]`)
**Properties:**

#### total_passed

```python
@property
def total_passed(self) -> int
```

Total successful checks across all validators.
#### total_info

```python
@property
def total_info(self) -> int
```

Total info messages across all validators.
#### total_warnings

```python
@property
def total_warnings(self) -> int
```

Total warnings across all validators.
#### total_errors

```python
@property
def total_errors(self) -> int
```

Total errors across all validators.
#### total_checks

```python
@property
def total_checks(self) -> int
```

Total number of checks run.

**Methods:**

#### total_passed

```python
def total_passed(self) -> int
```

Total successful checks across all validators.

**Parameters:**

- **self**

**Returns:** `int`






---
#### total_info

```python
def total_info(self) -> int
```

Total info messages across all validators.

**Parameters:**

- **self**

**Returns:** `int`






---
#### total_warnings

```python
def total_warnings(self) -> int
```

Total warnings across all validators.

**Parameters:**

- **self**

**Returns:** `int`






---
#### total_errors

```python
def total_errors(self) -> int
```

Total errors across all validators.

**Parameters:**

- **self**

**Returns:** `int`






---
#### total_checks

```python
def total_checks(self) -> int
```

Total number of checks run.

**Parameters:**

- **self**

**Returns:** `int`






---
#### has_errors

```python
def has_errors(self) -> bool
```

Check if any errors were found.

**Parameters:**

- **self**

**Returns:** `bool`






---
#### has_warnings

```python
def has_warnings(self) -> bool
```

Check if any warnings were found.

**Parameters:**

- **self**

**Returns:** `bool`






---
#### has_problems

```python
def has_problems(self) -> bool
```

Check if any errors or warnings were found.

**Parameters:**

- **self**

**Returns:** `bool`






---
#### build_quality_score

```python
def build_quality_score(self) -> int
```

Calculate build quality score (0-100).

Formula:
- Each passed check: +1 point
- Each info: +0.8 points
- Each warning: +0.5 points
- Each error: +0 points

**Parameters:**

- **self**

**Returns:** `int` - Score from 0-100 (100 = perfect)






---
#### quality_rating

```python
def quality_rating(self) -> str
```

Get quality rating based on score.

**Parameters:**

- **self**

**Returns:** `str`






---
#### format_console

```python
def format_console(self, mode: str = 'auto', verbose: bool = False) -> str
```

Format report for console output.

**Parameters:**

- **self**
- **mode** (`str`) = `'auto'` - Display mode - "auto", "quiet", "normal", "verbose" auto = quiet if no problems, normal if warnings/errors
- **verbose** (`bool`) = `False` - Legacy parameter, sets mode to "verbose"

**Returns:** `str` - Formatted string ready to print






---
#### format_json

```python
def format_json(self) -> Dict[str, Any]
```

Format report as JSON-serializable dictionary.

**Parameters:**

- **self**

**Returns:** `Dict[str, Any]` - Dictionary suitable for json.dumps()






---


