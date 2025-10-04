---
title: "template_functions.advanced_strings"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/advanced_strings.py"
---

# template_functions.advanced_strings

Advanced string manipulation functions for templates.

Provides 5 advanced string transformation functions.

**Source:** `../../bengal/rendering/template_functions/advanced_strings.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register advanced string functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### camelize

```python
def camelize(text: str) -> str
```

Convert string to camelCase.

**Parameters:**

- **text** (`str`) - Text to convert

**Returns:** `str` - camelCase text


**Examples:**

{{ "hello_world" | camelize }}  # "helloWorld"




---
### underscore

```python
def underscore(text: str) -> str
```

Convert string to snake_case.

**Parameters:**

- **text** (`str`) - Text to convert

**Returns:** `str` - snake_case text


**Examples:**

{{ "helloWorld" | underscore }}  # "hello_world"




---
### titleize

```python
def titleize(text: str) -> str
```

Convert string to Title Case (proper title capitalization).

More sophisticated than str.title() - handles articles, conjunctions,
and prepositions correctly.

**Parameters:**

- **text** (`str`) - Text to convert

**Returns:** `str` - Properly title-cased text


**Examples:**

{{ "the lord of the rings" | titleize }}




---
### wrap_text

```python
def wrap_text(text: str, width: int = 80) -> str
```

Wrap text to specified width.

**Parameters:**

- **text** (`str`) - Text to wrap
- **width** (`int`) = `80` - Maximum line width (default: 80)

**Returns:** `str` - Wrapped text with newlines


**Examples:**

{{ long_text | wrap(60) }}




---
### indent_text

```python
def indent_text(text: str, spaces: int = 4, first_line: bool = True) -> str
```

Indent text by specified number of spaces.

**Parameters:**

- **text** (`str`) - Text to indent
- **spaces** (`int`) = `4` - Number of spaces to indent (default: 4)
- **first_line** (`bool`) = `True` - Indent first line too (default: True)

**Returns:** `str` - Indented text


**Examples:**

{{ code | indent(2) }}




---
