
---
title: "asset_dependency_map"
type: "python-module"
source_file: "bengal/cache/asset_dependency_map.py"
line_number: 1
description: "Asset Dependency Map for incremental builds. Tracks which pages reference which assets to enable on-demand asset discovery. This allows incremental builds to discover only assets needed for changed pa..."
---

# asset_dependency_map
**Type:** Module
**Source:** [View source](bengal/cache/asset_dependency_map.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›asset_dependency_map

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

## Classes




### `AssetReference`


Reference to an asset from a page.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`url`
: 

`type`
: 

`source_page`
: 

:::










### `AssetDependencyEntry`


**Inherits from:**`Cacheable`Cache entry for asset dependencies.

Implements the Cacheable protocol for type-safe serialization.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`assets`
: 

`tracked_at`
: 

`is_valid`
: 

:::







## Methods



#### `to_cache_dict`

:::{div} api-badge-group
:::

```python
def to_cache_dict(self) -> dict[str, Any]
```


Serialize to cache-friendly dictionary (Cacheable protocol).



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `from_cache_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def from_cache_dict(cls, data: dict[str, Any]) -> AssetDependencyEntry
```


Deserialize from cache dictionary (Cacheable protocol).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`AssetDependencyEntry`



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


Alias for to_cache_dict (test compatibility).



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `from_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def from_dict(cls, data: dict[str, Any]) -> AssetDependencyEntry
```


Alias for from_cache_dict (test compatibility).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`AssetDependencyEntry`




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









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, cache_path: Path | None = None)
```


Initialize asset dependency map.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path \| None` | - | Path to cache file (defaults to .bengal/asset_deps.json) |









#### `save_to_disk`

:::{div} api-badge-group
:::

```python
def save_to_disk(self) -> None
```


Save asset dependencies to disk.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_page_assets`

:::{div} api-badge-group
:::

```python
def track_page_assets(self, source_path: Path, assets: set[str]) -> None
```


Track assets referenced by a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source page |
| `assets` | `set[str]` | - | Set of asset URLs/paths referenced by the page |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_page_assets`

:::{div} api-badge-group
:::

```python
def get_page_assets(self, source_path: Path) -> set[str] | None
```


Get assets referenced by a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source page |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str] | None` - Set of asset URLs if found and valid, None otherwise



#### `has_assets`

:::{div} api-badge-group
:::

```python
def has_assets(self, source_path: Path) -> bool
```


Check if page has tracked assets.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source page |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if page has valid asset tracking



#### `get_all_assets`

:::{div} api-badge-group
:::

```python
def get_all_assets(self) -> set[str]
```


Get all unique assets referenced by any page.



:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of all asset URLs across all pages



#### `get_assets_for_pages`

:::{div} api-badge-group
:::

```python
def get_assets_for_pages(self, source_paths: list[Path]) -> set[str]
```


Get all assets referenced by a set of pages.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_paths` | `list[Path]` | - | List of page paths to find assets for |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of all asset URLs referenced by the given pages



#### `invalidate`

:::{div} api-badge-group
:::

```python
def invalidate(self, source_path: Path) -> None
```


Mark a page's asset tracking as invalid.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source page |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `invalidate_all`

:::{div} api-badge-group
:::

```python
def invalidate_all(self) -> None
```


Invalidate all asset tracking entries.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `clear`

:::{div} api-badge-group
:::

```python
def clear(self) -> None
```


Clear all asset tracking.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_valid_entries`

:::{div} api-badge-group
:::

```python
def get_valid_entries(self) -> dict[str, set[str]]
```


Get all valid asset tracking entries.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, set[str]]` - Dictionary mapping source_path to asset set for valid entries



#### `get_invalid_entries`

:::{div} api-badge-group
:::

```python
def get_invalid_entries(self) -> dict[str, set[str]]
```


Get all invalid asset tracking entries.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, set[str]]` - Dictionary mapping source_path to asset set for invalid entries



#### `stats`

:::{div} api-badge-group
:::

```python
def stats(self) -> dict[str, Any]
```


Get asset dependency map statistics.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Dictionary with cache stats



#### `get_asset_pages`

:::{div} api-badge-group
:::

```python
def get_asset_pages(self, asset_url: str) -> set[str]
```


Get all pages that reference a specific asset.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `asset_url` | `str` | - | Asset URL to find references for |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of page paths that reference this asset



---
*Generated by Bengal autodoc from `bengal/cache/asset_dependency_map.py`*

