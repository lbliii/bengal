
---
title: "build_cache"
type: "python-module"
source_file: "bengal/bengal/cache/build_cache.py"
line_number: 1
description: "Build Cache - Tracks file changes and dependencies for incremental builds."
---

# build_cache
**Type:** Module
**Source:** [View source](bengal/bengal/cache/build_cache.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›build_cache

Build Cache - Tracks file changes and dependencies for incremental builds.

## Classes




### `BuildCache`


Tracks file hashes and dependencies between builds.

IMPORTANT PERSISTENCE CONTRACT:
- This cache must NEVER contain object references (Page, Section, Asset objects)
- All data must be JSON-serializable (paths, strings, numbers, lists, dicts, sets)
- Object relationships are rebuilt each build from cached paths

NOTE: BuildCache intentionally does NOT implement the Cacheable protocol.
Rationale:
- Uses pickle for performance (faster than JSON for sets/complex structures)
- Has tolerant loader with custom version handling logic
- Contains many specialized fields (dependencies, hashes, etc.)
- Designed for internal build state, not type-safe caching contracts

For type-safe caching, use types that implement the Cacheable protocol:
- PageCore (bengal/core/page/page_core.py)
- TagEntry (bengal/cache/taxonomy_index.py)
- AssetDependencyEntry (bengal/cache/asset_dependency_map.py)


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `VERSION` | - | *No description provided.* |
| `version` | - | *No description provided.* |
| `file_hashes` | - | Mapping of file paths to their SHA256 hashes |
| `dependencies` | - | Mapping of pages to their dependencies (templates, partials, etc.) |
| `output_sources` | - | Mapping of output files to their source files |
| `taxonomy_deps` | - | Mapping of taxonomy terms to affected pages |
| `page_tags` | - | Mapping of page paths to their tags (for detecting tag changes) |
| `tag_to_pages` | - | Inverted index mapping tag slug to page paths (for O(1) reconstruction) |
| `known_tags` | - | Set of all tag slugs from previous build (for detecting deletions) |
| `parsed_content` | - | Cached parsed HTML/TOC (Optimization #2) |
| `synthetic_pages` | - | *No description provided.* |
| `validation_results` | - | *No description provided.* |
| `config_hash` | - | Hash of resolved configuration (for auto-invalidation) |
| `last_build` | - | Timestamp of last successful build |







## Methods



#### `__post_init__`
```python
def __post_init__(self) -> None
```


Convert sets from lists after JSON deserialization.



**Returns**


`None`



#### `load` @classmethod
```python
def load(cls, cache_path: Path, use_lock: bool = True) -> BuildCache
```


Load build cache from disk with optional file locking.

Loader behavior:
- Tolerant to malformed JSON: On parse errors or schema mismatches, returns a fresh
  `BuildCache` instance and logs a warning.
- Version mismatches: Logs a warning and best-effort loads known fields.
- File locking: Acquires shared lock to prevent reading during writes.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path` | - | Path to cache file |
| `use_lock` | `bool` | `True` | Whether to use file locking (default: True) |







**Returns**


`BuildCache` - BuildCache instance (empty if file doesn't exist or is invalid)




#### `save`
```python
def save(self, cache_path: Path, use_lock: bool = True) -> None
```


Save build cache to disk with optional file locking.

Persistence semantics:
- Atomic writes: Uses `AtomicFile` (temp-write → atomic rename) to prevent partial files
  on crash/interruption.
- File locking: Acquires exclusive lock to prevent concurrent writes.
- Combined safety: Lock + atomic write ensures complete consistency.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_path` | `Path` | - | Path to cache file |
| `use_lock` | `bool` | `True` | Whether to use file locking (default: True) |







**Returns**


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`IOError`**:If cache file cannot be written json.JSONEncodeError: If cache data cannot be serialized
- **`LockAcquisitionError`**:If lock cannot be acquired (when use_lock=True)





#### `hash_file`
```python
def hash_file(self, file_path: Path) -> str
```


Generate SHA256 hash of a file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







**Returns**


`str` - Hex string of SHA256 hash



#### `is_changed`
```python
def is_changed(self, file_path: Path) -> bool
```


Check if a file has changed since last build.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







**Returns**


`bool` - True if file is new or has changed, False if unchanged



#### `update_file`
```python
def update_file(self, file_path: Path) -> None
```


Update the hash for a file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







**Returns**


`None`



#### `get_cached_validation_results`
```python
def get_cached_validation_results(self, file_path: Path, validator_name: str) -> list[dict[str, Any]] | None
```


Get cached validation results for a file and validator.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |
| `validator_name` | `str` | - | Name of validator |







**Returns**


`list[dict[str, Any]] | None` - List of CheckResult dicts if cached and file unchanged, None otherwise



#### `cache_validation_results`
```python
def cache_validation_results(self, file_path: Path, validator_name: str, results: list[Any]) -> None
```


Cache validation results for a file and validator.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |
| `validator_name` | `str` | - | Name of validator |
| `results` | `list[Any]` | - | List of CheckResult objects to cache |







**Returns**


`None`



#### `invalidate_validation_results`
```python
def invalidate_validation_results(self, file_path: Path | None = None) -> None
```


Invalidate validation results for a file or all files.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| None` | - | Path to file (if None, invalidate all) |







**Returns**


`None`



#### `track_output`
```python
def track_output(self, source_path: Path, output_path: Path, output_dir: Path) -> None
```


Track the relationship between a source file and its output file.

This enables cleanup of output files when source files are deleted.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file (e.g., content/blog/post.md) |
| `output_path` | `Path` | - | Absolute path to output file (e.g., /path/to/public/blog/post/index.html) |
| `output_dir` | `Path` | - | Site output directory (e.g., /path/to/public) |







**Returns**


`None`



#### `add_dependency`
```python
def add_dependency(self, source: Path, dependency: Path) -> None
```


Record that a source file depends on another file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `Path` | - | Source file (e.g., content page) |
| `dependency` | `Path` | - | Dependency file (e.g., template, partial, config) |







**Returns**


`None`



#### `add_taxonomy_dependency`
```python
def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None
```


Record that a taxonomy term affects a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `taxonomy_term` | `str` | - | Taxonomy term (e.g., "tag:python") |
| `page` | `Path` | - | Page that uses this taxonomy term |







**Returns**


`None`



#### `get_affected_pages`
```python
def get_affected_pages(self, changed_file: Path) -> set[str]
```


Find all pages that depend on a changed file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `changed_file` | `Path` | - | File that changed |







**Returns**


`set[str]` - Set of page paths that need to be rebuilt



#### `get_previous_tags`
```python
def get_previous_tags(self, page_path: Path) -> set[str]
```


Get tags from previous build for a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page |







**Returns**


`set[str]` - Set of tags from previous build (empty set if new page)



#### `update_tags`
```python
def update_tags(self, page_path: Path, tags: set[str]) -> None
```


Store current tags for a page (for next build's comparison).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page |
| `tags` | `set[str]` | - | Current set of tags for the page |







**Returns**


`None`



#### `update_page_tags`
```python
def update_page_tags(self, page_path: Path, tags: set[str]) -> set[str]
```


Update tag index when a page's tags change.

Maintains bidirectional index:
- page_tags: path → tags (forward)
- tag_to_pages: tag → paths (inverted)

This is the key method that enables O(1) taxonomy reconstruction.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page source file |
| `tags` | `set[str]` | - | Current set of tags for this page (original case, e.g., "Python", "Web Dev") |







**Returns**


`set[str]` - Set of affected tag slugs (tags added, removed, or modified)



#### `get_pages_for_tag`
```python
def get_pages_for_tag(self, tag_slug: str) -> set[str]
```


Get all page paths for a given tag.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Tag slug (e.g., 'python', 'web-dev') |







**Returns**


`set[str]` - Set of page path strings



#### `get_all_tags`
```python
def get_all_tags(self) -> set[str]
```


Get all known tag slugs from previous build.



**Returns**


`set[str]` - Set of tag slugs



#### `clear`
```python
def clear(self) -> None
```


Clear all cache data.



**Returns**


`None`



#### `validate_config`
```python
def validate_config(self, current_hash: str) -> bool
```


Check if cache is valid for the current configuration.

Compares the stored config_hash with the current configuration hash.
If they differ, the cache is automatically cleared to ensure correctness.

This enables automatic cache invalidation when:
- Configuration files change (bengal.toml, config/*.yaml)
- Environment variables change (BENGAL_*)
- Build profiles change (--profile writer)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_hash` | `str` | - | Hash of the current resolved configuration |







**Returns**


`bool` - True if cache is valid (hashes match), False if cache was cleared
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> from bengal.config.hash import compute_config_hash
    >>> config_hash = compute_config_hash(site.config)
    >>> if not cache.validate_config(config_hash):
    ...     logger.info("Config changed, performing full rebuild")
```




#### `invalidate_file`
```python
def invalidate_file(self, file_path: Path) -> None
```


Remove a file from the cache (useful when file is deleted).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







**Returns**


`None`



#### `get_stats`
```python
def get_stats(self) -> dict[str, int]
```


Get cache statistics with logging.



**Returns**


`dict[str, int]` - Dictionary with cache stats



#### `get_page_cache`
```python
def get_page_cache(self, cache_key: str) -> dict[str, Any] | None
```


Get cached data for a synthetic page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_key` | `str` | - | Unique cache key for the page |







**Returns**


`dict[str, Any] | None` - Cached page data or None if not found



#### `set_page_cache`
```python
def set_page_cache(self, cache_key: str, page_data: dict[str, Any]) -> None
```


Cache data for a synthetic page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_key` | `str` | - | Unique cache key for the page |
| `page_data` | `dict[str, Any]` | - | Page data to cache |







**Returns**


`None`



#### `invalidate_page_cache`
```python
def invalidate_page_cache(self, cache_key: str) -> None
```


Remove cached data for a synthetic page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_key` | `str` | - | Cache key to invalidate |







**Returns**


`None`



#### `__repr__`
```python
def __repr__(self) -> str
```


*No description provided.*



**Returns**


`str`



#### `store_parsed_content`
```python
def store_parsed_content(self, file_path: Path, html: str, toc: str, toc_items: list[dict[str, Any]], metadata: dict[str, Any], template: str, parser_version: str, ast: list[dict[str, Any]] | None = None) -> None
```


Store parsed content in cache (Optimization #2 + AST caching).

This allows skipping markdown parsing when only templates change,
resulting in 20-30% faster builds in that scenario.

Phase 3 Enhancement (RFC-content-ast-architecture):
- Also caches the true AST for parse-once, use-many patterns
- AST enables faster TOC/link extraction and plain text generation


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to source file |
| `html` | `str` | - | Rendered HTML (post-markdown, pre-template) |
| `toc` | `str` | - | Table of contents HTML |
| `toc_items` | `list[dict[str, Any]]` | - | Structured TOC data |
| `metadata` | `dict[str, Any]` | - | Page metadata (frontmatter) |
| `template` | `str` | - | Template name used |
| `parser_version` | `str` | - | Parser version string (e.g., "mistune-3.0-toc2") |
| `ast` | `list[dict[str, Any]] \| None` | - | True AST tokens from parser (optional, for Phase 3) |







**Returns**


`None`



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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to source file |
| `metadata` | `dict[str, Any]` | - | Current page metadata |
| `template` | `str` | - | Current template name |
| `parser_version` | `str` | - | Current parser version |







**Returns**


`dict[str, Any] | None` - Cached data dict if valid, None if invalid or not found



#### `invalidate_parsed_content`
```python
def invalidate_parsed_content(self, file_path: Path) -> None
```


Remove cached parsed content for a file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







**Returns**


`None`



#### `get_parsed_content_stats`
```python
def get_parsed_content_stats(self) -> dict[str, Any]
```


Get parsed content cache statistics.



**Returns**


`dict[str, Any]` - Dictionary with cache stats



---
*Generated by Bengal autodoc from `bengal/bengal/cache/build_cache.py`*

