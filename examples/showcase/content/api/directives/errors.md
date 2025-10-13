
---
title: "directives.errors"
type: python-module
source_file: "bengal/rendering/plugins/directives/errors.py"
css_class: api-content
description: "Rich error reporting for directive parsing.  Provides detailed, helpful error messages when directives fail to parse."
---

# directives.errors

Rich error reporting for directive parsing.

Provides detailed, helpful error messages when directives fail to parse.

---

## Classes

### `DirectiveError`

**Inherits from:** `Exception`
Rich error for directive parsing failures.

Provides detailed context including:
- Directive type that failed
- File path and line number
- Content snippet showing the problem
- Helpful suggestions for fixing




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, directive_type: str, error_message: str, file_path: Path | None = None, line_number: int | None = None, content_snippet: str | None = None, suggestion: str | None = None)
```

Initialize directive error.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `directive_type` | `str` | - | Type of directive that failed (e.g., 'tabs', 'note') |
| `error_message` | `str` | - | Human-readable error description |
| `file_path` | `Path | None` | `None` | Path to file containing the directive |
| `line_number` | `int | None` | `None` | Line number where directive starts |
| `content_snippet` | `str | None` | `None` | Snippet of content showing the problem |
| `suggestion` | `str | None` | `None` | Helpful suggestion for fixing the issue |





---
#### `display`
```python
def display(self) -> str
```

Get formatted error message (same as __str__).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---


## Functions

### `format_directive_error`
```python
def format_directive_error(directive_type: str, error_message: str, file_path: Path | None = None, line_number: int | None = None, content_lines: list | None = None, error_line_offset: int = 0, suggestion: str | None = None) -> str
```

Format a directive error message.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `directive_type` | `str` | - | Type of directive |
| `error_message` | `str` | - | Error description |
| `file_path` | `Path | None` | `None` | File containing the error |
| `line_number` | `int | None` | `None` | Line number of directive |
| `content_lines` | `list | None` | `None` | Lines of content around the error |
| `error_line_offset` | `int` | `0` | Which line in content_lines has the error (for highlighting) |
| `suggestion` | `str | None` | `None` | Helpful suggestion |

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Formatted error message




---
### `get_suggestion`
```python
def get_suggestion(error_key: str) -> str | None
```

Get a helpful suggestion for a common error type.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`error_key`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`str | None`




---
