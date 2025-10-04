---
title: "autodoc.docstring_parser"
layout: api-reference
type: python-module
source_file: "../../bengal/autodoc/docstring_parser.py"
---

# autodoc.docstring_parser

Docstring parsers for different styles.

Supports:
- Google style (Args:, Returns:, Raises:, Example:)
- NumPy style (Parameters, Returns, Raises, Examples with --------)
- Sphinx style (:param name:, :returns:, :raises:)

**Source:** `../../bengal/autodoc/docstring_parser.py`

---

## Classes

### ParsedDocstring


Container for parsed docstring data.




**Methods:**

#### __init__

```python
def __init__(self)
```

*No description provided.*

**Parameters:**

- **self**







---
#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert to dictionary.

**Parameters:**

- **self**

**Returns:** `Dict[str, Any]`






---

### GoogleDocstringParser


Parse Google-style docstrings.




**Methods:**

#### parse

```python
def parse(self, docstring: str) -> ParsedDocstring
```

Parse Google-style docstring.

**Parameters:**

- **self**
- **docstring** (`str`)

**Returns:** `ParsedDocstring`






---

### NumpyDocstringParser


Parse NumPy-style docstrings.




**Methods:**

#### parse

```python
def parse(self, docstring: str) -> ParsedDocstring
```

Parse NumPy-style docstring.

**Parameters:**

- **self**
- **docstring** (`str`)

**Returns:** `ParsedDocstring`






---

### SphinxDocstringParser


Parse Sphinx-style docstrings.




**Methods:**

#### parse

```python
def parse(self, docstring: str) -> ParsedDocstring
```

Parse Sphinx-style docstring.

**Parameters:**

- **self**
- **docstring** (`str`)

**Returns:** `ParsedDocstring`






---


## Functions

### parse_docstring

```python
def parse_docstring(docstring: Optional[str], style: str = 'auto') -> ParsedDocstring
```

Parse docstring and extract structured information.

**Parameters:**

- **docstring** (`Optional[str]`) - Raw docstring text
- **style** (`str`) = `'auto'` - Docstring style ('auto', 'google', 'numpy', 'sphinx')

**Returns:** `ParsedDocstring` - ParsedDocstring object with extracted information





---
### detect_docstring_style

```python
def detect_docstring_style(docstring: str) -> str
```

Auto-detect docstring style.

**Parameters:**

- **docstring** (`str`) - Raw docstring text

**Returns:** `str` - Style name ('google', 'numpy', 'sphinx', or 'plain')





---
