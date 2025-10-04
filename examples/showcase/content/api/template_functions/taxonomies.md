---
title: "template_functions.taxonomies"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/taxonomies.py"
---

# template_functions.taxonomies

Taxonomy helper functions for templates.

Provides 4 functions for working with tags, categories, and related content.

**Source:** `../../bengal/rendering/template_functions/taxonomies.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register taxonomy helper functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### related_posts

```python
def related_posts(page: Any, all_pages: List[Any], limit: int = 5) -> List[Any]
```

Find related posts based on shared tags.

**Parameters:**

- **page** (`Any`) - Current page
- **all_pages** (`List[Any]`) - All site pages
- **limit** (`int`) = `5` - Maximum number of related posts

**Returns:** `List[Any]` - List of related pages sorted by relevance


**Examples:**

{% set related = related_posts(page, limit=3) %}




---
### popular_tags

```python
def popular_tags(tags_dict: Dict[str, List[Any]], limit: int = 10) -> List[tuple]
```

Get most popular tags sorted by count.

**Parameters:**

- **tags_dict** (`Dict[str, List[Any]]`) - Dictionary of tag -> pages
- **limit** (`int`) = `10` - Maximum number of tags

**Returns:** `List[tuple]` - List of (tag, count) tuples


**Examples:**

{% set top_tags = popular_tags(limit=5) %}




---
### tag_url

```python
def tag_url(tag: str) -> str
```

Generate URL for a tag page.

**Parameters:**

- **tag** (`str`) - Tag name

**Returns:** `str` - URL path to tag page


**Examples:**

<a href="{{ tag_url('python') }}">Python</a>




---
### has_tag

```python
def has_tag(page: Any, tag: str) -> bool
```

Check if page has a specific tag.

**Parameters:**

- **page** (`Any`) - Page to check
- **tag** (`str`) - Tag to look for

**Returns:** `bool` - True if page has the tag


**Examples:**

{% if page | has_tag('tutorial') %}




---
