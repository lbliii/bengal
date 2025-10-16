
---
title: "cache.asset_dependency_map"
type: python-module
source_file: "bengal/cache/asset_dependency_map.py"
css_class: api-content
description: "Asset Dependency Map for incremental builds.  Tracks which pages reference which assets to enable on-demand asset discovery. This allows incremental builds to discover only assets needed for change..."
---

# cache.asset_dependency_map

Asset Dependency Map for incremental builds.

Tracks which pages reference which assets to enable on-demand asset discovery.
This allows incremental builds to discover only assets needed for changed pages,
skipping asset discovery for unchanged pages.

Architecture:
- Mapping: source_path → set[asset_urls] (which pages use which assets)
- Storage: .bengal/asset_deps.json (compact format)
- Tracking: Built during page parsing by extracting asset references
- Incremental: Only discover assets for changed pages

Performance Impact:
- Asset discovery skipped for unchanged pages (~50ms saved per 100 pages)
- Focus on only needed assets in incremental builds
- Incremental asset fingerprinting possible

Asset Types Tracked:
- Images: img src, picture sources
- Stylesheets: link href
- Scripts: script src
- Fonts: @font-face urls
- Other: data URLs, imports, includes

---

## Classes

### `AssetReference`


Reference to an asset from a page.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `url`
  - `str`
  - -
* - `type`
  - `str`
  - -
* - `source_page`
  - `str`
  - -
:::

::::



### `AssetDependencyEntry`


Cache entry for asset dependencies.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `assets`
  - `set[str]`
  - -
* - `tracked_at`
  - `str`
  - -
* - `is_valid`
  - `bool`
  - -
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]`




---
#### `from_dict` @staticmethod
```python
def from_dict(data: dict[str, Any]) -> 'AssetDependencyEntry'
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `data`
  - `dict[str, Any]`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`'AssetDependencyEntry'`




---

### `AssetDependencyMap`


Persistent map of page-to-asset dependencies for incremental discovery.

Purpose:
- Track which assets each page references
- Enable on-demand asset discovery
- Skip asset discovery for unchanged pages
- Support incremental asset fingerprinting

Cache Format (JSON):
{
    "version": 1,
    "pages": {
        "content/index.md": {
            "assets": [
                "/images/logo.png",
                "/css/style.css",
                "/fonts/inter.woff2"
            ],
            "tracked_at": "2025-10-16T12:00:00",
            "is_valid": true
        }
    }
}




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, cache_path: Path | None = None)
```

Initialize asset dependency map.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `cache_path`
  - `Path | None`
  - `None`
  - Path to cache file (defaults to .bengal/asset_deps.json)
:::

::::




---
#### `save_to_disk`
```python
def save_to_disk(self) -> None
```

Save asset dependencies to disk.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `track_page_assets`
```python
def track_page_assets(self, source_path: Path, assets: set[str]) -> None
```

Track assets referenced by a page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `source_path`
  - `Path`
  - -
  - Path to source page
* - `assets`
  - `set[str]`
  - -
  - Set of asset URLs/paths referenced by the page
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `get_page_assets`
```python
def get_page_assets(self, source_path: Path) -> set[str] | None
```

Get assets referenced by a page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `source_path`
  - `Path`
  - -
  - Path to source page
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str] | None` - Set of asset URLs if found and valid, None otherwise




---
#### `has_assets`
```python
def has_assets(self, source_path: Path) -> bool
```

Check if page has tracked assets.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `source_path`
  - `Path`
  - -
  - Path to source page
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if page has valid asset tracking




---
#### `get_all_assets`
```python
def get_all_assets(self) -> set[str]
```

Get all unique assets referenced by any page.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of all asset URLs across all pages




---
#### `get_assets_for_pages`
```python
def get_assets_for_pages(self, source_paths: list[Path]) -> set[str]
```

Get all assets referenced by a set of pages.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `source_paths`
  - `list[Path]`
  - -
  - List of page paths to find assets for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of all asset URLs referenced by the given pages




---
#### `invalidate`
```python
def invalidate(self, source_path: Path) -> None
```

Mark a page's asset tracking as invalid.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `source_path`
  - `Path`
  - -
  - Path to source page
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `invalidate_all`
```python
def invalidate_all(self) -> None
```

Invalidate all asset tracking entries.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `clear`
```python
def clear(self) -> None
```

Clear all asset tracking.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `get_valid_entries`
```python
def get_valid_entries(self) -> dict[str, set[str]]
```

Get all valid asset tracking entries.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, set[str]]` - Dictionary mapping source_path to asset set for valid entries




---
#### `get_invalid_entries`
```python
def get_invalid_entries(self) -> dict[str, set[str]]
```

Get all invalid asset tracking entries.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, set[str]]` - Dictionary mapping source_path to asset set for invalid entries




---
#### `stats`
```python
def stats(self) -> dict[str, Any]
```

Get asset dependency map statistics.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`dict[str, Any]` - Dictionary with cache stats




---
#### `get_asset_pages`
```python
def get_asset_pages(self, asset_url: str) -> set[str]
```

Get all pages that reference a specific asset.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `asset_url`
  - `str`
  - -
  - Asset URL to find references for
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of page paths that reference this asset




---


