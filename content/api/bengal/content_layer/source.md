
---
title: "source"
type: "python-module"
source_file: "bengal/content_layer/source.py"
line_number: 1
description: "ContentSource - Abstract base class for content sources. Defines the protocol that all content sources must implement."
---

# source
**Type:** Module
**Source:** [View source](bengal/content_layer/source.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[content_layer](/api/bengal/content_layer/) ›source

ContentSource - Abstract base class for content sources.

Defines the protocol that all content sources must implement.

## Classes




### `ContentSource`


**Inherits from:**`ABC`Abstract base class for content sources.

Implementations fetch content from various origins (local files,
remote APIs, databases) and return unified ContentEntry objects.

Subclasses must implement:
    - source_type property
    - fetch_all() async generator
    - fetch_one() async method






:::{rubric} Properties
:class: rubric-properties
:::



#### `source_type` @property

```python
def source_type(self) -> str
```
Return source type identifier.




## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, name: str, config: dict[str, Any]) -> None
```


Initialize content source.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Unique name for this source instance (e.g., "api-docs") |
| `config` | `dict[str, Any]` | - | Source-specific configuration dictionary |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `fetch_all`

:::{div} api-badge-group
<span class="api-badge api-badge-async">async</span>:::

```python
async def fetch_all(self) -> AsyncIterator[ContentEntry]
```


Fetch all content entries from this source.

:::{info} Async Method
This is an asynchronous method. Use `await` when calling.
:::



:::{rubric} Returns
:class: rubric-returns
:::


`AsyncIterator[ContentEntry]`
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> async for entry in source.fetch_all():
    ...     print(entry.title)
```




#### `fetch_one`

:::{div} api-badge-group
<span class="api-badge api-badge-async">async</span>:::

```python
async def fetch_one(self, id: str) -> ContentEntry | None
```


Fetch a single content entry by ID.

:::{info} Async Method
This is an asynchronous method. Use `await` when calling.
:::


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `id` | `str` | - | Source-specific identifier (e.g., file path, doc ID) |







:::{rubric} Returns
:class: rubric-returns
:::


`ContentEntry | None` - ContentEntry if found, None otherwise



#### `get_cache_key`

:::{div} api-badge-group
:::

```python
def get_cache_key(self) -> str
```


Generate cache key for this source configuration.

Used to invalidate cache when config changes. Override for
custom cache key logic.



:::{rubric} Returns
:class: rubric-returns
:::


`str` - 16-character hex string based on config hash



#### `get_last_modified`

:::{div} api-badge-group
<span class="api-badge api-badge-async">async</span>:::

```python
async def get_last_modified(self) -> datetime | None
```


Get last modification time for the entire source.

Used for cache invalidation. Returns None if unknown or not supported.

:::{info} Async Method
This is an asynchronous method. Use `await` when calling.
:::



:::{rubric} Returns
:class: rubric-returns
:::


`datetime | None` - Last modification datetime or None



#### `is_changed`

:::{div} api-badge-group
<span class="api-badge api-badge-async">async</span>:::

```python
async def is_changed(self, cached_checksum: str | None) -> bool
```


Check if source content has changed since last fetch.

:::{info} Async Method
This is an asynchronous method. Use `await` when calling.
:::


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cached_checksum` | `str \| None` | - | Previously cached checksum |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if content may have changed, False if definitely unchanged



#### `fetch_all_sync`

:::{div} api-badge-group
:::

```python
def fetch_all_sync(self) -> Iterator[ContentEntry]
```


Synchronous wrapper for fetch_all().

Runs the async generator in a new event loop.



:::{rubric} Returns
:class: rubric-returns
:::


`Iterator[ContentEntry]`



#### `fetch_one_sync`

:::{div} api-badge-group
:::

```python
def fetch_one_sync(self, id: str) -> ContentEntry | None
```


Synchronous wrapper for fetch_one().


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `id` | `str` | - | Source-specific identifier |







:::{rubric} Returns
:class: rubric-returns
:::


`ContentEntry | None` - ContentEntry if found, None otherwise



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
*Generated by Bengal autodoc from `bengal/content_layer/source.py`*

