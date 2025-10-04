---
title: "discovery.asset_discovery"
layout: api-reference
type: python-module
source_file: "../../bengal/discovery/asset_discovery.py"
---

# discovery.asset_discovery

Asset discovery - finds and organizes static assets.

**Source:** `../../bengal/discovery/asset_discovery.py`

---

## Classes

### AssetDiscovery


Discovers static assets (images, CSS, JS, etc.).




**Methods:**

#### __init__

```python
def __init__(self, assets_dir: Path) -> None
```

Initialize asset discovery.

**Parameters:**

- **self**
- **assets_dir** (`Path`) - Root assets directory

**Returns:** `None`






---
#### discover

```python
def discover(self) -> List[Asset]
```

Discover all assets in the assets directory.

**Parameters:**

- **self**

**Returns:** `List[Asset]` - List of Asset objects






---


