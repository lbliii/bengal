---
title: "autodoc.generator"
layout: api-reference
type: python-module
source_file: "../../bengal/autodoc/generator.py"
---

# autodoc.generator

Documentation generator - renders DocElements to markdown using templates.

**Source:** `../../bengal/autodoc/generator.py`

---

## Classes

### TemplateCache


Cache rendered templates for performance.




**Methods:**

#### __init__

```python
def __init__(self)
```

*No description provided.*

**Parameters:**

- **self**







---
#### get_cache_key

```python
def get_cache_key(self, template_name: str, element: DocElement) -> str
```

Generate cache key from template + data.

**Parameters:**

- **self**
- **template_name** (`str`)
- **element** (`DocElement`)

**Returns:** `str`






---
#### get

```python
def get(self, key: str) -> Optional[str]
```

Get cached rendered template.

**Parameters:**

- **self**
- **key** (`str`)

**Returns:** `Optional[str]`






---
#### set

```python
def set(self, key: str, rendered: str)
```

Cache rendered template.

**Parameters:**

- **self**
- **key** (`str`)
- **rendered** (`str`)







---

### DocumentationGenerator


Generate documentation from DocElements using templates.

Features:
- Template hierarchy (user templates override built-in)
- Template caching for performance
- Parallel generation
- Progress tracking




**Methods:**

#### __init__

```python
def __init__(self, extractor: Extractor, config: Dict[str, Any], template_cache: Optional[TemplateCache] = None, max_workers: Optional[int] = None)
```

Initialize generator.

**Parameters:**

- **self**
- **extractor** (`Extractor`) - Extractor instance for this doc type
- **config** (`Dict[str, Any]`) - Configuration dict
- **template_cache** (`Optional[TemplateCache]`) = `None` - Optional template cache
- **max_workers** (`Optional[int]`) = `None` - Max parallel workers (None = auto-detect)







---
#### generate_all

```python
def generate_all(self, elements: List[DocElement], output_dir: Path, parallel: bool = True) -> List[Path]
```

Generate documentation for all elements.

**Parameters:**

- **self**
- **elements** (`List[DocElement]`) - List of elements to document
- **output_dir** (`Path`) - Output directory for markdown files
- **parallel** (`bool`) = `True` - Use parallel processing

**Returns:** `List[Path]` - List of generated file paths






---
#### generate_single

```python
def generate_single(self, element: DocElement, output_dir: Path) -> Path
```

Generate documentation for a single element.

**Parameters:**

- **self**
- **element** (`DocElement`) - Element to document
- **output_dir** (`Path`) - Output directory

**Returns:** `Path` - Path to generated file






---


