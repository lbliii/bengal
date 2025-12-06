
---
title: "build_context"
type: "python-module"
source_file: "bengal/bengal/utils/build_context.py"
line_number: 1
description: "Build context for sharing state across build phases. Provides BuildContext dataclass for passing shared state between build phases, replacing scattered local variables. Created at build start and popu..."
---

# build_context
**Type:** Module
**Source:** [View source](bengal/bengal/utils/build_context.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›build_context

Build context for sharing state across build phases.

Provides BuildContext dataclass for passing shared state between build phases,
replacing scattered local variables. Created at build start and populated
incrementally as phases execute.

Key Concepts:
    - Shared context: Single context object passed to all build phases
    - Phase coordination: Enables phase-to-phase communication
    - State management: Centralized build state management
    - Lifecycle: Created at build start, populated during phases
    - Lazy artifacts: Expensive computations cached on first access

Related Modules:
    - bengal.orchestration.build: Build orchestration using BuildContext
    - bengal.utils.build_stats: Build statistics collection
    - bengal.utils.progress: Progress reporting

See Also:
    - bengal/utils/build_context.py:BuildContext for context structure
    - plan/active/rfc-build-pipeline.md: Build pipeline design
    - plan/active/rfc-lazy-build-artifacts.md: Lazy artifact design

## Classes




### `BuildContext`


Shared build context passed across build phases.

This context is created at the start of build() and passed to all _phase_* methods.
It replaces local variables that were scattered throughout the 894-line build() method.

Lifecycle:
    1. Created in _setup_build_context() at build start
    2. Populated incrementally as phases execute
    3. Used by all _phase_* methods for shared state

Categories:
    - Core: site, stats, profile (required)
    - Cache: cache, tracker (initialized in Phase 0)
    - Build mode: incremental, verbose, quiet, strict, parallel
    - Work items: pages_to_build, assets_to_process (determined in Phase 2)
    - Incremental state: affected_tags, affected_sections, changed_page_paths
    - Output: cli, progress_manager, reporter


:::{info}
This is a dataclass.
:::



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `site` | - | *No description provided.* |
| `stats` | - | *No description provided.* |
| `profile` | - | *No description provided.* |
| `cache` | - | *No description provided.* |
| `tracker` | - | *No description provided.* |
| `incremental` | - | *No description provided.* |
| `verbose` | - | *No description provided.* |
| `quiet` | - | *No description provided.* |
| `strict` | - | *No description provided.* |
| `parallel` | - | *No description provided.* |
| `memory_optimized` | - | *No description provided.* |
| `full_output` | - | *No description provided.* |
| `profile_templates` | - | *No description provided.* |
| `pages` | - | *No description provided.* |
| `pages_to_build` | - | *No description provided.* |
| `assets` | - | *No description provided.* |
| `assets_to_process` | - | *No description provided.* |
| `affected_tags` | - | *No description provided.* |
| `affected_sections` | - | *No description provided.* |
| `changed_page_paths` | - | *No description provided.* |
| `config_changed` | - | *No description provided.* |
| `cli` | - | *No description provided.* |
| `progress_manager` | - | *No description provided.* |
| `reporter` | - | *No description provided.* |
| `build_start` | - | *No description provided.* |
| `_knowledge_graph` | - | *No description provided.* |
| `_knowledge_graph_enabled` | - | *No description provided.* |
| `_page_contents` | - | *No description provided.* |
| `_content_cache_lock` | - | *No description provided.* |
| `_accumulated_page_json` | - | *No description provided.* |
| `_accumulated_json_lock` | - | *No description provided.* |




:::{rubric} Properties
:class: rubric-properties
:::



#### `knowledge_graph` @property

```python
def knowledge_graph(self) -> KnowledgeGraph | None
```
Get knowledge graph (built lazily, cached for build duration).

The knowledge graph is expensive to build (~200-500ms for 773 pages).
By caching it here, we avoid rebuilding it 3 times per build
(post-processing, special pages, health check).

#### `content_cache_size` @property

```python
def content_cache_size(self) -> int
```
Get number of cached content entries.

#### `has_cached_content` @property

```python
def has_cached_content(self) -> bool
```
Check if content cache has any entries.

Validators can use this to decide whether to use cache or fallback.

#### `has_accumulated_json` @property

```python
def has_accumulated_json(self) -> bool
```
Check if accumulated JSON data exists.

Post-processing can use this to decide whether to use accumulated
data or fall back to computing from pages.




## Methods



#### `knowledge_graph`
```python
def knowledge_graph(self) -> KnowledgeGraph | None
```


Get knowledge graph (built lazily, cached for build duration).

The knowledge graph is expensive to build (~200-500ms for 773 pages).
By caching it here, we avoid rebuilding it 3 times per build
(post-processing, special pages, health check).



**Returns**


`KnowledgeGraph | None` - Built KnowledgeGraph instance, or None if disabled/unavailable
:::{rubric} Examples
:class: rubric-examples
:::


```python
# First access builds the graph
    graph = ctx.knowledge_graph

    # Subsequent accesses reuse cached instance
    graph2 = ctx.knowledge_graph  # Same instance, no rebuild
```




#### `content_cache_size`
```python
def content_cache_size(self) -> int
```


Get number of cached content entries.



**Returns**


`int` - Number of files with cached content



#### `has_cached_content`
```python
def has_cached_content(self) -> bool
```


Check if content cache has any entries.

Validators can use this to decide whether to use cache or fallback.



**Returns**


`bool` - True if cache has content



#### `has_accumulated_json`
```python
def has_accumulated_json(self) -> bool
```


Check if accumulated JSON data exists.

Post-processing can use this to decide whether to use accumulated
data or fall back to computing from pages.



**Returns**


`bool` - True if accumulated JSON data exists




#### `clear_lazy_artifacts`
```python
def clear_lazy_artifacts(self) -> None
```


Clear lazy-computed artifacts to free memory.

Call this at the end of a build to release memory used by
cached artifacts like the knowledge graph and content cache.



**Returns**


`None`



#### `cache_content`
```python
def cache_content(self, source_path: Path, content: str) -> None
```


Cache raw content during discovery phase (thread-safe).

Call this during content discovery to store file content for later
use by validators. This eliminates redundant disk I/O during health
checks.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file (used as cache key) |
| `content` | `str` | - | Raw file content to cache |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
# During content discovery
    content = file_path.read_text()
    if build_context:
        build_context.cache_content(file_path, content)
```




#### `get_content`
```python
def get_content(self, source_path: Path) -> str | None
```


Get cached content without disk I/O.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `source_path` | `Path` | - | Path to source file |







**Returns**


`str | None` - Cached content string, or None if not cached
:::{rubric} Examples
:class: rubric-examples
:::


```python
# In validator
    content = build_context.get_content(page.source_path)
    if content is None:
        content = page.source_path.read_text()  # Fallback
```




#### `get_all_cached_contents`
```python
def get_all_cached_contents(self) -> dict[str, str]
```


Get a copy of all cached contents for batch processing.

Returns a copy to avoid thread safety issues when iterating.



**Returns**


`dict[str, str]` - Dictionary mapping source path strings to content
:::{rubric} Examples
:class: rubric-examples
:::


```python
# In DirectiveAnalyzer
    all_contents = build_context.get_all_cached_contents()
    for path, content in all_contents.items():
        directives = self._extract_directives(content, Path(path))
```




#### `clear_content_cache`
```python
def clear_content_cache(self) -> None
```


Clear content cache to free memory.

Call this after validation phase completes to release memory
used by cached file contents.



**Returns**


`None`



#### `accumulate_page_json`
```python
def accumulate_page_json(self, json_path: Any, page_data: dict[str, Any]) -> None
```


Accumulate JSON data for a page during rendering (thread-safe).

Call this during rendering phase to store JSON data for later
use in post-processing. This eliminates redundant computation
and double iteration of pages.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `json_path` | `Any` | - | Path where JSON file should be written |
| `page_data` | `dict[str, Any]` | - | Pre-computed JSON data dictionary |







**Returns**


`None`
:::{rubric} Examples
:class: rubric-examples
:::


```python
# During rendering phase
    json_path = get_page_json_path(page)
    page_data = build_page_json_data(page)
    if build_context:
        build_context.accumulate_page_json(json_path, page_data)
```




#### `get_accumulated_json`
```python
def get_accumulated_json(self) -> list[tuple[Any, dict[str, Any]]]
```


Get all accumulated JSON data for post-processing.

Returns a copy to avoid thread safety issues when iterating.



**Returns**


`list[tuple[Any, dict[str, Any]]]` - List of (json_path, page_data) tuples
:::{rubric} Examples
:class: rubric-examples
:::


```python
# In post-processing phase
    accumulated = build_context.get_accumulated_json()
    for json_path, page_data in accumulated:
        write_json(json_path, page_data)
```




#### `clear_accumulated_json`
```python
def clear_accumulated_json(self) -> None
```


Clear accumulated JSON data to free memory.

Call this after post-processing phase completes to release memory
used by accumulated JSON data.



**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/utils/build_context.py`*
