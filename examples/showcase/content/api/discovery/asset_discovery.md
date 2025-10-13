
---
title: "discovery.asset_discovery"
type: python-module
source_file: "bengal/discovery/asset_discovery.py"
css_class: api-content
description: "Asset discovery - finds and organizes static assets."
---

# discovery.asset_discovery

Asset discovery - finds and organizes static assets.

---

## Classes

### `AssetDiscovery`


Discovers static assets (images, CSS, JS, etc.).

This class is responsible ONLY for finding files.
Asset processing logic (bundling, minification) is handled elsewhere.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, assets_dir: Path) -> None
```

Initialize asset discovery.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`assets_dir`** (`Path`) - Root assets directory

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `discover`
```python
def discover(self) -> list[Asset]
```

Discover all assets in the assets directory.

Simply walks the directory tree and creates Asset objects.
No business logic - just discovery.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[Asset]` - List of Asset objects




---
