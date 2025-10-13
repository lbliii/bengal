
---
title: "discovery.content_discovery"
type: python-module
source_file: "bengal/discovery/content_discovery.py"
css_class: api-content
description: "Content discovery - finds and organizes pages and sections."
---

# discovery.content_discovery

Content discovery - finds and organizes pages and sections.

---

## Classes

### `ContentDiscovery`


Discovers and organizes content files into pages and sections.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, content_dir: Path, site: Any | None = None) -> None
```

Initialize content discovery.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content_dir`** (`Path`) - Root content directory
- **`site`** (`Any | None`) = `None`

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `discover`
```python
def discover(self) -> tuple[list[Section], list[Page]]
```

Discover all content in the content directory.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`tuple[list[Section], list[Page]]` - Tuple of (sections, pages)




---
