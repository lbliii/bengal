
---
title: "generator"
type: "python-module"
source_file: "bengal/autodoc/generator.py"
line_number: 1
description: "Documentation generator - renders DocElements to markdown using templates."
---

# generator
**Type:** Module
**Source:** [View source](bengal/autodoc/generator.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[autodoc](/api/bengal/autodoc/) ›generator

Documentation generator - renders DocElements to markdown using templates.

## Classes




### `TemplateCache`


Cache rendered templates for performance with intelligent invalidation.









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, max_size: int = DEFAULT_CACHE_SIZE)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `max_size` | `int` | `DEFAULT_CACHE_SIZE` | *No description provided.* |








#### `get_cache_key`

:::{div} api-badge-group
:::

```python
def get_cache_key(self, template_name: str, element: DocElement) -> str
```


Generate cache key from template + data.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | *No description provided.* |
| `element` | `DocElement` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`str`



#### `get`

:::{div} api-badge-group
:::

```python
def get(self, key: str) -> str | None
```


Get cached rendered template.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`str | None`



#### `set`

:::{div} api-badge-group
:::

```python
def set(self, key: str, rendered: str) -> None
```


Cache rendered template with LRU eviction.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | *No description provided.* |
| `rendered` | `str` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`




#### `clear`

:::{div} api-badge-group
:::

```python
def clear(self) -> None
```


Clear all cached content.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_stats`

:::{div} api-badge-group
:::

```python
def get_stats(self) -> dict[str, Any]
```


Get cache statistics.



:::{rubric} Returns
:class: rubric-returns
:::


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

:::{div} api-badge-group
:::

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

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`list[Path]` - List of generated file paths





#### `generate_single`

:::{div} api-badge-group
:::

```python
def generate_single(self, element: DocElement, output_dir: Path) -> Path
```


Generate documentation for a single element.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `element` | `DocElement` | - | Element to document |
| `output_dir` | `Path` | - | Output directory |







:::{rubric} Returns
:class: rubric-returns
:::


`Path` - Path to generated file






#### `get_error_report`

:::{div} api-badge-group
:::

```python
def get_error_report(self) -> str
```


Get comprehensive error report from template rendering.



:::{rubric} Returns
:class: rubric-returns
:::


`str`



#### `get_detailed_error_report`

:::{div} api-badge-group
:::

```python
def get_detailed_error_report(self) -> str
```


Get detailed error report for debugging.



:::{rubric} Returns
:class: rubric-returns
:::


`str`



#### `has_template_errors`

:::{div} api-badge-group
:::

```python
def has_template_errors(self) -> bool
```


Check if any template errors occurred during generation.



:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `clear_errors`

:::{div} api-badge-group
:::

```python
def clear_errors(self) -> None
```


Clear all recorded template errors.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_template_config`

:::{div} api-badge-group
:::

```python
def get_template_config(self) -> dict[str, Any]
```


Get current template configuration for debugging.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `export_error_report`

:::{div} api-badge-group
:::

```python
def export_error_report(self, output_path: Path) -> None
```


Export comprehensive error report to file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_path` | `Path` | - | Path to write the error report |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `validate_template_syntax`

:::{div} api-badge-group
:::

```python
def validate_template_syntax(self, template_name: str) -> list[str]
```


Validate a specific template for syntax issues.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_name` | `str` | - | Name of template to validate |







:::{rubric} Returns
:class: rubric-returns
:::


`list[str]` - List of validation issues (empty if valid)



#### `reload_templates`

:::{div} api-badge-group
:::

```python
def reload_templates(self) -> None
```


Reload template environment and clear caches.
Useful for development with hot-reloading.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



---
*Generated by Bengal autodoc from `bengal/autodoc/generator.py`*

