
---
title: "cache.taxonomy_index"
type: python-module
source_file: "bengal/cache/taxonomy_index.py"
css_class: api-content
description: "Taxonomy Index for incremental builds.  Maintains persistent index of tag-to-pages mappings to enable incremental taxonomy updates. Instead of rebuilding the entire taxonomy structure, incremental ..."
---

# cache.taxonomy_index

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

---

## Classes

### `TagEntry`


Entry for a single tag in the index.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 5 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `tag_slug`
  - `str`
  - -
* - `tag_name`
  - `str`
  - -
* - `page_paths`
  - `list[str]`
  - -
* - `updated_at`
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
def from_dict(data: dict[str, Any]) -> 'TagEntry'
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

`'TagEntry'`




---

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




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, cache_path: Path | None = None)
```

Initialize taxonomy index.



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
  - Path to cache file (defaults to .bengal/taxonomy_index.json)
:::

::::




---
#### `save_to_disk`
```python
def save_to_disk(self) -> None
```

Save taxonomy index to disk.



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
#### `update_tag`
```python
def update_tag(self, tag_slug: str, tag_name: str, page_paths: list[str]) -> None
```

Update or create a tag entry.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 4 parameters (click to expand)
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
* - `tag_slug`
  - `str`
  - -
  - Normalized tag identifier
* - `tag_name`
  - `str`
  - -
  - Original tag name for display
* - `page_paths`
  - `list[str]`
  - -
  - List of page paths with this tag
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `get_tag`
```python
def get_tag(self, tag_slug: str) -> TagEntry | None
```

Get a tag entry by slug.



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
* - `tag_slug`
  - `str`
  - -
  - Normalized tag identifier
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`TagEntry | None` - TagEntry if found and valid, None otherwise




---
#### `get_pages_for_tag`
```python
def get_pages_for_tag(self, tag_slug: str) -> list[str] | None
```

Get pages with a specific tag.



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
* - `tag_slug`
  - `str`
  - -
  - Normalized tag identifier
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[str] | None` - List of page paths or None if tag not found/invalid




---
#### `has_tag`
```python
def has_tag(self, tag_slug: str) -> bool
```

Check if tag exists and is valid.



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
* - `tag_slug`
  - `str`
  - -
  - Normalized tag identifier
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if tag exists and is valid




---
#### `get_tags_for_page`
```python
def get_tags_for_page(self, page_path: Path) -> set[str]
```

Get all tags for a specific page (reverse lookup).



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
* - `page_path`
  - `Path`
  - -
  - Path to page
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of tag slugs for this page




---
#### `get_all_tags`
```python
def get_all_tags(self) -> dict[str, TagEntry]
```

Get all valid tags.



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

`dict[str, TagEntry]` - Dictionary mapping tag_slug to TagEntry for valid tags




---
#### `invalidate_tag`
```python
def invalidate_tag(self, tag_slug: str) -> None
```

Mark a tag as invalid.



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
* - `tag_slug`
  - `str`
  - -
  - Normalized tag identifier
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

Invalidate all tag entries.



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

Clear all tags.



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
#### `remove_page_from_all_tags`
```python
def remove_page_from_all_tags(self, page_path: Path) -> set[str]
```

Remove a page from all tags it belongs to.



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
* - `page_path`
  - `Path`
  - -
  - Path to page to remove
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of affected tag slugs




---
#### `get_valid_entries`
```python
def get_valid_entries(self) -> dict[str, TagEntry]
```

Get all valid tag entries.



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

`dict[str, TagEntry]` - Dictionary mapping tag_slug to TagEntry for valid entries




---
#### `get_invalid_entries`
```python
def get_invalid_entries(self) -> dict[str, TagEntry]
```

Get all invalid tag entries.



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

`dict[str, TagEntry]` - Dictionary mapping tag_slug to TagEntry for invalid entries




---
#### `pages_changed`
```python
def pages_changed(self, tag_slug: str, new_page_paths: list[str]) -> bool
```

Check if pages for a tag have changed (enabling skipping of unchanged tag regeneration).

This is the key optimization for Phase 2c.2: If a tag's page membership hasn't changed,
we can skip regenerating its HTML pages entirely since the output would be identical.



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
* - `tag_slug`
  - `str`
  - -
  - Normalized tag identifier
* - `new_page_paths`
  - `list[str]`
  - -
  - New list of page paths for this tag
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if tag pages have changed and need regeneration
    False if tag pages are identical to cached version




---
#### `stats`
```python
def stats(self) -> dict[str, Any]
```

Get taxonomy index statistics.



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

`dict[str, Any]` - Dictionary with index stats




---


