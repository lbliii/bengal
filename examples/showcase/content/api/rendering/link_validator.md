---
title: "rendering.link_validator"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/link_validator.py"
---

# rendering.link_validator

Link validation for catching broken links.

**Source:** `../../bengal/rendering/link_validator.py`

---

## Classes

### LinkValidator


Validates links in pages to catch broken links.




**Methods:**

#### __init__

```python
def __init__(self) -> None
```

Initialize the link validator.

**Parameters:**

- **self**

**Returns:** `None`






---
#### validate_page_links

```python
def validate_page_links(self, page: Page) -> List[str]
```

Validate all links in a page.

**Parameters:**

- **self**
- **page** (`Page`) - Page to validate

**Returns:** `List[str]` - List of broken link URLs






---
#### validate_site

```python
def validate_site(self, site: Any) -> List[tuple]
```

Validate all links in the entire site.

**Parameters:**

- **self**
- **site** (`Any`) - Site instance

**Returns:** `List[tuple]` - List of (page_path, broken_link) tuples






---


