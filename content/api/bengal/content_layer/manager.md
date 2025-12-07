
---
title: "manager"
type: "python-module"
source_file: "bengal/content_layer/manager.py"
line_number: 1
description: "ContentLayerManager - Orchestrates content fetching from multiple sources. Handles source registration, parallel fetching, caching, and aggregation."
---

# manager
**Type:** Module
**Source:** [View source](bengal/content_layer/manager.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[content_layer](/api/bengal/content_layer/) ›manager

ContentLayerManager - Orchestrates content fetching from multiple sources.

Handles source registration, parallel fetching, caching, and aggregation.

## Classes




### `CachedSource`


Metadata about a cached source.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`source_key`
: 

`cached_at`
: 

`entry_count`
: 

`checksum`
: 

:::










### `ContentLayerManager`


Manages content from multiple sources.

Handles:
- Source registration (local, remote, custom)
- Parallel async fetching
- Disk caching with TTL and invalidation
- Aggregation of all sources into unified content list









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, cache_dir: Path | None = None, cache_ttl: timedelta = timedelta(hours=1), offline: bool = False) -> None
```


Initialize content layer manager.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_dir` | `Path \| None` | - | Directory for caching remote content (default: .bengal/content_cache) |
| `cache_ttl` | `timedelta` | `timedelta(hours=1)` | Time-to-live for cached content (default: 1 hour) |
| `offline` | `bool` | `False` | If True, only use cached content (no network requests) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `register_source`

:::{div} api-badge-group
:::

```python
def register_source(self, name: str, source_type: str, config: dict[str, Any]) -> None
```


Register a content source.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Unique name for this source instance |
| `source_type` | `str` | - | Type identifier ('local', 'github', 'rest', 'notion') |
| `config` | `dict[str, Any]` | - | Source-specific configuration |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`ValueError`**:If source_type is unknown




#### `register_custom_source`

:::{div} api-badge-group
:::

```python
def register_custom_source(self, name: str, source: ContentSource) -> None
```


Register a custom source instance.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Unique name for this source |
| `source` | `ContentSource` | - | ContentSource implementation instance |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `fetch_all`

:::{div} api-badge-group
<span class="api-badge api-badge-async">async</span>:::

```python
async def fetch_all(self, use_cache: bool = True) -> list[ContentEntry]
```


Fetch content from all registered sources.

Fetches from all sources in parallel, using cache when available
and falling back to cached content in offline mode.

:::{info} Async Method
This is an asynchronous method. Use `await` when calling.
:::


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `use_cache` | `bool` | `True` | Whether to use cached content if available |







:::{rubric} Returns
:class: rubric-returns
:::


`list[ContentEntry]` - List of all content entries from all sources







#### `clear_cache`

:::{div} api-badge-group
:::

```python
def clear_cache(self, source_name: str | None = None) -> int
```


Clear cached content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_name` | `str \| None` | - | Specific source to clear, or None for all |







:::{rubric} Returns
:class: rubric-returns
:::


`int` - Number of cache files deleted



#### `get_cache_status`

:::{div} api-badge-group
:::

```python
def get_cache_status(self) -> dict[str, dict[str, Any]]
```


Get status of all cached sources.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, dict[str, Any]]` - Dictionary mapping source names to cache status



#### `fetch_all_sync`

:::{div} api-badge-group
:::

```python
def fetch_all_sync(self, use_cache: bool = True) -> list[ContentEntry]
```


Synchronous wrapper for fetch_all().


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `use_cache` | `bool` | `True` | Whether to use cached content if available |







:::{rubric} Returns
:class: rubric-returns
:::


`list[ContentEntry]` - List of all content entries



#### `__repr__`

:::{div} api-badge-group
:::

```python
def __repr__(self) -> str
```


*No description provided.*



:::{rubric} Returns
:class: rubric-returns
:::


`str`



---
*Generated by Bengal autodoc from `bengal/content_layer/manager.py`*

