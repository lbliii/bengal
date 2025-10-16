
---
title: "plugins.cross_references"
type: python-module
source_file: "bengal/rendering/plugins/cross_references.py"
css_class: api-content
description: "Cross-reference plugin for Mistune.  Provides [[link]] syntax for internal page references with O(1) lookup performance using pre-built xref_index."
---

# plugins.cross_references

Cross-reference plugin for Mistune.

Provides [[link]] syntax for internal page references with O(1) lookup
performance using pre-built xref_index.

---

## Classes

### `CrossReferencePlugin`


Mistune plugin for inline cross-references with [[link]] syntax.

Syntax:
    [[docs/installation]]           -> Link with page title
    [[docs/installation|Install]]   -> Link with custom text
    [[#heading-name]]               -> Link to heading anchor
    [[id:my-page]]                  -> Link by custom ID
    [[id:my-page|Custom]]          -> Link by ID with custom text

Performance: O(1) per reference (dictionary lookup from xref_index)
Thread-safe: Read-only access to xref_index built during discovery

Architecture:
- Runs as inline parser (processes text before rendering)
- Uses xref_index for O(1) lookups (no linear search)
- Returns raw HTML that bypasses further processing
- Broken refs get special markup for debugging/health checks

Note: For Mistune v3, this works by post-processing the rendered HTML
to replace [[link]] patterns. This is simpler and more compatible than
trying to hook into the inline parser which has a complex API.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, xref_index: dict[str, Any])
```

Initialize cross-reference plugin.



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
* - `xref_index`
  - `dict[str, Any]`
  - -
  - Pre-built cross-reference index from site discovery
:::

::::




---
#### `__call__`
```python
def __call__(self, md)
```

Register the plugin with Mistune.

For Mistune v3, we post-process the HTML output to replace [[link]] patterns.
This is simpler and more compatible than hooking into the inline parser.



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
* - `md`
  - -
  - -
  - -
:::

::::




---


