
---
title: "rendering.link_validator"
type: python-module
source_file: "bengal/rendering/link_validator.py"
css_class: api-content
description: "Link validation for catching broken links."
---

# rendering.link_validator

Link validation for catching broken links.

---

## Classes

### `LinkValidator`


Validates links in pages to catch broken links.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self) -> None
```

Initialize the link validator.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `validate_page_links`
```python
def validate_page_links(self, page: Page) -> list[str]
```

Validate all links in a page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page`** (`Page`) - Page to validate

:::{rubric} Returns
:class: rubric-returns
:::
`list[str]` - List of broken link URLs




---
#### `validate_site`
```python
def validate_site(self, site: Any) -> list[tuple]
```

Validate all links in the entire site.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`Any`) - Site instance

:::{rubric} Returns
:class: rubric-returns
:::
`list[tuple]` - List of (page_path, broken_link) tuples




---
