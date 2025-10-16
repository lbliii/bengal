
---
title: "parsers.factory"
type: python-module
source_file: "bengal/rendering/parsers/factory.py"
css_class: api-content
description: "HTML parser factory for Bengal.  Returns NativeHTMLParser, optimized for build-time validation and health checks. Replaced BeautifulSoup4 for performance (~5-10x faster for text extraction)."
---

# parsers.factory

HTML parser factory for Bengal.

Returns NativeHTMLParser, optimized for build-time validation and health checks.
Replaced BeautifulSoup4 for performance (~5-10x faster for text extraction).

---

## Classes

### `ParserBackend`


HTML parser backend identifiers.





### `ParserFactory`


Factory for HTML parsers used in Bengal.

Currently returns NativeHTMLParser, which is optimized for build-time
validation and health checks. Replaced BeautifulSoup4 for performance
(~5-10x faster for text extraction).




:::{rubric} Methods
:class: rubric-methods
:::
#### `get_html_parser` @staticmethod
```python
def get_html_parser(backend: str | None = None) -> callable
```

Get HTML parser for build-time validation and health checks.



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
* - `backend`
  - `str | None`
  - `None`
  - Parser backend (currently only 'native' supported)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`callable` - Parser callable that returns NativeHTMLParser instance




:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> parser_fn = ParserFactory.get_html_parser()
    >>> result = parser_fn("<p>Text</p>")
    >>> text = result.get_text()
```


---
#### `get_parser_features` @staticmethod
```python
def get_parser_features(backend: str) -> dict
```

Get features/capabilities for a backend.



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
* - `backend`
  - `str`
  - -
  - Parser backend identifier
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict` - Dictionary of parser features




---
