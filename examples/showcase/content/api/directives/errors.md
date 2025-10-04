---
title: "directives.errors"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/errors.py"
---

# directives.errors

Rich error reporting for directive parsing.

Provides detailed, helpful error messages when directives fail to parse.

**Source:** `../../bengal/rendering/plugins/directives/errors.py`

---

## Classes

### DirectiveError

**Inherits from:** `Exception`
Rich error for directive parsing failures.

Provides detailed context including:
- Directive type that failed
- File path and line number
- Content snippet showing the problem
- Helpful suggestions for fixing




**Methods:**

#### __init__

```python
def __init__(self, directive_type: str, error_message: str, file_path: Optional[Path] = None, line_number: Optional[int] = None, content_snippet: Optional[str] = None, suggestion: Optional[str] = None)
```

Initialize directive error.

**Parameters:**

- **self**
- **directive_type** (`str`) - Type of directive that failed (e.g., 'tabs', 'note')
- **error_message** (`str`) - Human-readable error description
- **file_path** (`Optional[Path]`) = `None` - Path to file containing the directive
- **line_number** (`Optional[int]`) = `None` - Line number where directive starts
- **content_snippet** (`Optional[str]`) = `None` - Snippet of content showing the problem
- **suggestion** (`Optional[str]`) = `None` - Helpful suggestion for fixing the issue







---
#### display

```python
def display(self) -> str
```

Get formatted error message (same as __str__).

**Parameters:**

- **self**

**Returns:** `str`






---


## Functions

### format_directive_error

```python
def format_directive_error(directive_type: str, error_message: str, file_path: Optional[Path] = None, line_number: Optional[int] = None, content_lines: Optional[list] = None, error_line_offset: int = 0, suggestion: Optional[str] = None) -> str
```

Format a directive error message.

**Parameters:**

- **directive_type** (`str`) - Type of directive
- **error_message** (`str`) - Error description
- **file_path** (`Optional[Path]`) = `None` - File containing the error
- **line_number** (`Optional[int]`) = `None` - Line number of directive
- **content_lines** (`Optional[list]`) = `None` - Lines of content around the error
- **error_line_offset** (`int`) = `0` - Which line in content_lines has the error (for highlighting)
- **suggestion** (`Optional[str]`) = `None` - Helpful suggestion

**Returns:** `str` - Formatted error message





---
### get_suggestion

```python
def get_suggestion(error_key: str) -> Optional[str]
```

Get a helpful suggestion for a common error type.

**Parameters:**

- **error_key** (`str`)

**Returns:** `Optional[str]`





---
