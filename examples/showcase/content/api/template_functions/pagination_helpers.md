---
title: "template_functions.pagination_helpers"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/pagination_helpers.py"
---

# template_functions.pagination_helpers

Pagination helper functions for templates.

Provides 3 functions for building pagination controls.

**Source:** `../../bengal/rendering/template_functions/pagination_helpers.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register pagination helper functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### paginate_items

```python
def paginate_items(items: List[Any], per_page: int = 10, current_page: int = 1) -> dict
```

Paginate a list of items.

**Parameters:**

- **items** (`List[Any]`) - List to paginate
- **per_page** (`int`) = `10` - Items per page (default: 10)
- **current_page** (`int`) = `1` - Current page number (1-indexed)

**Returns:** `dict` - Dictionary with pagination data


**Examples:**

{% set pagination = posts | paginate(10, current_page) %}




---
### page_url

```python
def page_url(base_path: str, page_num: int) -> str
```

Generate URL for a pagination page.

**Parameters:**

- **base_path** (`str`) - Base path (e.g., "/posts/")
- **page_num** (`int`) - Page number

**Returns:** `str` - URL for that page


**Examples:**

<a href="{{ page_url('/posts/', 2) }}">Page 2</a>




---
### page_range

```python
def page_range(current_page: int, total_pages: int, window: int = 2) -> List[Optional[int]]
```

Generate page range with ellipsis for pagination controls.

**Parameters:**

- **current_page** (`int`) - Current page number
- **total_pages** (`int`) - Total number of pages
- **window** (`int`) = `2` - Number of pages to show around current (default: 2)

**Returns:** `List[Optional[int]]` - List of page numbers with None for ellipsis


**Examples:**

{% for page_num in page_range(5, 20, window=2) %}




---
