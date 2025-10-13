
---
title: "autodoc.utils"
type: python-module
source_file: "bengal/autodoc/utils.py"
css_class: api-content
description: "Utility functions for autodoc system.  Provides text sanitization and common helpers for all extractors."
---

# autodoc.utils

Utility functions for autodoc system.

Provides text sanitization and common helpers for all extractors.

---


## Functions

### `sanitize_text`
```python
def sanitize_text(text: str | None) -> str
```

Clean user-provided text for markdown generation.

This function is the single source of truth for text cleaning across
all autodoc extractors. It prevents common markdown rendering issues by:

- Removing leading/trailing whitespace
- Dedenting indented blocks (prevents accidental code blocks)
- Normalizing line endings
- Collapsing excessive blank lines



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`text`** (`str | None`) - Raw text from docstrings, help text, or API specs

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Cleaned text safe for markdown generation




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> text = '''
    ...     Indented docstring text.
    ...
    ...     More content here.
    ... '''
    >>> sanitize_text(text)
    'Indented docstring text.\n\nMore content here.'
```


---
### `truncate_text`
```python
def truncate_text(text: str, max_length: int = 200, suffix: str = '...') -> str
```

Truncate text to a maximum length, adding suffix if truncated.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`text`** (`str`) - Text to truncate
- **`max_length`** (`int`) = `200` - Maximum length (default: 200)
- **`suffix`** (`str`) = `'...'` - Suffix to add if truncated (default: '...')

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Truncated text




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> truncate_text('A very long description here', max_length=20)
    'A very long descr...'
```


---
