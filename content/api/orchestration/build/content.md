
---
title: "content"
type: "python-module"
source_file: "bengal/orchestration/build/content.py"
line_number: 1
description: "Content phases for build orchestration. Phases 6-11: Sections, taxonomies, menus, related posts, query indexes, update pages list."
---

# content
**Type:** Module
**Source:** [View source](bengal/orchestration/build/content.py#L1)



**Navigation:**
[orchestration](/api/orchestration/) ›[build](/api/orchestration/build/) ›content

Content phases for build orchestration.

Phases 6-11: Sections, taxonomies, menus, related posts, query indexes, update pages list.

## Functions



### `phase_sections`


```python
def phase_sections(orchestrator: BuildOrchestrator, cli, incremental: bool, affected_sections: set | None) -> None
```



Phase 6: Section Finalization.

Ensures all sections have index pages and validates section structure.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | Build orchestrator instance |
| `cli` | - | - | CLI output for user messages |
| `incremental` | `bool` | - | Whether this is an incremental build |
| `affected_sections` | `set \| None` | - | Set of section paths affected by changes (or None for full build) Side effects: - May create generated index pages for sections without them - Invalidates regular_pages cache |







**Returns**


`None`




### `phase_taxonomies`


```python
def phase_taxonomies(orchestrator: BuildOrchestrator, cache, incremental: bool, parallel: bool, pages_to_build: list) -> set
```



Phase 7: Taxonomies & Dynamic Pages.

Collects taxonomy terms (tags, categories) and generates taxonomy pages.
Optimized for incremental builds - only processes changed pages.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | Build orchestrator instance |
| `cache` | - | - | Build cache |
| `incremental` | `bool` | - | Whether this is an incremental build |
| `parallel` | `bool` | - | Whether to use parallel processing |
| `pages_to_build` | `list` | - | List of pages being built (for incremental) |







**Returns**


`set` - Set of affected tag slugs

Side effects:
    - Populates orchestrator.site.taxonomies
    - Creates taxonomy pages in orchestrator.site.pages
    - Invalidates regular_pages cache
    - Updates orchestrator.stats.taxonomy_time_ms




### `phase_taxonomy_index`


```python
def phase_taxonomy_index(orchestrator: BuildOrchestrator) -> None
```



Phase 8: Save Taxonomy Index.

Persists tag-to-pages mapping for incremental builds.

Side effects:
    - Writes taxonomy index to .bengal/taxonomy_index.json


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | *No description provided.* |







**Returns**


`None`




### `phase_menus`


```python
def phase_menus(orchestrator: BuildOrchestrator, incremental: bool, changed_page_paths: set) -> None
```



Phase 9: Menu Building.

Builds navigation menus. Optimized for incremental builds.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | Build orchestrator instance |
| `incremental` | `bool` | - | Whether this is an incremental build |
| `changed_page_paths` | `set` | - | Set of paths for pages that changed Side effects: - Populates orchestrator.site.menu - Updates orchestrator.stats.menu_time_ms |







**Returns**


`None`




### `phase_related_posts`


```python
def phase_related_posts(orchestrator: BuildOrchestrator, incremental: bool, parallel: bool, pages_to_build: list) -> None
```



Phase 10: Related Posts Index.

Pre-computes related posts for O(1) template access.
Skipped for large sites (>5K pages) or sites without tags.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | Build orchestrator instance |
| `incremental` | `bool` | - | Whether this is an incremental build |
| `parallel` | `bool` | - | Whether to use parallel processing |
| `pages_to_build` | `list` | - | List of pages being built (for incremental optimization) Side effects: - Populates page.related_posts for each page - Updates orchestrator.stats.related_posts_time_ms |







**Returns**


`None`




### `phase_query_indexes`


```python
def phase_query_indexes(orchestrator: BuildOrchestrator, cache, incremental: bool, pages_to_build: list) -> None
```



Phase 11: Query Indexes.

Builds pre-computed indexes for O(1) template lookups.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | Build orchestrator instance |
| `cache` | - | - | Build cache |
| `incremental` | `bool` | - | Whether this is an incremental build |
| `pages_to_build` | `list` | - | List of pages being built (for incremental) Side effects: - Builds/updates site.indexes |







**Returns**


`None`




### `phase_update_pages_list`


```python
def phase_update_pages_list(orchestrator: BuildOrchestrator, incremental: bool, pages_to_build: list, affected_tags: set) -> list
```



Phase 12: Update Pages List.

Updates the pages_to_build list to include newly generated taxonomy pages.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `orchestrator` | `BuildOrchestrator` | - | Build orchestrator instance |
| `incremental` | `bool` | - | Whether this is an incremental build |
| `pages_to_build` | `list` | - | Current list of pages to build |
| `affected_tags` | `set` | - | Set of affected tag slugs |







**Returns**


`list` - Updated pages_to_build list including generated taxonomy pages

Side effects:
    - Invalidates page caches



---
*Generated by Bengal autodoc from `bengal/orchestration/build/content.py`*
