
---
title: "taxonomy_index"
type: "python-module"
source_file: "bengal/bengal/cache/taxonomy_index.py"
line_number: 1
description: "Taxonomy Index for incremental builds. Maintains persistent index of tag-to-pages mappings to enable incremental taxonomy updates. Instead of rebuilding the entire taxonomy structure, incremental buil..."
---

# taxonomy_index
**Type:** Module
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/bengal/cache/taxonomy_index.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›taxonomy_index

Taxonomy Index for incremental builds.

Maintains persistent index of tag-to-pages mappings to enable incremental
taxonomy updates. Instead of rebuilding the entire taxonomy structure,
incremental builds can update only affected tags.

Architecture:
- Mapping: tag_slug → [page_paths] (which pages have which tags)
- Storage: .bengal/taxonomy_index.json (compact format)
- Tracking: Built during page discovery, updated on tag changes
- Incremental: Only update affected tags, reuse unchanged tags

Performance Impact:
- Taxonomy rebuild skipped for unchanged pages (~60ms saved per 100 pages)
- Only affected tags regenerated
- Avoid full taxonomy structure rebuild

## Classes




### `TagEntry`


**Inherits from:**`Cacheable`Entry for a single tag in the index.

Implements the Cacheable protocol for type-safe serialization.


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `tag_slug` | - | *No description provided.* |
| `tag_name` | - | *No description provided.* |
| `page_paths` | - | *No description provided.* |
| `updated_at` | - | *No description provided.* |
| `is_valid` | - | *No description provided.* |







## Methods



#### `to_cache_dict`
```python
def to_cache_dict(self) -> dict[str, Any]
```


Serialize to cache-friendly dictionary (Cacheable protocol).



**Returns**


`dict[str, Any]`



#### `from_cache_dict` @classmethod
```python
def from_cache_dict(cls, data: dict[str, Any]) -> TagEntry
```


Deserialize from cache dictionary (Cacheable protocol).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







**Returns**


`TagEntry`



#### `to_dict`
```python
def to_dict(self) -> dict[str, Any]
```


Alias for to_cache_dict (test compatibility).



**Returns**


`dict[str, Any]`



#### `from_dict` @classmethod
```python
def from_dict(cls, data: dict[str, Any]) -> TagEntry
```


Alias for from_cache_dict (test compatibility).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







**Returns**


`TagEntry`




### `TaxonomyIndex`


Persistent index of tag-to-pages mappings for incremental taxonomy updates.

Purpose:
- Track which pages have which tags
- Enable incremental tag updates (only changed tags)
- Avoid full taxonomy rebuild on every page change
- Support incremental tag page generation

Cache Format (JSON):
{
    "version": 1,
    "tags": {
        "python": {
            "tag_slug": "python",
            "tag_name": "Python",
            "page_paths": ["content/post1.md", "content/post2.md"],
            "updated_at": "2025-10-16T12:00:00",
            "is_valid": true
        }
    }
}









## Methods



#### `__init__`
```python
def __init__(self, cache_path: Path | None = None)
```


Initialize taxonomy index.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path \| None` | - | Path to cache file (defaults to .bengal/taxonomy_index.json) |









#### `save_to_disk`
```python
def save_to_disk(self) -> None
```


Save taxonomy index to disk.



**Returns**


`None`



#### `update_tag`
```python
def update_tag(self, tag_slug: str, tag_name: str, page_paths: list[str]) -> None
```


Update or create a tag entry.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Normalized tag identifier |
| `tag_name` | `str` | - | Original tag name for display |
| `page_paths` | `list[str]` | - | List of page paths with this tag |







**Returns**


`None`



#### `get_tag`
```python
def get_tag(self, tag_slug: str) -> TagEntry | None
```


Get a tag entry by slug.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Normalized tag identifier |







**Returns**


`TagEntry | None` - TagEntry if found and valid, None otherwise



#### `get_pages_for_tag`
```python
def get_pages_for_tag(self, tag_slug: str) -> list[str] | None
```


Get pages with a specific tag.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Normalized tag identifier |







**Returns**


`list[str] | None` - List of page paths or None if tag not found/invalid



#### `has_tag`
```python
def has_tag(self, tag_slug: str) -> bool
```


Check if tag exists and is valid.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Normalized tag identifier |







**Returns**


`bool` - True if tag exists and is valid



#### `get_tags_for_page`
```python
def get_tags_for_page(self, page_path: Path) -> set[str]
```


Get all tags for a specific page (reverse lookup).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page |







**Returns**


`set[str]` - Set of tag slugs for this page



#### `get_all_tags`
```python
def get_all_tags(self) -> dict[str, TagEntry]
```


Get all valid tags.



**Returns**


`dict[str, TagEntry]` - Dictionary mapping tag_slug to TagEntry for valid tags



#### `invalidate_tag`
```python
def invalidate_tag(self, tag_slug: str) -> None
```


Mark a tag as invalid.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Normalized tag identifier |







**Returns**


`None`



#### `invalidate_all`
```python
def invalidate_all(self) -> None
```


Invalidate all tag entries.



**Returns**


`None`



#### `clear`
```python
def clear(self) -> None
```


Clear all tags.



**Returns**


`None`



#### `remove_page_from_all_tags`
```python
def remove_page_from_all_tags(self, page_path: Path) -> set[str]
```


Remove a page from all tags it belongs to.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page to remove |







**Returns**


`set[str]` - Set of affected tag slugs



#### `get_valid_entries`
```python
def get_valid_entries(self) -> dict[str, TagEntry]
```


Get all valid tag entries.



**Returns**


`dict[str, TagEntry]` - Dictionary mapping tag_slug to TagEntry for valid entries



#### `get_invalid_entries`
```python
def get_invalid_entries(self) -> dict[str, TagEntry]
```


Get all invalid tag entries.



**Returns**


`dict[str, TagEntry]` - Dictionary mapping tag_slug to TagEntry for invalid entries



#### `pages_changed`
```python
def pages_changed(self, tag_slug: str, new_page_paths: list[str]) -> bool
```


Check if pages for a tag have changed (enabling skipping of unchanged tag regeneration).

This is the key optimization for Phase 2c.2: If a tag's page membership hasn't changed,
we can skip regenerating its HTML pages entirely since the output would be identical.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Normalized tag identifier |
| `new_page_paths` | `list[str]` | - | New list of page paths for this tag |







**Returns**


`bool` - True if tag pages have changed and need regeneration
    False if tag pages are identical to cached version



#### `stats`
```python
def stats(self) -> dict[str, Any]
```


Get taxonomy index statistics.



**Returns**


`dict[str, Any]` - Dictionary with index stats



---
*Generated by Bengal autodoc from `bengal/bengal/cache/taxonomy_index.py`*

