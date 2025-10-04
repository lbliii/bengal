---
title: "template_functions.crossref"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/crossref.py"
---

# template_functions.crossref

Cross-reference functions for templates.

Provides 4 functions for Sphinx-style cross-referencing with O(1) performance.

**Source:** `../../bengal/rendering/template_functions/crossref.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register cross-reference functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### ref

```python
def ref(path: str, index: dict, text: str = None) -> Markup
```

Generate cross-reference link (like Sphinx :doc: or :ref:).

O(1) lookup - zero performance impact!

**Parameters:**

- **path** (`str`) - Path to reference ('docs/installation', 'id:my-page', or slug)
- **index** (`dict`) - Cross-reference index from site
- **text** (`str`) = `None` - Optional custom link text (defaults to page title)

**Returns:** `Markup` - Safe HTML link or broken reference indicator


**Examples:**

In templates:




---
### doc

```python
def doc(path: str, index: dict) -> Optional['Page']
```

Get page object by path (like Hugo's .GetPage).

O(1) lookup - zero performance impact!
Useful for accessing page metadata in templates.

**Parameters:**

- **path** (`str`) - Path to page ('docs/installation', 'id:my-page', or slug)
- **index** (`dict`) - Cross-reference index from site

**Returns:** `Optional['Page']` - Page object or None if not found


**Examples:**

{% set install_page = doc('docs/installation') %}




---
### anchor

```python
def anchor(heading: str, index: dict, page_path: str = None) -> Markup
```

Link to a heading (anchor) in a page.

**Parameters:**

- **heading** (`str`) - Heading text to link to
- **index** (`dict`) - Cross-reference index from site
- **page_path** (`str`) = `None` - Optional page path to restrict search (default: search all)

**Returns:** `Markup` - Safe HTML link to heading or broken reference indicator


**Examples:**

{{ anchor('Installation') }}




---
### relref

```python
def relref(path: str, index: dict) -> str
```

Get relative URL for a page (Hugo-style relref).

Returns just the URL without generating a full link.
Useful for custom link generation.

**Parameters:**

- **path** (`str`) - Path to page
- **index** (`dict`) - Cross-reference index from site

**Returns:** `str` - URL string or empty string if not found


**Examples:**

<a href="{{ relref('docs/api') }}" class="btn">API Docs</a>




---
