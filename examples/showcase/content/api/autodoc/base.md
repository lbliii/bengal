---
title: "autodoc.base"
layout: api-reference
type: python-module
source_file: "../../bengal/autodoc/base.py"
---

# autodoc.base

Base classes for autodoc system.

Provides common interfaces for all documentation extractors.

**Source:** `../../bengal/autodoc/base.py`

---

## Classes

### DocElement


Represents a documented element (function, class, endpoint, command, etc.).

This is the unified data model used by all extractors.
Each extractor converts its specific domain into this common format.

Attributes:
    name: Element name (e.g., 'build', 'Site', 'GET /users')
    qualified_name: Full path (e.g., 'bengal.core.site.Site.build')
    description: Main description/docstring
    element_type: Type of element ('function', 'class', 'endpoint', 'command', etc.)
    source_file: Source file path (if applicable)
    line_number: Line number in source (if applicable)
    metadata: Type-specific data (signatures, parameters, etc.)
    children: Nested elements (methods, subcommands, etc.)
    examples: Usage examples
    see_also: Cross-references to related elements
    deprecated: Deprecation notice (if any)

::: info
This is a dataclass.
:::

**Attributes:**

- **name** (`str`)- **qualified_name** (`str`)- **description** (`str`)- **element_type** (`str`)- **source_file** (`Optional[Path]`)- **line_number** (`Optional[int]`)- **metadata** (`Dict[str, Any]`)- **children** (`List['DocElement']`)- **examples** (`List[str]`)- **see_also** (`List[str]`)- **deprecated** (`Optional[str]`)

**Methods:**

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert to dictionary for caching/serialization.

**Parameters:**

- **self**

**Returns:** `Dict[str, Any]`






---
#### from_dict

```python
def from_dict(cls, data: Dict[str, Any]) -> 'DocElement'
```

Create from dictionary (for cache loading).

**Parameters:**

- **cls**
- **data** (`Dict[str, Any]`)

**Returns:** `'DocElement'`






---

### Extractor

**Inherits from:** `ABC`
Base class for all documentation extractors.

Each documentation type (Python, OpenAPI, CLI) implements this interface.
This enables a unified API for generating documentation from different sources.




**Methods:**

#### extract

```python
def extract(self, source: Any) -> List[DocElement]
```

Extract documentation elements from source.

**Parameters:**

- **self**
- **source** (`Any`) - Source to extract from (Path for files, dict for specs, etc.)

**Returns:** `List[DocElement]` - List of DocElement objects representing the documentation structure






---
#### get_template_dir

```python
def get_template_dir(self) -> str
```

Get template directory name for this extractor.

**Parameters:**

- **self**

**Returns:** `str` - Directory name (e.g., 'python', 'openapi', 'cli')


**Examples:**

Templates will be loaded from:





---
#### get_output_path

```python
def get_output_path(self, element: DocElement) -> Path
```

Determine output path for an element.

**Parameters:**

- **self**
- **element** (`DocElement`) - Element to generate path for

**Returns:** `Path` - Relative path for the generated markdown file


**Examples:**

For Python: bengal.core.site.Site → bengal/core/site.md





---


