
---
title: "generator"
type: "python-module"
source_file: "bengal/bengal/autodoc/generator.py"
line_number: 1
description: "Documentation generator - renders DocElements to markdown using templates."
---

# generator
**Type:** Module
**Source:** [View source](bengal/bengal/autodoc/generator.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[autodoc](/api/bengal/autodoc/) ›generator

Documentation generator - renders DocElements to markdown using templates.

## Classes




### `TemplateCache`


Cache rendered templates for performance with intelligent invalidation.









## Methods



#### `__init__`
```python
def __init__(self, max_size: int = DEFAULT_CACHE_SIZE)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `max_size` | `int` | `DEFAULT_CACHE_SIZE` | *No description provided.* |








#### `get_cache_key`
```python
def get_cache_key(self, template_name: str, element: DocElement) -> str
```


Generate cache key from template + data.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | *No description provided.* |
| `element` | `DocElement` | - | *No description provided.* |







**Returns**


`str`



#### `get`
```python
def get(self, key: str) -> str | None
```


Get cached rendered template.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |







**Returns**


`str | None`



#### `set`
```python
def set(self, key: str, rendered: str) -> None
```


Cache rendered template with LRU eviction.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |
| `rendered` | `str` | - | *No description provided.* |







**Returns**


`None`




#### `clear`
```python
def clear(self) -> None
```


Clear all cached content.



**Returns**


`None`



#### `get_stats`
```python
def get_stats(self) -> dict[str, Any]
```


Get cache statistics.



**Returns**


`dict[str, Any]`




### `DocumentationGenerator`


Generate documentation from DocElements using templates.

Features:
- Template hierarchy (user templates override built-in)
- Template caching for performance
- Parallel generation
- Progress tracking









## Methods



#### `__init__`
```python
def __init__(self, extractor: Extractor, config: dict[str, Any], template_cache: TemplateCache | None = None, max_workers: int | None = None)
```


Initialize generator.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `extractor` | `Extractor` | - | Extractor instance for this doc type |
| `config` | `dict[str, Any]` | - | Configuration dict |
| `template_cache` | `TemplateCache \| None` | - | Optional template cache |
| `max_workers` | `int \| None` | - | Max parallel workers (None = auto-detect) |



















#### `generate_all`
```python
def generate_all(self, elements: list[DocElement], output_dir: Path, parallel: bool = True) -> list[Path]
```


Generate documentation for all elements.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `elements` | `list[DocElement]` | - | List of elements to document |
| `output_dir` | `Path` | - | Output directory for markdown files |
| `parallel` | `bool` | `True` | Use parallel processing |







**Returns**


`list[Path]` - List of generated file paths





#### `generate_single`
```python
def generate_single(self, element: DocElement, output_dir: Path) -> Path
```


Generate documentation for a single element.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `element` | `DocElement` | - | Element to document |
| `output_dir` | `Path` | - | Output directory |







**Returns**


`Path` - Path to generated file






#### `get_error_report`
```python
def get_error_report(self) -> str
```


Get comprehensive error report from template rendering.



**Returns**


`str`



#### `get_detailed_error_report`
```python
def get_detailed_error_report(self) -> str
```


Get detailed error report for debugging.



**Returns**


`str`



#### `has_template_errors`
```python
def has_template_errors(self) -> bool
```


Check if any template errors occurred during generation.



**Returns**


`bool`



#### `clear_errors`
```python
def clear_errors(self) -> None
```


Clear all recorded template errors.



**Returns**


`None`



#### `get_template_config`
```python
def get_template_config(self) -> dict[str, Any]
```


Get current template configuration for debugging.



**Returns**


`dict[str, Any]`



#### `export_error_report`
```python
def export_error_report(self, output_path: Path) -> None
```


Export comprehensive error report to file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_path` | `Path` | - | Path to write the error report |







**Returns**


`None`



#### `validate_template_syntax`
```python
def validate_template_syntax(self, template_name: str) -> list[str]
```


Validate a specific template for syntax issues.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | Name of template to validate |







**Returns**


`list[str]` - List of validation issues (empty if valid)



#### `reload_templates`
```python
def reload_templates(self) -> None
```


Reload template environment and clear caches.
Useful for development with hot-reloading.



**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/autodoc/generator.py`*

