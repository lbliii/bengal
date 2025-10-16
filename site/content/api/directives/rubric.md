
---
title: "directives.rubric"
type: python-module
source_file: "bengal/rendering/plugins/directives/rubric.py"
css_class: api-content
description: "Rubric directive for Mistune.  Provides styled text that looks like a heading but isn't part of the document hierarchy or table of contents. Perfect for API documentation section labels like "Param..."
---

# directives.rubric

Rubric directive for Mistune.

Provides styled text that looks like a heading but isn't part of the
document hierarchy or table of contents. Perfect for API documentation
section labels like "Parameters:", "Returns:", "Raises:", etc.

---

## Classes

### `RubricDirective`

**Inherits from:** `DirectivePlugin`
Rubric directive for pseudo-headings.

Syntax:
    ```{rubric} Parameters
    :class: rubric-parameters
    ```

Or with content (content is ignored, only title/class are used):
    ```{rubric} Returns
    :class: rubric-returns

    Ignored content
    ```

Creates styled text that looks like a heading but doesn't appear in TOC.
The rubric renders immediately with no content inside - content after
the directive is parsed as separate markdown.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block, m, state)
```

Parse rubric directive.

Rubrics are label-only directives - they ignore any content and
just render the title as a styled heading.



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
* - `block`
  - -
  - -
  - -
* - `m`
  - -
  - -
  - -
* - `state`
  - -
  - -
  - -
:::

::::




---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register the directive and renderer.



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
* - `directive`
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


## Functions

### `render_rubric`
```python
def render_rubric(renderer, text, **attrs) -> str
```

Render rubric to HTML.

Renders as a styled div that looks like a heading but is
semantically different (not part of document outline).



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
* - `renderer`
  - -
  - -
  - Mistune renderer
* - `text`
  - -
  - -
  - Rendered children content (unused for rubrics) **attrs: Directive attributes (title, class, etc.)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
