---
title: "cache.build_cache"
layout: api-reference
type: python-module
source_file: "../../bengal/cache/build_cache.py"
---

# cache.build_cache

Build Cache - Tracks file changes and dependencies for incremental builds.

**Source:** `../../bengal/cache/build_cache.py`

---

## Classes

### BuildCache


Tracks file hashes and dependencies between builds.

Attributes:
    file_hashes: Mapping of file paths to their SHA256 hashes
    dependencies: Mapping of pages to their dependencies (templates, partials, etc.)
    output_sources: Mapping of output files to their source files
    taxonomy_deps: Mapping of taxonomy terms to affected pages
    page_tags: Mapping of page paths to their tags (for detecting tag changes)
    last_build: Timestamp of last successful build

::: info
This is a dataclass.
:::

**Attributes:**

- **file_hashes** (`Dict[str, str]`)- **dependencies** (`Dict[str, Set[str]]`)- **output_sources** (`Dict[str, str]`)- **taxonomy_deps** (`Dict[str, Set[str]]`)- **page_tags** (`Dict[str, Set[str]]`)- **last_build** (`Optional[str]`)

**Methods:**

#### __post_init__

```python
def __post_init__(self) -> None
```

Convert sets from lists after JSON deserialization.

**Parameters:**

- **self**

**Returns:** `None`






---
#### load

```python
def load(cls, cache_path: Path) -> 'BuildCache'
```

Load build cache from disk.

**Parameters:**

- **cls**
- **cache_path** (`Path`) - Path to cache file

**Returns:** `'BuildCache'` - BuildCache instance (empty if file doesn't exist or is invalid)






---
#### save

```python
def save(self, cache_path: Path) -> None
```

Save build cache to disk.

**Parameters:**

- **self**
- **cache_path** (`Path`) - Path to cache file

**Returns:** `None`






---
#### hash_file

```python
def hash_file(self, file_path: Path) -> str
```

Generate SHA256 hash of a file.

**Parameters:**

- **self**
- **file_path** (`Path`) - Path to file

**Returns:** `str` - Hex string of SHA256 hash






---
#### is_changed

```python
def is_changed(self, file_path: Path) -> bool
```

Check if a file has changed since last build.

**Parameters:**

- **self**
- **file_path** (`Path`) - Path to file

**Returns:** `bool` - True if file is new or has changed, False if unchanged






---
#### update_file

```python
def update_file(self, file_path: Path) -> None
```

Update the hash for a file.

**Parameters:**

- **self**
- **file_path** (`Path`) - Path to file

**Returns:** `None`






---
#### add_dependency

```python
def add_dependency(self, source: Path, dependency: Path) -> None
```

Record that a source file depends on another file.

**Parameters:**

- **self**
- **source** (`Path`) - Source file (e.g., content page)
- **dependency** (`Path`) - Dependency file (e.g., template, partial, config)

**Returns:** `None`






---
#### add_taxonomy_dependency

```python
def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None
```

Record that a taxonomy term affects a page.

**Parameters:**

- **self**
- **taxonomy_term** (`str`) - Taxonomy term (e.g., "tag:python")
- **page** (`Path`) - Page that uses this taxonomy term

**Returns:** `None`






---
#### get_affected_pages

```python
def get_affected_pages(self, changed_file: Path) -> Set[str]
```

Find all pages that depend on a changed file.

**Parameters:**

- **self**
- **changed_file** (`Path`) - File that changed

**Returns:** `Set[str]` - Set of page paths that need to be rebuilt






---
#### get_previous_tags

```python
def get_previous_tags(self, page_path: Path) -> Set[str]
```

Get tags from previous build for a page.

**Parameters:**

- **self**
- **page_path** (`Path`) - Path to page

**Returns:** `Set[str]` - Set of tags from previous build (empty set if new page)






---
#### update_tags

```python
def update_tags(self, page_path: Path, tags: Set[str]) -> None
```

Store current tags for a page (for next build's comparison).

**Parameters:**

- **self**
- **page_path** (`Path`) - Path to page
- **tags** (`Set[str]`) - Current set of tags for the page

**Returns:** `None`






---
#### clear

```python
def clear(self) -> None
```

Clear all cache data.

**Parameters:**

- **self**

**Returns:** `None`






---
#### invalidate_file

```python
def invalidate_file(self, file_path: Path) -> None
```

Remove a file from the cache (useful when file is deleted).

**Parameters:**

- **self**
- **file_path** (`Path`) - Path to file

**Returns:** `None`






---
#### get_stats

```python
def get_stats(self) -> Dict[str, int]
```

Get cache statistics.

**Parameters:**

- **self**

**Returns:** `Dict[str, int]` - Dictionary with cache stats






---
#### __repr__

```python
def __repr__(self) -> str
```

*No description provided.*

**Parameters:**

- **self**

**Returns:** `str`






---


