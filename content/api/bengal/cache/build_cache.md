
---
title: "build_cache"
type: "python-module"
source_file: "bengal/cache/build_cache.py"
line_number: 1
description: "Build cache for tracking file changes and dependencies in incremental builds. Maintains file hashes, dependency graphs, taxonomy indexes, and validation results across builds. Uses Zstandard-compresse..."
---

# build_cache
**Type:** Module
**Source:** [View source](bengal/cache/build_cache.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›build_cache

Build cache for tracking file changes and dependencies in incremental builds.

Maintains file hashes, dependency graphs, taxonomy indexes, and validation
results across builds. Uses Zstandard-compressed JSON for persistence and
provides tolerant loading for version migrations.

Key Concepts:
    - File fingerprints: mtime + size for fast change detection, hash for verification
    - Dependency tracking: Templates, partials, and data files used by pages
    - Taxonomy indexes: Tag/category mappings for fast reconstruction
    - Config hash: Auto-invalidation when configuration changes
    - Version tolerance: Accepts missing/older cache versions gracefully
    - Zstandard compression: 92-93% size reduction, <1ms overhead

Performance Optimization (RFC: orchestrator-performance-improvements):
    - Fast path: mtime + size check (no I/O beyond stat)
    - Slow path: SHA256 hash only when mtime/size mismatch suggests change
    - Expected improvement: 10-30% faster incremental build detection
    - Compression: 12-14x smaller cache files, faster I/O

Related Modules:
    - bengal.orchestration.incremental: Incremental build logic using cache
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.cache.taxonomy_index: Taxonomy reconstruction from cache
    - bengal.cache.compression: Zstandard compression utilities

See Also:
    - bengal/cache/build_cache.py:BuildCache class for cache structure
    - plan/active/rfc-incremental-builds.md: Incremental build design
    - plan/active/rfc-orchestrator-performance-improvements.md: Performance RFC
    - plan/active/rfc-zstd-cache-compression.md: Compression RFC

## Classes




### `FileFingerprint`


Fast file change detection using mtime + size, with optional hash verification.

Performance Optimization:
    - mtime + size comparison is O(1) stat call (no file read)
    - Hash computed lazily only when mtime/size mismatch detected
    - Handles edge cases like touch/rsync that change mtime but not content


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`mtime`
: File modification time (seconds since epoch)

`size`
: File size in bytes

`hash`
: SHA256 hash (computed lazily, may be None for fast path) Thread Safety: Immutable after creation. Thread-safe for read operations.

:::







## Methods



#### `matches_stat`

:::{div} api-badge-group
:::

```python
def matches_stat(self, stat_result) -> bool
```


Fast path check: does mtime + size match?


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `stat_result` | - | - | Result from Path.stat() |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if mtime and size both match (definitely unchanged)



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


Serialize to JSON-compatible dict.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `from_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def from_dict(cls, data: dict[str, Any]) -> FileFingerprint
```


Deserialize from JSON dict.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`FileFingerprint`



#### `from_path`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def from_path(cls, file_path: Path, compute_hash: bool = True) -> FileFingerprint
```


Create fingerprint from file path.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |
| `compute_hash` | `bool` | `True` | Whether to compute SHA256 hash (slower but more reliable) |







:::{rubric} Returns
:class: rubric-returns
:::


`FileFingerprint` - FileFingerprint with mtime, size, and optionally hash




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

:::{div} api-attributes
`VERSION`
: 

`version`
: 

`file_hashes`
: Mapping of file paths to their SHA256 hashes

`file_fingerprints`
: 

`dependencies`
: Mapping of pages to their dependencies (templates, partials, etc.)

`output_sources`
: Mapping of output files to their source files

`taxonomy_deps`
: Mapping of taxonomy terms to affected pages

`page_tags`
: Mapping of page paths to their tags (for detecting tag changes)

`tag_to_pages`
: Inverted index mapping tag slug to page paths (for O(1) reconstruction)

`known_tags`
: Set of all tag slugs from previous build (for detecting deletions)

`parsed_content`
: Cached parsed HTML/TOC (Optimization #2)

`rendered_output`
: 

`synthetic_pages`
: 

`validation_results`
: 

`config_hash`
: Hash of resolved configuration (for auto-invalidation)

`last_build`
: Timestamp of last successful build

:::







## Methods



#### `__post_init__`

:::{div} api-badge-group
:::

```python
def __post_init__(self) -> None
```


Convert sets from lists after JSON deserialization.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `load`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`BuildCache` - BuildCache instance (empty if file doesn't exist or is invalid)





#### `save`

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`IOError`**:If cache file cannot be written json.JSONEncodeError: If cache data cannot be serialized
- **`LockAcquisitionError`**:If lock cannot be acquired (when use_lock=True)





#### `hash_file`

:::{div} api-badge-group
:::

```python
def hash_file(self, file_path: Path) -> str
```


Generate SHA256 hash of a file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







:::{rubric} Returns
:class: rubric-returns
:::


`str` - Hex string of SHA256 hash



#### `is_changed`

:::{div} api-badge-group
:::

```python
def is_changed(self, file_path: Path) -> bool
```


Check if a file has changed since last build.

Performance Optimization (RFC: orchestrator-performance-improvements):
    - Fast path: mtime + size check (single stat call, no file read)
    - Slow path: SHA256 hash only when mtime/size mismatch detected
    - Handles edge cases: touch/rsync may change mtime but not content


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if file is new or has changed, False if unchanged



#### `update_file`

:::{div} api-badge-group
:::

```python
def update_file(self, file_path: Path) -> None
```


Update the fingerprint for a file (mtime + size + hash).

Performance Optimization:
    Stores full fingerprint for fast change detection on subsequent builds.
    Uses mtime + size for fast path, hash for verification.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_cached_validation_results`

:::{div} api-badge-group
:::

```python
def get_cached_validation_results(self, file_path: Path, validator_name: str) -> list[dict[str, Any]] | None
```


Get cached validation results for a file and validator.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |
| `validator_name` | `str` | - | Name of validator |







:::{rubric} Returns
:class: rubric-returns
:::


`list[dict[str, Any]] | None` - List of CheckResult dicts if cached and file unchanged, None otherwise



#### `cache_validation_results`

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `invalidate_validation_results`

:::{div} api-badge-group
:::

```python
def invalidate_validation_results(self, file_path: Path | None = None) -> None
```


Invalidate validation results for a file or all files.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path \| None` | - | Path to file (if None, invalidate all) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_output`

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `add_dependency`

:::{div} api-badge-group
:::

```python
def add_dependency(self, source: Path, dependency: Path) -> None
```


Record that a source file depends on another file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source` | `Path` | - | Source file (e.g., content page) |
| `dependency` | `Path` | - | Dependency file (e.g., template, partial, config) |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `add_taxonomy_dependency`

:::{div} api-badge-group
:::

```python
def add_taxonomy_dependency(self, taxonomy_term: str, page: Path) -> None
```


Record that a taxonomy term affects a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `taxonomy_term` | `str` | - | Taxonomy term (e.g., "tag:python") |
| `page` | `Path` | - | Page that uses this taxonomy term |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_affected_pages`

:::{div} api-badge-group
:::

```python
def get_affected_pages(self, changed_file: Path) -> set[str]
```


Find all pages that depend on a changed file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `changed_file` | `Path` | - | File that changed |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of page paths that need to be rebuilt



#### `get_previous_tags`

:::{div} api-badge-group
:::

```python
def get_previous_tags(self, page_path: Path) -> set[str]
```


Get tags from previous build for a page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of tags from previous build (empty set if new page)



#### `update_tags`

:::{div} api-badge-group
:::

```python
def update_tags(self, page_path: Path, tags: set[str]) -> None
```


Store current tags for a page (for next build's comparison).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to page |
| `tags` | `set[str]` | - | Current set of tags for the page |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `update_page_tags`

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of affected tag slugs (tags added, removed, or modified)



#### `get_pages_for_tag`

:::{div} api-badge-group
:::

```python
def get_pages_for_tag(self, tag_slug: str) -> set[str]
```


Get all page paths for a given tag.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `tag_slug` | `str` | - | Tag slug (e.g., 'python', 'web-dev') |







:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of page path strings



#### `get_all_tags`

:::{div} api-badge-group
:::

```python
def get_all_tags(self) -> set[str]
```


Get all known tag slugs from previous build.



:::{rubric} Returns
:class: rubric-returns
:::


`set[str]` - Set of tag slugs



#### `clear`

:::{div} api-badge-group
:::

```python
def clear(self) -> None
```


Clear all cache data.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `validate_config`

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


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

:::{div} api-badge-group
:::

```python
def invalidate_file(self, file_path: Path) -> None
```


Remove a file from the cache (useful when file is deleted).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_stats`

:::{div} api-badge-group
:::

```python
def get_stats(self) -> dict[str, int]
```


Get cache statistics with logging.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, int]` - Dictionary with cache stats



#### `get_page_cache`

:::{div} api-badge-group
:::

```python
def get_page_cache(self, cache_key: str) -> dict[str, Any] | None
```


Get cached data for a synthetic page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_key` | `str` | - | Unique cache key for the page |







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any] | None` - Cached page data or None if not found



#### `set_page_cache`

:::{div} api-badge-group
:::

```python
def set_page_cache(self, cache_key: str, page_data: dict[str, Any]) -> None
```


Cache data for a synthetic page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_key` | `str` | - | Unique cache key for the page |
| `page_data` | `dict[str, Any]` | - | Page data to cache |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `invalidate_page_cache`

:::{div} api-badge-group
:::

```python
def invalidate_page_cache(self, cache_key: str) -> None
```


Remove cached data for a synthetic page.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache_key` | `str` | - | Cache key to invalidate |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



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



#### `store_parsed_content`

:::{div} api-badge-group
:::

```python
def store_parsed_content(self, file_path: Path, html: str, toc: str, toc_items: list[dict[str, Any]], metadata: dict[str, Any], template: str, parser_version: str, ast: list[dict[str, Any]] | None = None) -> None
```


Store parsed content in cache (Optimization #2 + AST caching).

This allows skipping markdown parsing when only templates change,
resulting in 20-30% faster builds in that scenario.

Phase 3 Enhancement (RFC-content-ast-architecture):
- Also caches the true AST for parse-once, use-many patterns
- AST enables faster TOC/link extraction and plain text generation


**Parameters**

::::{dropdown} 8 parameters (click to expand)
:open: true

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



::::






:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_parsed_content`

:::{div} api-badge-group
:::

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







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any] | None` - Cached data dict if valid, None if invalid or not found



#### `invalidate_parsed_content`

:::{div} api-badge-group
:::

```python
def invalidate_parsed_content(self, file_path: Path) -> None
```


Remove cached parsed content for a file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_parsed_content_stats`

:::{div} api-badge-group
:::

```python
def get_parsed_content_stats(self) -> dict[str, Any]
```


Get parsed content cache statistics.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Dictionary with cache stats



#### `store_rendered_output`

:::{div} api-badge-group
:::

```python
def store_rendered_output(self, file_path: Path, html: str, template: str, metadata: dict[str, Any], dependencies: list[str] | None = None) -> None
```


Store fully rendered HTML output in cache.

This allows skipping BOTH markdown parsing AND template rendering for
pages where content, template, and metadata are unchanged. Expected
to provide 20-40% faster incremental builds.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to source file |
| `html` | `str` | - | Fully rendered HTML (post-template, ready to write) |
| `template` | `str` | - | Template name used for rendering |
| `metadata` | `dict[str, Any]` | - | Page metadata (frontmatter) |
| `dependencies` | `list[str] \| None` | - | List of template/partial paths this page depends on |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_rendered_output`

:::{div} api-badge-group
:::

```python
def get_rendered_output(self, file_path: Path, template: str, metadata: dict[str, Any]) -> str | None
```


Get cached rendered HTML if still valid.

Validates that:
1. Content file hasn't changed (via file_fingerprints)
2. Metadata hasn't changed (via metadata_hash)
3. Template name matches
4. Template files haven't changed (via dependencies)
5. Config hasn't changed (caller should validate config_hash)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to source file |
| `template` | `str` | - | Current template name |
| `metadata` | `dict[str, Any]` | - | Current page metadata |







:::{rubric} Returns
:class: rubric-returns
:::


`str | None` - Cached HTML string if valid, None if invalid or not found



#### `invalidate_rendered_output`

:::{div} api-badge-group
:::

```python
def invalidate_rendered_output(self, file_path: Path) -> None
```


Remove cached rendered output for a file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `file_path` | `Path` | - | Path to file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_rendered_output_stats`

:::{div} api-badge-group
:::

```python
def get_rendered_output_stats(self) -> dict[str, Any]
```


Get rendered output cache statistics.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Dictionary with cache stats



---
*Generated by Bengal autodoc from `bengal/cache/build_cache.py`*

