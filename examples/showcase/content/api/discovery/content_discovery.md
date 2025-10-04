---
title: "discovery.content_discovery"
layout: api-reference
type: python-module
source_file: "../../bengal/discovery/content_discovery.py"
---

# discovery.content_discovery

Content discovery - finds and organizes pages and sections.

**Source:** `../../bengal/discovery/content_discovery.py`

---

## Classes

### ContentDiscovery


Discovers and organizes content files into pages and sections.




**Methods:**

#### __init__

```python
def __init__(self, content_dir: Path) -> None
```

Initialize content discovery.

**Parameters:**

- **self**
- **content_dir** (`Path`) - Root content directory

**Returns:** `None`






---
#### discover

```python
def discover(self) -> Tuple[List[Section], List[Page]]
```

Discover all content in the content directory.

**Parameters:**

- **self**

**Returns:** `Tuple[List[Section], List[Page]]` - Tuple of (sections, pages)






---


