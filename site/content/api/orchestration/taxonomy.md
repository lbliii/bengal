
---
title: "orchestration.taxonomy"
type: python-module
source_file: "bengal/orchestration/taxonomy.py"
css_class: api-content
description: "Taxonomy orchestration for Bengal SSG.  Handles taxonomy collection (tags, categories) and dynamic page generation (tag pages, archive pages, etc.)."
---

# orchestration.taxonomy

Taxonomy orchestration for Bengal SSG.

Handles taxonomy collection (tags, categories) and dynamic page generation
(tag pages, archive pages, etc.).

---

## Classes

### `TaxonomyOrchestrator`


Handles taxonomies and dynamic page generation.

Responsibilities:
    - Collect tags, categories, and other taxonomies
    - Generate tag index pages
    - Generate individual tag pages (with pagination)

Note: Section archive pages are now handled by SectionOrchestrator




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site', threshold: int = 20, parallel: bool = True)
```

Initialize taxonomy orchestrator.



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
* - `site`
  - `'Site'`
  - -
  - Site instance containing pages and sections
* - `threshold`
  - `int`
  - `20`
  - -
* - `parallel`
  - `bool`
  - `True`
  - -
:::

::::




---
#### `collect_and_generate`
```python
def collect_and_generate(self, parallel: bool = True) -> None
```

Collect taxonomies and generate dynamic pages.
Main entry point called during build.



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
* - `parallel`
  - `bool`
  - `True`
  - Whether to use parallel processing for tag page generation
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `collect_and_generate_incremental`
```python
def collect_and_generate_incremental(self, changed_pages: list['Page'], cache: 'BuildCache') -> set[str]
```

Incrementally update taxonomies for changed pages only.

Architecture:
1. Only rebuild site.taxonomies from current Page objects when tags actually changed
2. Use cache to determine which tag PAGES need regeneration (fast)
3. Never reuse taxonomy structure with object references (prevents bugs)

Performance:
- Change detection: O(changed pages)
- Taxonomy reconstruction: O(all tags * pages_per_tag) ≈ O(all pages) but ONLY when tags changed
- Tag page generation: O(affected tags)



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
* - `changed_pages`
  - `list['Page']`
  - -
  - List of pages that changed (NOT generated pages)
* - `cache`
  - `'BuildCache'`
  - -
  - Build cache with tag index
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`set[str]` - Set of affected tag slugs (for regenerating tag pages)




---
#### `collect_taxonomies`
```python
def collect_taxonomies(self) -> None
```

Collect taxonomies (tags, categories, etc.) from all pages.
Organizes pages by their taxonomic terms.



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
#### `generate_dynamic_pages_for_tags`
```python
def generate_dynamic_pages_for_tags(self, affected_tags: set) -> None
```

Generate dynamic pages only for specific affected tags (incremental optimization).

This method supports i18n - it generates per-locale tag pages when i18n is enabled.



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
* - `affected_tags`
  - `set`
  - -
  - Set of tag slugs that need page regeneration
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `generate_dynamic_pages_for_tags_with_cache`
```python
def generate_dynamic_pages_for_tags_with_cache(self, affected_tags: set, taxonomy_index: 'TaxonomyIndex' = None) -> None
```

Generate dynamic pages only for specific affected tags with TaxonomyIndex optimization (Phase 2c.2).

This enhanced version uses TaxonomyIndex to skip regenerating tags whose page membership
hasn't changed, providing ~160ms savings per incremental build for typical sites.



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
* - `affected_tags`
  - `set`
  - -
  - Set of tag slugs that need page regeneration
* - `taxonomy_index`
  - `'TaxonomyIndex'`
  - `None`
  - Optional TaxonomyIndex for skipping unchanged tags
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `generate_dynamic_pages`
```python
def generate_dynamic_pages(self, parallel: bool = True) -> None
```

Generate dynamic taxonomy pages (tag pages, etc.) that don't have source files.

Note: Section archive pages are now generated by SectionOrchestrator



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
* - `parallel`
  - `bool`
  - `True`
  - Whether to use parallel processing for tag pages (default: True)
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `generate_tag_pages`
```python
def generate_tag_pages(self, tags: list, selective: bool = False, context: 'BuildContext' = None)
```

*No description provided.*



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
* - `tags`
  - `list`
  - -
  - -
* - `selective`
  - `bool`
  - `False`
  - -
* - `context`
  - `'BuildContext'`
  - `None`
  - -
:::

::::




---
