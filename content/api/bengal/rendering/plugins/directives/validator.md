
---
title: "validator"
type: "python-module"
source_file: "../bengal/bengal/rendering/plugins/directives/validator.py"
line_number: 1
description: "Pre-parse validation for directives. Validates directive syntax before parsing to catch errors early with helpful messages."
---

# validator
**Type:** Module
**Source:** [View source](../bengal/bengal/rendering/plugins/directives/validator.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[plugins](/api/bengal/rendering/plugins/) ›[directives](/api/bengal/rendering/plugins/directives/) ›validator

Pre-parse validation for directives.

Validates directive syntax before parsing to catch errors early with
helpful messages.

## Classes




### `DirectiveSyntaxValidator`


Validates directive syntax before parsing.

Catches common errors early with helpful messages before expensive
parsing and recursive markdown processing.









## Methods



#### `validate_tabs_directive` @staticmethod
```python
def validate_tabs_directive(content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```


Validate tabs directive content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Directive content (between opening and closing backticks) |
| `file_path` | `Path \| None` | - | Optional file path for error messages |
| `line_number` | `int \| None` | - | Optional line number for error messages |







**Returns**


`list[str]` - List of validation error messages (empty if valid)



#### `validate_code_tabs_directive` @staticmethod
```python
def validate_code_tabs_directive(content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```


Validate code-tabs directive content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Directive content |
| `file_path` | `Path \| None` | - | Optional file path |
| `line_number` | `int \| None` | - | Optional line number |







**Returns**


`list[str]` - List of validation errors



#### `validate_dropdown_directive` @staticmethod
```python
def validate_dropdown_directive(content: str, title: str = '', file_path: Path | None = None, line_number: int | None = None) -> list[str]
```


Validate dropdown directive content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Directive content |
| `title` | `str` | `''` | Directive title |
| `file_path` | `Path \| None` | - | Optional file path |
| `line_number` | `int \| None` | - | Optional line number |







**Returns**


`list[str]` - List of validation errors



#### `validate_admonition_directive` @staticmethod
```python
def validate_admonition_directive(admon_type: str, content: str, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```


Validate admonition directive content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `admon_type` | `str` | - | Type of admonition (note, tip, warning, etc.) |
| `content` | `str` | - | Directive content |
| `file_path` | `Path \| None` | - | Optional file path |
| `line_number` | `int \| None` | - | Optional line number |







**Returns**


`list[str]` - List of validation errors



#### `validate_nested_fences` @staticmethod
```python
def validate_nested_fences(content: str, file_path: Path | None = None) -> list[str]
```


Validate nested fence usage (colon fences).

Checks for:
1. Unclosed fences
2. Mismatched closing fence lengths
3. Nested directives using same fence length as parent (ambiguous)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Markdown content |
| `file_path` | `Path \| None` | - | Optional file path |







**Returns**


`list[str]` - List of error/warning messages



#### `validate_directive` @classmethod
```python
def validate_directive(cls, directive_type: str, content: str, title: str = '', options: dict[str, Any] | None = None, file_path: Path | None = None, line_number: int | None = None) -> list[str]
```


Validate any directive type.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive_type` | `str` | - | Type of directive (tabs, note, dropdown, etc.) |
| `content` | `str` | - | Directive content |
| `title` | `str` | `''` | Directive title (if any) |
| `options` | `dict[str, Any] \| None` | - | Directive options dictionary |
| `file_path` | `Path \| None` | - | Optional file path |
| `line_number` | `int \| None` | - | Optional line number |







**Returns**


`list[str]` - List of validation errors (empty if valid)



#### `validate_directive_block` @classmethod
```python
def validate_directive_block(cls, directive_block: str, file_path: Path | None = None, start_line: int | None = None) -> dict[str, Any]
```


Validate a complete directive block from markdown.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `directive_block` | `str` | - | Full directive block including opening/closing backticks |
| `file_path` | `Path \| None` | - | Optional file path |
| `start_line` | `int \| None` | - | Optional starting line number |







**Returns**


`dict[str, Any]` - Dictionary with validation results:
    {
        'valid': bool,
        'errors': List[str],
        'directive_type': str,
        'content': str,
        'title': str,
        'options': Dict[str, Any]
    }

## Functions



### `validate_markdown_directives`


```python
def validate_markdown_directives(markdown_content: str, file_path: Path | None = None) -> list[dict[str, Any]]
```



Validate all directive blocks in a markdown file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `markdown_content` | `str` | - | Full markdown content |
| `file_path` | `Path \| None` | - | Optional file path for error reporting |







**Returns**


`list[dict[str, Any]]` - List of validation results, one per directive block




### `get_directive_validation_summary`


```python
def get_directive_validation_summary(validation_results: list[dict[str, Any]]) -> dict[str, Any]
```



Get a summary of directive validation results.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `validation_results` | `list[dict[str, Any]]` | - | List of validation result dictionaries |







**Returns**


`dict[str, Any]` - Summary dictionary with counts and error lists



---
*Generated by Bengal autodoc from `../bengal/bengal/rendering/plugins/directives/validator.py`*
