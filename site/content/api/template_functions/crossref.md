
---
title: "template_functions.crossref"
type: python-module
source_file: "bengal/rendering/template_functions/crossref.py"
css_class: api-content
description: "Cross-reference functions for templates.  Provides 4 functions for Sphinx-style cross-referencing with O(1) performance."
---

# template_functions.crossref

Cross-reference functions for templates.

Provides 4 functions for Sphinx-style cross-referencing with O(1) performance.

---


## Functions

### `register`
```python
def register(env: Environment, site: Site) -> None
```

Register cross-reference functions with Jinja2 environment.



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
* - `env`
  - `Environment`
  - -
  - -
* - `site`
  - `Site`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `ref`
```python
def ref(path: str, index: dict, text: str | None = None) -> Markup
```

Generate cross-reference link (like Sphinx :doc: or :ref:).

O(1) lookup - zero performance impact!



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
* - `path`
  - `str`
  - -
  - Path to reference ('docs/installation', 'id:my-page', or slug)
* - `index`
  - `dict`
  - -
  - Cross-reference index from site
* - `text`
  - `str | None`
  - `None`
  - Optional custom link text (defaults to page title)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Markup` - Safe HTML link or broken reference indicator




:::{rubric} Examples
:class: rubric-examples
:::
```python
In templates:
```


---
### `doc`
```python
def doc(path: str, index: dict) -> Page | None
```

Get page object by path (like Hugo's .GetPage).

O(1) lookup - zero performance impact!
Useful for accessing page metadata in templates.



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
* - `path`
  - `str`
  - -
  - Path to page ('docs/installation', 'id:my-page', or slug)
* - `index`
  - `dict`
  - -
  - Cross-reference index from site
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Page | None` - Page object or None if not found




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set install_page = doc('docs/installation') %}
```


---
### `anchor`
```python
def anchor(heading: str, index: dict, page_path: str | None = None) -> Markup
```

Link to a heading (anchor) in a page.



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
* - `heading`
  - `str`
  - -
  - Heading text to link to
* - `index`
  - `dict`
  - -
  - Cross-reference index from site
* - `page_path`
  - `str | None`
  - `None`
  - Optional page path to restrict search (default: search all)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`Markup` - Safe HTML link to heading or broken reference indicator




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ anchor('Installation') }}
```


---
### `relref`
```python
def relref(path: str, index: dict) -> str
```

Get relative URL for a page (Hugo-style relref).

Returns just the URL without generating a full link.
Useful for custom link generation.



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
* - `path`
  - `str`
  - -
  - Path to page
* - `index`
  - `dict`
  - -
  - Cross-reference index from site
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - URL string or empty string if not found




:::{rubric} Examples
:class: rubric-examples
:::
```python
<a href="{{ relref('docs/api') }}" class="btn">API Docs</a>
```


---
