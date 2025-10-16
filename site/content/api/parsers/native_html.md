
---
title: "parsers.native_html"
type: python-module
source_file: "bengal/rendering/parsers/native_html.py"
css_class: api-content
description: "Native HTML parser for build-time validation and health checks.  This parser is used during `bengal build` for: - Health check validation (detecting unrendered directives, Jinja templates) - Text e..."
---

# parsers.native_html

Native HTML parser for build-time validation and health checks.

This parser is used during `bengal build` for:
- Health check validation (detecting unrendered directives, Jinja templates)
- Text extraction from rendered HTML (excluding code blocks)
- Performance-optimized alternative to BeautifulSoup4

Design:
- Uses Python's stdlib html.parser (fast, zero dependencies)
- Tracks state for code/script/style blocks to exclude from text extraction
- Optimized for build-time validation, not complex DOM manipulation

Performance:
- ~5-10x faster than BeautifulSoup4 for text extraction
- Suitable for high-volume build-time validation

---

## Classes

### `NativeHTMLParser`

**Inherits from:** `HTMLParser`
Fast HTML parser for build-time validation and text extraction.

This parser is the production parser used during `bengal build` for health
checks and validation. It's optimized for speed over features, using Python's
stdlib html.parser without external dependencies.

**Primary use cases:**
- Health check validation (unrendered directives, Jinja templates)
- Text extraction for search indexing
- Link validation and content analysis

**Performance:**
- ~5-10x faster than BeautifulSoup4 for text extraction
- Zero external dependencies (uses stdlib only)

**Example:**
    >>> parser = NativeHTMLParser()
    >>> result = parser.feed("<p>Hello <code>world</code></p>")
    >>> result.get_text()
    'Hello'  # Code block excluded




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

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::




---
#### `handle_starttag`
```python
def handle_starttag(self, tag: str, attrs: list) -> None
```

Handle opening tags.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `tag`
  - `str`
  - -
  - -
* - `attrs`
  - `list`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `handle_endtag`
```python
def handle_endtag(self, tag: str) -> None
```

Handle closing tags.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `tag`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `handle_data`
```python
def handle_data(self, data: str) -> None
```

Handle text data.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `data`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `feed`
```python
def feed(self, data: str) -> 'NativeHTMLParser'
```

Parse HTML content and return self for chaining.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `data`
  - `str`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'NativeHTMLParser'` - self to allow parser(html).get_text() pattern




---
#### `get_text`
```python
def get_text(self) -> str
```

Get extracted text content (excluding code/script/style blocks).



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Text content with whitespace normalized




---
#### `reset`
```python
def reset(self) -> None
```

Reset parser state for reuse.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
