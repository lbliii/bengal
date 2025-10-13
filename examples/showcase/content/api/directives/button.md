
---
title: "directives.button"
type: python-module
source_file: "bengal/rendering/plugins/directives/button.py"
css_class: api-content
description: "Button directive for Mistune.  Provides clean button syntax for CTAs and navigation:      :::{button} /get-started/     :color: primary     :style: pill     :size: large      Get Started     :::  R..."
---

# directives.button

Button directive for Mistune.

Provides clean button syntax for CTAs and navigation:

    :::{button} /get-started/
    :color: primary
    :style: pill
    :size: large

    Get Started
    :::

Replaces Sphinx-Design's complex button-ref syntax with a simpler approach.

---

## Classes

### `ButtonDirective`

**Inherits from:** `DirectivePlugin`
Button directive for creating styled link buttons.

Syntax:
    :::{button} /path/to/page/
    :color: primary
    :style: pill
    :size: large
    :icon: rocket
    :target: _blank

    Button Text
    :::

Options:
    color: primary, secondary, success, danger, warning, info, light, dark
    style: default (rounded), pill (fully rounded), outline
    size: small, medium (default), large
    icon: Icon name (same as cards)
    target: _blank for external links (optional)




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, block: Any, m: Match, state: Any) -> dict[str, Any]
```

Parse button directive.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`block`** (`Any`) - Block parser
- **`m`** (`Match`) - Regex match object
- **`state`** (`Any`) - Parser state

:::{rubric} Returns
:class: rubric-returns
:::
`dict[str, Any]` - Token dict with type 'button'




---
#### `__call__`
```python
def __call__(self, directive, md)
```

Register the directive with mistune.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`directive`**
- **`md`**





---


## Functions

### `render_button`
```python
def render_button(renderer, text: str, **attrs) -> str
```

Render button as HTML link.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`renderer`** - Mistune renderer
- **`text`** (`str`) - Button text (content between :::{button} and :::) **attrs: Button attributes (url, color, style, size, icon, target)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML string for button




---
