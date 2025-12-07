
---
title: "query_index"
type: "python-module"
source_file: "bengal/cache/query_index.py"
line_number: 1
description: "Query Index - Base class for queryable indexes. Provides O(1) lookups for common page queries by pre-computing indexes at build time. Similar to TaxonomyIndex but generalized for any page attribute. A..."
---

# query_index
**Type:** Module
**Source:** [View source](bengal/cache/query_index.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›query_index

Query Index - Base class for queryable indexes.

Provides O(1) lookups for common page queries by pre-computing indexes
at build time. Similar to TaxonomyIndex but generalized for any page attribute.

Architecture:
- Build indexes once during build phase (O(n) cost)
- Persist to disk for incremental builds
- Template access is O(1) hash lookup
- Incrementally update only changed pages

Example:
    # Built-in indexes
    site.indexes.section.get('blog')        # O(1) - all blog posts
    site.indexes.author.get('Jane Smith')   # O(1) - posts by Jane

    # Custom indexes
    site.indexes.status.get('published')    # O(1) - published posts

## Classes




### `IndexEntry`


**Inherits from:**`Cacheable`A single entry in a query index.

Represents one index key (e.g., 'blog' section, 'Jane Smith' author)
and all pages that match that key.

Implements the Cacheable protocol for type-safe serialization.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`key`
: Index key (e.g., 'blog', 'Jane Smith', '2024')

`page_paths`
: List of page source paths (strings, not Page objects)

`metadata`
: Extra data for display (e.g., section title, author email)

`updated_at`
: ISO timestamp of last update

`content_hash`
: Hash of page_paths for change detection

:::







## Methods



#### `__post_init__`

:::{div} api-badge-group
:::

```python
def __post_init__(self)
```


Compute content hash if not provided.





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
def from_cache_dict(cls, data: dict[str, Any]) -> IndexEntry
```


Deserialize from cache dictionary (Cacheable protocol).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`IndexEntry`



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


Alias for to_cache_dict (backward compatibility).



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `from_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-staticmethod">staticmethod</span>:::

```python
def from_dict(data: dict[str, Any]) -> IndexEntry
```


Alias for from_cache_dict (backward compatibility).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`IndexEntry`




### `QueryIndex`


**Inherits from:**`ABC`Base class for queryable indexes.

Subclasses define:
- What to index (e.g., by_section, by_author, by_tag)
- How to extract keys from pages
- Optionally: custom serialization logic

The base class handles:
- Index storage and persistence
- Incremental updates
- Change detection
- O(1) lookups









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, name: str, cache_path: Path)
```


Initialize query index.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `name` | `str` | - | Index name (e.g., 'section', 'author') |
| `cache_path` | `Path` | - | Path to cache file (e.g., .bengal/indexes/section_index.json) |








#### `extract_keys`

:::{div} api-badge-group
:::

```python
def extract_keys(self, page: Page) -> list[tuple[str, dict[str, Any]]]
```


Extract index keys from a page.

Returns list of (key, metadata) tuples. Can return multiple keys
for multi-valued indexes (e.g., multi-author papers, multiple tags).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to extract keys from |







:::{rubric} Returns
:class: rubric-returns
:::


`list[tuple[str, dict[str, Any]]]` - List of (key, metadata) tuples
:::{rubric} Examples
:class: rubric-examples
:::


```python
# Single-valued
    return [('blog', {'title': 'Blog'})]

    # Multi-valued
    return [
        ('Jane Smith', {'email': 'jane@example.com'}),
        ('Bob Jones', {'email': 'bob@example.com'})
    ]

    # Empty (skip this page)
    return []
```




#### `update_page`

:::{div} api-badge-group
:::

```python
def update_page(self, page: Page, build_cache: BuildCache) -> set[str]
```


Update index for a single page.

Handles:
- Removing page from old keys
- Adding page to new keys
- Tracking affected keys for incremental regeneration


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page` | - | Page to update |
| `build_cache` | `BuildCache` | - | Build cache for dependency tracking |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of affected index keys (need regeneration)



#### `remove_page`

:::{div} api-badge-group
:::

```python
def remove_page(self, page_path: str) -> set[str]
```


Remove page from all index entries.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `str` | - | Path to page source file |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of affected keys



#### `get`

:::{div} api-badge-group
:::

```python
def get(self, key: str) -> list[str]
```


Get page paths for index key (O(1) lookup).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | Index key |







:::{rubric} Returns
:class: rubric-returns
:::


`list[str]` - List of page paths (copy, safe to modify)



#### `keys`

:::{div} api-badge-group
:::

```python
def keys(self) -> list[str]
```


Get all index keys.



:::{rubric} Returns
:class: rubric-returns
:::


`list[str]`



#### `has_changed`

:::{div} api-badge-group
:::

```python
def has_changed(self, key: str, page_paths: list[str]) -> bool
```


Check if index entry changed (for skip optimization).

Compares page_paths as sets (order doesn't matter for most use cases).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | Index key |
| `page_paths` | `list[str]` | - | New list of page paths |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if entry changed and needs regeneration



#### `get_metadata`

:::{div} api-badge-group
:::

```python
def get_metadata(self, key: str) -> dict[str, Any]
```


Get metadata for index key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `key` | `str` | - | Index key |







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Metadata dict (empty if key not found)



#### `save_to_disk`

:::{div} api-badge-group
:::

```python
def save_to_disk(self) -> None
```


Persist index to disk.



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


Clear all index data.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `stats`

:::{div} api-badge-group
:::

```python
def stats(self) -> dict[str, Any]
```


Get index statistics.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Dictionary with index stats



#### `__repr__`

:::{div} api-badge-group
:::

```python
def __repr__(self) -> str
```


String representation.



:::{rubric} Returns
:class: rubric-returns
:::


`str`



---
*Generated by Bengal autodoc from `bengal/cache/query_index.py`*

