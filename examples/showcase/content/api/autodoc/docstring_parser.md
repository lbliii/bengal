
---
title: "autodoc.docstring_parser"
type: python-module
source_file: "bengal/autodoc/docstring_parser.py"
css_class: api-content
description: "Docstring parsers for different styles.  Supports: - Google style (Args:, Returns:, Raises:, Example:) - NumPy style (Parameters, Returns, Raises, Examples with --------) - Sphinx style (:param nam..."
---

# autodoc.docstring_parser

Docstring parsers for different styles.

Supports:
- Google style (Args:, Returns:, Raises:, Example:)
- NumPy style (Parameters, Returns, Raises, Examples with --------)
- Sphinx style (:param name:, :returns:, :raises:)

---

## Classes

### `ParsedDocstring`


Container for parsed docstring data.




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
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

Convert to dictionary.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]`




---

### `GoogleDocstringParser`


Parse Google-style docstrings.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, docstring: str) -> ParsedDocstring
```

Parse Google-style docstring.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`docstring`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`ParsedDocstring`




---

### `NumpyDocstringParser`


Parse NumPy-style docstrings.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, docstring: str) -> ParsedDocstring
```

Parse NumPy-style docstring.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`docstring`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`ParsedDocstring`




---

### `SphinxDocstringParser`


Parse Sphinx-style docstrings.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, docstring: str) -> ParsedDocstring
```

Parse Sphinx-style docstring.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`docstring`** (`str`)

:::{rubric} Returns
:class: rubric-returns
:::
`ParsedDocstring`




---


## Functions

### `parse_docstring`
```python
def parse_docstring(docstring: str | None, style: str = 'auto') -> ParsedDocstring
```

Parse docstring and extract structured information.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`docstring`** (`str | None`) - Raw docstring text
- **`style`** (`str`) = `'auto'` - Docstring style ('auto', 'google', 'numpy', 'sphinx')

:::{rubric} Returns
:class: rubric-returns
:::
`ParsedDocstring` - ParsedDocstring object with extracted information




---
### `detect_docstring_style`
```python
def detect_docstring_style(docstring: str) -> str
```

Auto-detect docstring style.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`docstring`** (`str`) - Raw docstring text

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Style name ('google', 'numpy', 'sphinx', or 'plain')




---
