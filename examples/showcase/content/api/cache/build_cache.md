
---
title: "cache.build_cache"
type: python-module
source_file: "bengal/cache/build_cache.py"
css_class: api-content
description: "Build Cache - Tracks file changes and dependencies for incremental builds."
---

# cache.build_cache

Build Cache - Tracks file changes and dependencies for incremental builds.

---

## Classes

### `ParsedContentCache`


Cached parsed markdown content for a page.

This allows skipping markdown parsing when only templates change.
Optimization #2: Saves 20-30% time on template changes.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`html`** (`str`)- **`toc`** (`str`)- **`toc_items`** (`list[dict[str, Any]]`)- **`metadata_hash`** (`str`)- **`template`** (`str`)- **`parser_version`** (`str`)- **`timestamp`** (`str`)- **`size_bytes`** (`int`)



### `BuildCache`


Tracks file hashes and dependencies between builds.

IMPORTANT PERSISTENCE CONTRACT:
- This cache must NEVER contain object references (Page, Section, Asset objects)
- All data must be JSON-serializable (paths, strings, numbers, lists, dicts, sets)
- Object relationships are rebuilt each build from cached paths

Attributes:
    file_hashes: Mapping of file paths to their SHA256 hashes
    dependencies: Mapping of pages to their dependencies (templates, partials, etc.)
    output_sources: Mapping of output files to their source files
    taxonomy_deps: Mapping of taxonomy terms to affected pages
    page_tags: Mapping of page paths to their tags (for detecting tag changes)
    tag_to_pages: Inverted index mapping tag slug to page paths (for O(1) reconstruction)
    known_tags: Set of all tag slugs from previous build (for detecting deletions)
    parsed_content: Cached parsed HTML/TOC (Optimization #2)
    last_build: Timestamp of last successful build

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`file_hashes`** (`dict[str, str]`)- **`dependencies`** (`dict[str, set[str]]`)- **`output_sources`** (`dict[str, str]`)- **`taxonomy_deps`** (`dict[str, set[str]]`)- **`page_tags`** (`dict[str, set[str]]`)- **`tag_to_pages`** (`dict[str, set[str]]`)- **`known_tags`** (`set[str]`)- **`parsed_content`** (`dict[str, dict[str, Any]]`)- **`last_build`** (`str | None`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `__post_init__`
```python
def __post_init__(self) -> None
```

Convert sets from lists after JSON deserialization.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `load` @classmethod
```python
def load(cls, cache_path: Path) -> 'BuildCache'
```

Load build cache from disk.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`cls`**
- **`cache_path`** (`Path`) - Path to cache file

:::{rubric} Returns
:class: rubric-returns
:::
`'BuildCache'` - BuildCache instance (empty if file doesn't exist or is invalid)




---
#### `save`
```python
def save(self, cache_path: Path) -> None
```

Save build cache to disk.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`cache_path`** (`Path`) - Path to cache file

:::{rubric} Returns
:class: rubric-returns
:::
`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`IOError`**: If cache file cannot be written json.JSONEncodeError: If cache data cannot be serialized



---
#### `hash_file`
```python
def hash_file(self, file_path: Path) -> str
```

Generate SHA256 hash of a file.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`file_path`** (`Path`) - Path to file

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Hex string of SHA256 hash




---
#### `is_changed`
```python
def is_changed(self, file_path: Path) -> bool
```

Check if a file has changed since last build.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`file_path`** (`Path`) - Path to file

:::{rubric} Returns
:class: rubric-returns
:::
`bool` - True if file is new or has changed, False if unchanged




---
#### `update_file`
```python
def update_file(self, file_path: Path) -> None
```

Update the hash for a file.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`file_path`** (`Path`) - Path to file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `add_dependency`
```python
def add_dependency(self, source: Path, dependency: Path) -> None
```

Record that a source file depends on another file.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`source`** (`Path`) - Source file (e.g., content page)
- **`dependency`** (`Path`) - Dependency file (e.g., template, partial, config)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `add_taxonomy_dependency`
```python
def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None
```

Record that a taxonomy term affects a page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`taxonomy_term`** (`str`) - Taxonomy term (e.g., "tag:python")
- **`page`** (`Path`) - Page that uses this taxonomy term

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `get_affected_pages`
```python
def get_affected_pages(self, changed_file: Path) -> set[str]
```

Find all pages that depend on a changed file.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`changed_file`** (`Path`) - File that changed

:::{rubric} Returns
:class: rubric-returns
:::
`set[str]` - Set of page paths that need to be rebuilt




---
#### `get_previous_tags`
```python
def get_previous_tags(self, page_path: Path) -> set[str]
```

Get tags from previous build for a page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page_path`** (`Path`) - Path to page

:::{rubric} Returns
:class: rubric-returns
:::
`set[str]` - Set of tags from previous build (empty set if new page)




---
#### `update_tags`
```python
def update_tags(self, page_path: Path, tags: set[str]) -> None
```

Store current tags for a page (for next build's comparison).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page_path`** (`Path`) - Path to page
- **`tags`** (`set[str]`) - Current set of tags for the page

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `update_page_tags`
```python
def update_page_tags(self, page_path: Path, tags: set[str]) -> set[str]
```

Update tag index when a page's tags change.

Maintains bidirectional index:
- page_tags: path → tags (forward)
- tag_to_pages: tag → paths (inverted)

This is the key method that enables O(1) taxonomy reconstruction.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`page_path`** (`Path`) - Path to page source file
- **`tags`** (`set[str]`) - Current set of tags for this page (original case, e.g., "Python", "Web Dev")

:::{rubric} Returns
:class: rubric-returns
:::
`set[str]` - Set of affected tag slugs (tags added, removed, or modified)




---
#### `get_pages_for_tag`
```python
def get_pages_for_tag(self, tag_slug: str) -> set[str]
```

Get all page paths for a given tag.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`tag_slug`** (`str`) - Tag slug (e.g., 'python', 'web-dev')

:::{rubric} Returns
:class: rubric-returns
:::
`set[str]` - Set of page path strings




---
#### `get_all_tags`
```python
def get_all_tags(self) -> set[str]
```

Get all known tag slugs from previous build.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`set[str]` - Set of tag slugs




---
#### `clear`
```python
def clear(self) -> None
```

Clear all cache data.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `invalidate_file`
```python
def invalidate_file(self, file_path: Path) -> None
```

Remove a file from the cache (useful when file is deleted).



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`file_path`** (`Path`) - Path to file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `get_stats`
```python
def get_stats(self) -> dict[str, int]
```

Get cache statistics with logging.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, int]` - Dictionary with cache stats




---
#### `__repr__`
```python
def __repr__(self) -> str
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
#### `store_parsed_content`
```python
def store_parsed_content(self, file_path: Path, html: str, toc: str, toc_items: list[dict[str, Any]], metadata: dict[str, Any], template: str, parser_version: str) -> None
```

Store parsed content in cache (Optimization #2).

This allows skipping markdown parsing when only templates change,
resulting in 20-30% faster builds in that scenario.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `file_path` | `Path` | - | Path to source file |
| `html` | `str` | - | Rendered HTML (post-markdown, pre-template) |
| `toc` | `str` | - | Table of contents HTML |
| `toc_items` | `list[dict[str, Any]]` | - | Structured TOC data |
| `metadata` | `dict[str, Any]` | - | Page metadata (frontmatter) |
| `template` | `str` | - | Template name used |
| `parser_version` | `str` | - | Parser version string (e.g., "mistune-3.0") |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `get_parsed_content`
```python
def get_parsed_content(self, file_path: Path, metadata: dict[str, Any], template: str, parser_version: str) -> dict[str, Any] | None
```

Get cached parsed content if valid (Optimization #2).

Validates that:
1. Content file hasn't changed (via file_hashes)
2. Metadata hasn't changed (via metadata_hash)
3. Template hasn't changed (via template name)
4. Parser version matches (avoid incompatibilities)
5. Template file hasn't changed (via dependencies)



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `self` | - | - | - |
| `file_path` | `Path` | - | Path to source file |
| `metadata` | `dict[str, Any]` | - | Current page metadata |
| `template` | `str` | - | Current template name |
| `parser_version` | `str` | - | Current parser version |

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any] | None` - Cached data dict if valid, None if invalid or not found




---
#### `invalidate_parsed_content`
```python
def invalidate_parsed_content(self, file_path: Path) -> None
```

Remove cached parsed content for a file.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`file_path`** (`Path`) - Path to file

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `get_parsed_content_stats`
```python
def get_parsed_content_stats(self) -> dict[str, Any]
```

Get parsed content cache statistics.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Dictionary with cache stats




---
