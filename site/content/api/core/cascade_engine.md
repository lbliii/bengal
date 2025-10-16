
---
title: "core.cascade_engine"
type: python-module
source_file: "bengal/core/cascade_engine.py"
css_class: api-content
description: "Isolated cascade engine for applying Hugo-style metadata cascades.  This module provides the CascadeEngine class which handles all cascade application logic independently from Site and ContentOrche..."
---

# core.cascade_engine

Isolated cascade engine for applying Hugo-style metadata cascades.

This module provides the CascadeEngine class which handles all cascade
application logic independently from Site and ContentOrchestrator.

The engine pre-computes page-section relationships for O(1) top-level
page detection, improving performance from O(n²) to O(n).

---

## Classes

### `CascadeEngine`


Isolated cascade application logic with pre-computed O(1) lookups.

Handles Hugo-style metadata cascading where section _index.md files
can define cascade metadata that propagates to descendant pages.

Pre-computes page-section relationships to avoid O(n²) lookups
when determining if a page is top-level (not in any section).


:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 3 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `pages`
  - -
  - All pages in the site
* - `sections`
  - -
  - All sections in the site
* - `_pages_in_sections`
  - -
  - Pre-computed set of pages that belong to sections (O(1) lookup)
:::

::::


:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, pages: list[Any], sections: list[Any]) -> None
```

Initialize cascade engine with site pages and sections.



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
* - `pages`
  - `list[Any]`
  - -
  - List of all Page objects in the site
* - `sections`
  - `list[Any]`
  - -
  - List of all Section objects in the site
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `is_top_level_page`
```python
def is_top_level_page(self, page: Any) -> bool
```

Check if a page is top-level (not in any section).

O(1) lookup using pre-computed set.



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
* - `page`
  - `Any`
  - -
  - Page object to check
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`bool` - True if page is not in any section, False otherwise




---
#### `apply`
```python
def apply(self) -> dict[str, int]
```

Apply cascade metadata from sections to pages.

Processes root-level cascades first, then recursively applies
cascades through the section hierarchy. Returns statistics about
what was cascaded.



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

`dict[str, int]` - Dictionary with cascade statistics:
    - pages_processed: Total pages in site
    - pages_with_cascade: Pages that received cascade values
    - root_cascade_pages: Pages affected by root cascade
    - cascade_keys_applied: Count of each cascaded key




---
