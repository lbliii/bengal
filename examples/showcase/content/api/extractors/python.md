---
title: "extractors.python"
layout: api-reference
type: python-module
source_file: "../../bengal/autodoc/extractors/python.py"
---

# extractors.python

Python API documentation extractor.

Extracts documentation from Python source files via AST parsing.
No imports required - fast and reliable.

**Source:** `../../bengal/autodoc/extractors/python.py`

---

## Classes

### PythonExtractor

**Inherits from:** `Extractor`
Extract Python API documentation via AST parsing.

Features:
- No imports (AST-only) - fast and reliable
- Extracts modules, classes, functions, methods
- Type hint support
- Docstring extraction
- Signature building

Performance:
- ~0.1-0.5s per file
- No dependencies loaded
- No side effects




**Methods:**

#### __init__

```python
def __init__(self, exclude_patterns: Optional[List[str]] = None)
```

Initialize extractor.

**Parameters:**

- **self**
- **exclude_patterns** (`Optional[List[str]]`) = `None` - Glob patterns to exclude (e.g., "*/tests/*")







---
#### extract

```python
def extract(self, source: Path) -> List[DocElement]
```

Extract documentation from Python source.

**Parameters:**

- **self**
- **source** (`Path`) - Directory or file path

**Returns:** `List[DocElement]` - List of DocElement objects






---
#### get_template_dir

```python
def get_template_dir(self) -> str
```

Get template directory name.

**Parameters:**

- **self**

**Returns:** `str`






---
#### get_output_path

```python
def get_output_path(self, element: DocElement) -> Path
```

Get output path for element.

**Parameters:**

- **self**
- **element** (`DocElement`)

**Returns:** `Path`


**Examples:**

bengal.core.site (module) → bengal/core/site.md





---


