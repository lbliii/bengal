
---
title: "dependency_tracker"
type: "python-module"
source_file: "bengal/cache/dependency_tracker.py"
line_number: 1
description: "Dependency tracker for build process dependency management. Tracks template, partial, and data file dependencies during rendering to enable incremental builds. Records dependencies in BuildCache for c..."
---

# dependency_tracker
**Type:** Module
**Source:** [View source](bengal/cache/dependency_tracker.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[cache](/api/bengal/cache/) ›dependency_tracker

Dependency tracker for build process dependency management.

Tracks template, partial, and data file dependencies during rendering to enable
incremental builds. Records dependencies in BuildCache for change detection
and selective rebuilding.

Key Concepts:
    - Dependency tracking: Template and data file dependencies per page
    - Thread-safe tracking: Thread-local storage for parallel rendering
    - Cache integration: Dependencies stored in BuildCache
    - Incremental builds: Dependency changes trigger selective rebuilds

Related Modules:
    - bengal.cache.build_cache: Build cache persistence
    - bengal.orchestration.incremental: Incremental build logic
    - bengal.rendering.pipeline: Rendering pipeline using dependency tracking

See Also:
    - bengal/cache/dependency_tracker.py:DependencyTracker for tracking logic
    - plan/active/rfc-incremental-builds.md: Incremental build design

## Classes




### `CacheInvalidator`


Cache invalidation logic for incremental builds.

Tracks invalidated paths based on content, template, and config changes.
Provides methods for selective invalidation and full cache invalidation.

Creation:
    Direct instantiation: CacheInvalidator(config_hash, content_paths, template_paths)
        - Created by DependencyTracker for cache invalidation
        - Requires config hash and path lists



**Attributes:**

:::{div} api-attributes
`config_hash`
: Hash of configuration for config change detection

`content_paths`
: List of content file paths

`template_paths`
: List of template file paths

`invalidated`
: Set of invalidated paths

`Relationships`
: - Used by: DependencyTracker for cache invalidation - Uses: Path sets for invalidation tracking

:::




:::{rubric} Properties
:class: rubric-properties
:::



#### `is_stale` @property

```python
def is_stale(self) -> bool
```
Invariant: Check if cache needs rebuild.




## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, config_hash: str, content_paths: list[Path], template_paths: list[Path])
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `config_hash` | `str` | - | *No description provided.* |
| `content_paths` | `list[Path]` | - | *No description provided.* |
| `template_paths` | `list[Path]` | - | *No description provided.* |








#### `invalidate_content`

:::{div} api-badge-group
:::

```python
def invalidate_content(self, changed_paths: set[Path]) -> set[Path]
```


Invalidate on content changes.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `changed_paths` | `set[Path]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`set[Path]`



#### `invalidate_templates`

:::{div} api-badge-group
:::

```python
def invalidate_templates(self, changed_paths: set[Path]) -> set[Path]
```


Invalidate dependent pages on template changes.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `changed_paths` | `set[Path]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`set[Path]`



#### `invalidate_config`

:::{div} api-badge-group
:::

```python
def invalidate_config(self) -> set[Path]
```


Full invalidation on config change.



:::{rubric} Returns
:class: rubric-returns
:::


`set[Path]`




### `DependencyTracker`


Tracks dependencies between pages and their templates, partials, and config files.

Records template and data file dependencies during rendering to enable incremental
builds. Uses thread-local storage for thread-safe parallel rendering and maintains
dependency graphs for change detection.

Creation:
    Direct instantiation: DependencyTracker(cache, site=None)
        - Created by IncrementalOrchestrator for dependency tracking
        - Requires BuildCache instance for dependency storage



**Attributes:**

:::{div} api-attributes
`cache`
: BuildCache instance for dependency storage

`site`
: Optional Site instance for config path access

`logger`
: Logger instance for dependency tracking events

`tracked_files`
: Mapping of file paths to page paths

`dependencies`
: Forward dependency graph (page → dependencies)

`reverse_dependencies`
: Reverse dependency graph (dependency → pages)

`current_page`
: Thread-local current page being processed

`invalidator`
: CacheInvalidator for cache invalidation

`Relationships`
: - Uses: BuildCache for dependency persistence - Used by: RenderingPipeline for dependency tracking during rendering - Used by: IncrementalOrchestrator for change detection Thread Safety: Thread-safe. Uses thread-local storage for current page tracking and thread-safe locks for dependency graph updates.

:::







## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, cache: BuildCache, site = None)
```


Initialize the dependency tracker.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `cache` | `BuildCache` | - | BuildCache instance to store dependencies in |
| `site` | - | - | Optional Site instance to get config path from |









#### `start_page`

:::{div} api-badge-group
:::

```python
def start_page(self, page_path: Path) -> None
```


Mark the start of processing a page (thread-safe).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to the page being processed |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_template`

:::{div} api-badge-group
:::

```python
def track_template(self, template_path: Path) -> None
```


Record that the current page depends on a template (thread-safe).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `template_path` | `Path` | - | Path to the template file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_partial`

:::{div} api-badge-group
:::

```python
def track_partial(self, partial_path: Path) -> None
```


Record that the current page depends on a partial/include (thread-safe).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `partial_path` | `Path` | - | Path to the partial file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_config`

:::{div} api-badge-group
:::

```python
def track_config(self, config_path: Path) -> None
```


Record that the current page depends on the config file (thread-safe).
All pages depend on config, so this marks it as a global dependency.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `config_path` | `Path` | - | Path to the config file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_asset`

:::{div} api-badge-group
:::

```python
def track_asset(self, asset_path: Path) -> None
```


Record an asset file (for cache invalidation).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `asset_path` | `Path` | - | Path to the asset file |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `track_taxonomy`

:::{div} api-badge-group
:::

```python
def track_taxonomy(self, page_path: Path, tags: set[str]) -> None
```


Record taxonomy (tags/categories) dependencies.

When a page's tags change, tag pages need to be regenerated.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_path` | `Path` | - | Path to the page |
| `tags` | `set[str]` | - | Set of tags/categories for this page |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `end_page`

:::{div} api-badge-group
:::

```python
def end_page(self) -> None
```


Mark the end of processing a page (thread-safe).



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `get_changed_files`

:::{div} api-badge-group
:::

```python
def get_changed_files(self, root_path: Path) -> set[Path]
```


Get all files that have changed since the last build.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `root_path` | `Path` | - | Root path of the site |







:::{rubric} Returns
:class: rubric-returns
:::


`set[Path]` - Set of paths that have changed



#### `find_new_files`

:::{div} api-badge-group
:::

```python
def find_new_files(self, current_files: set[Path]) -> set[Path]
```


Find files that are new (not in cache).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_files` | `set[Path]` | - | Set of current file paths |







:::{rubric} Returns
:class: rubric-returns
:::


`set[Path]` - Set of new file paths



#### `find_deleted_files`

:::{div} api-badge-group
:::

```python
def find_deleted_files(self, current_files: set[Path]) -> set[Path]
```


Find files that were deleted (in cache but not on disk).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_files` | `set[Path]` | - | Set of current file paths |







:::{rubric} Returns
:class: rubric-returns
:::


`set[Path]` - Set of deleted file paths



---
*Generated by Bengal autodoc from `bengal/cache/dependency_tracker.py`*

