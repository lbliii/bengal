
---
title: "incremental"
type: "python-module"
source_file: "bengal/orchestration/incremental.py"
line_number: 1
description: "Incremental build orchestration for Bengal SSG. Handles cache management, change detection, and determining what needs rebuilding. Uses file hashes, dependency graphs, and taxonomy indexes to identify..."
---

# incremental
**Type:** Module
**Source:** [View source](bengal/orchestration/incremental.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[orchestration](/api/bengal/orchestration/) ›incremental

Incremental build orchestration for Bengal SSG.

Handles cache management, change detection, and determining what needs rebuilding.
Uses file hashes, dependency graphs, and taxonomy indexes to identify changed
content and minimize rebuild work. Supports both full and incremental builds.

Key Concepts:
    - Change detection: File hash comparison for content changes
    - Dependency tracking: Template and data file dependencies
    - Taxonomy invalidation: Tag/category change detection
    - Selective rebuilding: Only rebuild changed pages and dependencies

Related Modules:
    - bengal.cache.build_cache: Build cache persistence
    - bengal.cache.dependency_tracker: Dependency graph construction
    - bengal.orchestration.build: Build orchestration entry point

See Also:
    - bengal/orchestration/incremental.py:IncrementalOrchestrator for incremental logic
    - plan/active/rfc-incremental-builds.md: Incremental build design

## Classes




### `IncrementalOrchestrator`


Orchestrates incremental build logic for efficient rebuilds.

Handles cache initialization, change detection, dependency tracking, and
selective rebuilding. Uses file hashes, dependency graphs, and taxonomy
indexes to minimize rebuild work by only rebuilding changed content.

Creation:
    Direct instantiation: IncrementalOrchestrator(site)
        - Created by BuildOrchestrator when incremental builds enabled
        - Requires Site instance with content populated



**Attributes:**

:::{div} api-attributes
`site`
: Site instance for incremental builds

`cache`
: BuildCache instance for build state persistence

`tracker`
: DependencyTracker instance for dependency graph construction

`logger`
: Logger instance for incremental build events

`Relationships`
: - Uses: BuildCache for build state persistence - Uses: DependencyTracker for dependency graph construction - Used by: BuildOrchestrator for incremental build coordination - Uses: Site for content access and change detection Thread Safety: Not thread-safe. Should be used from single thread during build. Cache and tracker operations are thread-safe internally.

:::







## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, site: Site)
```


Initialize incremental orchestrator.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `site` | `Site` | - | Site instance for incremental builds |








#### `initialize`

:::{div} api-badge-group
:::

```python
def initialize(self, enabled: bool = False) -> tuple[BuildCache, DependencyTracker]
```


Initialize cache and dependency tracker for incremental builds.

Sets up BuildCache and DependencyTracker instances. If enabled, loads
existing cache from .bengal/cache.json (migrates from legacy location
if needed). If disabled, creates empty cache instances.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `enabled` | `bool` | `False` | Whether incremental builds are enabled. If False, creates empty cache instances (full rebuilds always). |







:::{rubric} Returns
:class: rubric-returns
:::


`tuple[BuildCache, DependencyTracker]` - Tuple of (BuildCache, DependencyTracker) instances

Process:
    1. Create .bengal/ directory if enabled
    2. Migrate legacy cache from output_dir/.bengal-cache.json if exists
    3. Load or create BuildCache instance
    4. Create DependencyTracker with cache and site
:::{rubric} Examples
:class: rubric-examples
:::


```python
cache, tracker = orchestrator.initialize(enabled=True)
    # Cache loaded from .bengal/cache.json if exists
```




#### `check_config_changed`

:::{div} api-badge-group
:::

```python
def check_config_changed(self) -> bool
```


Check if configuration has changed (requires full rebuild).

Uses config hash validation which captures the *effective* configuration state:
- Base config from files (bengal.toml, config/*.yaml)
- Environment variable overrides (BENGAL_*)
- Build profile settings (--profile writer)

This is more robust than file-based tracking because it detects changes
in split config files, env vars, and profiles that wouldn't trigger
a file hash change.



:::{rubric} Returns
:class: rubric-returns
:::


`bool` - True if config changed (cache was invalidated)




#### `find_work_early`

:::{div} api-badge-group
:::

```python
def find_work_early(self, verbose: bool = False) -> tuple[list[Page], list[Asset], dict[str, list]]
```


Find pages/assets that need rebuilding (early version - before taxonomy generation).

This is called BEFORE taxonomies/menus are generated, so it only checks content/asset changes.
Generated pages (tags, etc.) will be determined later based on affected tags.

Uses section-level optimization: skips checking individual pages in unchanged sections.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `verbose` | `bool` | `False` | Whether to collect detailed change information |







:::{rubric} Returns
:class: rubric-returns
:::


`tuple[list[Page], list[Asset], dict[str, list]]` - Tuple of (pages_to_build, assets_to_process, change_summary)



#### `find_work`

:::{div} api-badge-group
:::

```python
def find_work(self, verbose: bool = False) -> tuple[list[Page], list[Asset], dict[str, list]]
```


Find pages/assets that need rebuilding (legacy version - after taxonomy generation).

This is the old method that expects generated pages to already exist.
Kept for backward compatibility but should be replaced with find_work_early().


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `verbose` | `bool` | `False` | Whether to collect detailed change information |







:::{rubric} Returns
:class: rubric-returns
:::


`tuple[list[Page], list[Asset], dict[str, list]]` - Tuple of (pages_to_build, assets_to_process, change_summary)



#### `process`

:::{div} api-badge-group
:::

```python
def process(self, change_type: str, changed_paths: set) -> None
```


Bridge-style process for testing incremental invalidation.

⚠️  TEST BRIDGE ONLY
========================
This method is a lightweight adapter used in tests to simulate an
incremental pass without invoking the entire site build orchestrator.

**Not for production use:**
- Writes placeholder output ("Updated") for verification only
- Does not perform full rendering or asset processing
- Skips postprocessing (RSS, sitemap, etc.)
- Use run() or full_build() for production builds

**Primarily consumed by:**
- tests/integration/test_full_to_incremental_sequence.py
- bengal/orchestration/full_to_incremental.py (test bridge helper)
- Test scenarios validating cache invalidation logic


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `change_type` | `str` | - | One of "content", "template", or "config" |
| `changed_paths` | `set` | - | Set of paths that changed (ignored for "config") |







:::{rubric} Returns
:class: rubric-returns
:::


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`RuntimeError`**:If tracker not initialized (call initialize() first)





#### `full_rebuild`

:::{div} api-badge-group
:::

```python
def full_rebuild(self, pages: list, context: BuildContext)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list` | - | *No description provided.* |
| `context` | `BuildContext` | - | *No description provided.* |









#### `save_cache`

:::{div} api-badge-group
:::

```python
def save_cache(self, pages_built: list[Page], assets_processed: list[Asset]) -> None
```


Update cache with processed files.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages_built` | `list[Page]` | - | Pages that were built |
| `assets_processed` | `list[Asset]` | - | Assets that were processed |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



---
*Generated by Bengal autodoc from `bengal/orchestration/incremental.py`*

