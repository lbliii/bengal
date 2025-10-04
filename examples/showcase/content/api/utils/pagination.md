---
title: "utils.pagination"
layout: api-reference
type: python-module
source_file: "../../bengal/utils/pagination.py"
---

# utils.pagination

Pagination utility for splitting long lists into pages.

**Source:** `../../bengal/utils/pagination.py`

---

## Classes

### Paginator

**Inherits from:** `Generic[T]`
Paginator for splitting a list of items into pages.

Usage:
    paginator = Paginator(posts, per_page=10)
    page = paginator.page(1)  # Get first page
    
Attributes:
    items: List of items to paginate
    per_page: Number of items per page
    num_pages: Total number of pages




**Methods:**

#### __init__

```python
def __init__(self, items: List[T], per_page: int = 10) -> None
```

Initialize the paginator.

**Parameters:**

- **self**
- **items** (`List[T]`) - List of items to paginate
- **per_page** (`int`) = `10` - Number of items per page (default: 10)

**Returns:** `None`






---
#### page

```python
def page(self, number: int) -> List[T]
```

Get items for a specific page.

**Parameters:**

- **self**
- **number** (`int`) - Page number (1-indexed)

**Returns:** `List[T]` - List of items for that page

**Raises:**

- **ValueError**: If page number is out of range





---
#### page_context

```python
def page_context(self, page_number: int, base_url: str) -> Dict[str, Any]
```

Get template context for a specific page.

**Parameters:**

- **self**
- **page_number** (`int`) - Current page number (1-indexed)
- **base_url** (`str`) - Base URL for pagination links (e.g., '/posts/')

**Returns:** `Dict[str, Any]` - Dictionary with pagination context for templates






---
#### __repr__

```python
def __repr__(self) -> str
```

*No description provided.*

**Parameters:**

- **self**

**Returns:** `str`






---


