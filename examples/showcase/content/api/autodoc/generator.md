
---
title: "autodoc.generator"
type: python-module
source_file: "bengal/autodoc/generator.py"
css_class: api-content
description: "Documentation generator - renders DocElements to markdown using templates."
---

# autodoc.generator

Documentation generator - renders DocElements to markdown using templates.

---

## Classes

### `TemplateCache`


Cache rendered templates for performance.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self)
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**





---
#### `get_cache_key`
```python
def get_cache_key(self, template_name: str, element: DocElement) -> str
```

Generate cache key from template + data.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`template_name`** (`str`)
- **`element`** (`DocElement`)

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
#### `get`
```python
def get(self, key: str) -> str | None
```

Get cached rendered template.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`key`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`str | None`




---
#### `set`
```python
def set(self, key: str, rendered: str)
```

Cache rendered template.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`key`** (`str`)
- **`rendered`** (`str`)





---

### `DocumentationGenerator`


Generate documentation from DocElements using templates.

Features:
- Template hierarchy (user templates override built-in)
- Template caching for performance
- Parallel generation
- Progress tracking




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, extractor: Extractor, config: dict[str, Any], template_cache: TemplateCache | None = None, max_workers: int | None = None)
```

Initialize generator.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `extractor` | `Extractor` | - | Extractor instance for this doc type |
| `config` | `dict[str, Any]` | - | Configuration dict |
| `template_cache` | `TemplateCache | None` | `None` | Optional template cache |
| `max_workers` | `int | None` | `None` | Max parallel workers (None = auto-detect) |





---
#### `generate_all`
```python
def generate_all(self, elements: list[DocElement], output_dir: Path, parallel: bool = True) -> list[Path]
```

Generate documentation for all elements.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`elements`** (`list[DocElement]`) - List of elements to document
- **`output_dir`** (`Path`) - Output directory for markdown files
- **`parallel`** (`bool`) = `True` - Use parallel processing

:::{rubric} Returns
:class: rubric-returns
:::
`list[Path]` - List of generated file paths




---
#### `generate_single`
```python
def generate_single(self, element: DocElement, output_dir: Path) -> Path
```

Generate documentation for a single element.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`element`** (`DocElement`) - Element to document
- **`output_dir`** (`Path`) - Output directory

:::{rubric} Returns
:class: rubric-returns
:::
`Path` - Path to generated file




---
