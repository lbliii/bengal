---
title: "orchestration.content"
layout: api-reference
type: python-module
source_file: "../../bengal/orchestration/content.py"
---

# orchestration.content

Content discovery and setup orchestration for Bengal SSG.

Handles content and asset discovery, page/section reference setup,
and cascading frontmatter.

**Source:** `../../bengal/orchestration/content.py`

---

## Classes

### ContentOrchestrator


Handles content and asset discovery.

Responsibilities:
    - Discover content (pages and sections)
    - Discover assets (site and theme)
    - Set up page/section references for navigation
    - Apply cascading frontmatter from sections to pages




**Methods:**

#### __init__

```python
def __init__(self, site: 'Site')
```

Initialize content orchestrator.

**Parameters:**

- **self**
- **site** (`'Site'`) - Site instance to populate with content







---
#### discover

```python
def discover(self) -> None
```

Discover all content and assets.
Main entry point called during build.

**Parameters:**

- **self**

**Returns:** `None`






---
#### discover_content

```python
def discover_content(self, content_dir: Optional[Path] = None) -> None
```

Discover all content (pages, sections) in the content directory.

**Parameters:**

- **self**
- **content_dir** (`Optional[Path]`) = `None` - Content directory path (defaults to root_path/content)

**Returns:** `None`






---
#### discover_assets

```python
def discover_assets(self, assets_dir: Optional[Path] = None) -> None
```

Discover all assets in the assets directory and theme assets.

**Parameters:**

- **self**
- **assets_dir** (`Optional[Path]`) = `None` - Assets directory path (defaults to root_path/assets)

**Returns:** `None`






---


