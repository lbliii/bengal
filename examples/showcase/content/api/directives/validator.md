---
title: "directives.validator"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/plugins/directives/validator.py"
---

# directives.validator

Pre-parse validation for directives.

Validates directive syntax before parsing to catch errors early with
helpful messages.

**Source:** `../../bengal/rendering/plugins/directives/validator.py`

---

## Classes

### DirectiveSyntaxValidator


Validates directive syntax before parsing.

Catches common errors early with helpful messages before expensive
parsing and recursive markdown processing.




**Methods:**

#### validate_tabs_directive

```python
def validate_tabs_directive(content: str, file_path: Optional[Path] = None, line_number: Optional[int] = None) -> List[str]
```

Validate tabs directive content.

**Parameters:**

- **content** (`str`) - Directive content (between opening and closing backticks)
- **file_path** (`Optional[Path]`) = `None` - Optional file path for error messages
- **line_number** (`Optional[int]`) = `None` - Optional line number for error messages

**Returns:** `List[str]` - List of validation error messages (empty if valid)






---
#### validate_code_tabs_directive

```python
def validate_code_tabs_directive(content: str, file_path: Optional[Path] = None, line_number: Optional[int] = None) -> List[str]
```

Validate code-tabs directive content.

**Parameters:**

- **content** (`str`) - Directive content
- **file_path** (`Optional[Path]`) = `None` - Optional file path
- **line_number** (`Optional[int]`) = `None` - Optional line number

**Returns:** `List[str]` - List of validation errors






---
#### validate_dropdown_directive

```python
def validate_dropdown_directive(content: str, title: str = '', file_path: Optional[Path] = None, line_number: Optional[int] = None) -> List[str]
```

Validate dropdown directive content.

**Parameters:**

- **content** (`str`) - Directive content
- **title** (`str`) = `''` - Directive title
- **file_path** (`Optional[Path]`) = `None` - Optional file path
- **line_number** (`Optional[int]`) = `None` - Optional line number

**Returns:** `List[str]` - List of validation errors






---
#### validate_admonition_directive

```python
def validate_admonition_directive(admon_type: str, content: str, file_path: Optional[Path] = None, line_number: Optional[int] = None) -> List[str]
```

Validate admonition directive content.

**Parameters:**

- **admon_type** (`str`) - Type of admonition (note, tip, warning, etc.)
- **content** (`str`) - Directive content
- **file_path** (`Optional[Path]`) = `None` - Optional file path
- **line_number** (`Optional[int]`) = `None` - Optional line number

**Returns:** `List[str]` - List of validation errors






---
#### validate_directive

```python
def validate_directive(cls, directive_type: str, content: str, title: str = '', options: Dict[str, Any] = None, file_path: Optional[Path] = None, line_number: Optional[int] = None) -> List[str]
```

Validate any directive type.

**Parameters:**

- **cls**
- **directive_type** (`str`) - Type of directive (tabs, note, dropdown, etc.)
- **content** (`str`) - Directive content
- **title** (`str`) = `''` - Directive title (if any)
- **options** (`Dict[str, Any]`) = `None` - Directive options dictionary
- **file_path** (`Optional[Path]`) = `None` - Optional file path
- **line_number** (`Optional[int]`) = `None` - Optional line number

**Returns:** `List[str]` - List of validation errors (empty if valid)






---
#### validate_directive_block

```python
def validate_directive_block(cls, directive_block: str, file_path: Optional[Path] = None, start_line: Optional[int] = None) -> Dict[str, Any]
```

Validate a complete directive block from markdown.

**Parameters:**

- **cls**
- **directive_block** (`str`) - Full directive block including opening/closing backticks
- **file_path** (`Optional[Path]`) = `None` - Optional file path
- **start_line** (`Optional[int]`) = `None` - Optional starting line number

**Returns:** `Dict[str, Any]` - Dictionary with validation results:
    {
        'valid': bool,
        'errors': List[str],
        'directive_type': str,
        'content': str,
        'title': str,
        'options': Dict[str, Any]
    }






---


## Functions

### validate_markdown_directives

```python
def validate_markdown_directives(markdown_content: str, file_path: Optional[Path] = None) -> List[Dict[str, Any]]
```

Validate all directive blocks in a markdown file.

**Parameters:**

- **markdown_content** (`str`) - Full markdown content
- **file_path** (`Optional[Path]`) = `None` - Optional file path for error reporting

**Returns:** `List[Dict[str, Any]]` - List of validation results, one per directive block





---
### get_directive_validation_summary

```python
def get_directive_validation_summary(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Get a summary of directive validation results.

**Parameters:**

- **validation_results** (`List[Dict[str, Any]]`) - List of validation result dictionaries

**Returns:** `Dict[str, Any]` - Summary dictionary with counts and error lists





---
