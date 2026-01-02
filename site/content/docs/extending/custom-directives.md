---
title: Custom Directives
description: Create custom MyST directive blocks for specialized content
weight: 40
---

Directives are block-level content elements that extend Markdown with custom rendering. Bengal uses MyST-style syntax (`:::{name}`) and provides a base class for creating your own directives.

## Directive Basics

Directives in Bengal:

- Parse content using the MyST fenced syntax
- Support typed options with automatic coercion
- Can define parent-child nesting relationships
- Register automatically when added to the directive factory

## Creating a Custom Directive

Subclass `BengalDirective` and implement the required methods:

```python
from bengal.directives import BengalDirective, DirectiveToken

class AlertDirective(BengalDirective):
    """Custom alert box directive."""

    # Required: Names that trigger this directive
    NAMES = ["alert", "callout"]

    # Required: Token type for the AST
    TOKEN_TYPE = "alert"

    def parse_directive(self, title, options, content, children, state):
        """Parse the directive into a token."""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "level": title or "info",
                "class": options.get("class", ""),
            },
            children=children,
        )

    def render(self, renderer, text, **attrs):
        """Render the token to HTML."""
        level = attrs.get("level", "info")
        css_class = attrs.get("class", "")
        classes = f"alert alert-{level} {css_class}".strip()
        return f'<div class="{classes}">{text}</div>'
```

Usage in Markdown:

```markdown
:::{alert} warning
:class: my-custom-class

This is a warning message.
:::
```

## Class Attributes

### NAMES (Required)

List of directive names that trigger this directive:

```python
NAMES = ["dropdown", "details", "collapsible"]
```

All names map to the same directive class.

### TOKEN_TYPE (Required)

String identifier for the AST node:

```python
TOKEN_TYPE = "dropdown"
```

Used internally to match parse and render phases.

### OPTIONS_CLASS (Optional)

Typed dataclass for parsing directive options:

```python
from bengal.directives import DirectiveOptions
from dataclasses import dataclass

@dataclass
class DropdownOptions(DirectiveOptions):
    open: bool = False
    icon: str | None = None

class DropdownDirective(BengalDirective):
    NAMES = ["dropdown"]
    TOKEN_TYPE = "dropdown"
    OPTIONS_CLASS = DropdownOptions

    def parse_directive(self, title, options, content, children, state):
        # options is now a DropdownOptions instance
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "Details",
                "open": options.open,  # Typed access
                "icon": options.icon,
            },
            children=children,
        )
```

### CONTRACT (Optional)

Define valid parent-child nesting relationships:

```python
from bengal.directives import DirectiveContract

class StepDirective(BengalDirective):
    NAMES = ["step"]
    TOKEN_TYPE = "step"
    CONTRACT = DirectiveContract(requires_parent=("steps",))
```

This ensures `:::{step}` can only appear inside `:::{steps}`.

## Methods to Implement

### parse_directive

Build the AST token from parsed components:

```python
def parse_directive(
    self,
    title: str,          # Text after directive name
    options: Options,    # Parsed options (or DirectiveOptions instance)
    content: str,        # Raw content inside directive
    children: list,      # Parsed child tokens
    state: Any,          # Parser state (for advanced use)
) -> DirectiveToken:
    return DirectiveToken(
        type=self.TOKEN_TYPE,
        attrs={"title": title},
        children=children,
    )
```

### render

Convert the token to HTML:

```python
def render(
    self,
    renderer: Any,   # Patitas renderer (for rendering children)
    text: str,       # Pre-rendered HTML of children
    **attrs: Any,    # Attributes from parse_directive
) -> str:
    title = attrs.get("title", "")
    return f"<details><summary>{title}</summary>{text}</details>"
```

## Built-in Utilities

The package provides HTML generation helpers:

```python
from bengal.directives import (
    escape_html,        # Escape HTML entities
    build_class_string, # Build CSS class string from list
    class_attr,         # Generate class="..." attribute
    data_attrs,         # Generate data-* attributes
    bool_attr,          # Generate boolean attributes (open, disabled)
)

def render(self, renderer, text, **attrs):
    classes = build_class_string("alert", attrs.get("class", ""))
    data = data_attrs(level=attrs.get("level"))
    return f'<div class="{classes}" {data}>{text}</div>'
```

## Example: Embed Directive

A directive for embedding external content:

```python
from dataclasses import dataclass
from bengal.directives import (
    BengalDirective,
    DirectiveOptions,
    DirectiveToken,
    escape_html,
)

@dataclass
class EmbedOptions(DirectiveOptions):
    width: str = "100%"
    height: str = "400px"
    title: str = ""

class EmbedDirective(BengalDirective):
    """Embed external content via iframe."""

    NAMES = ["embed", "iframe"]
    TOKEN_TYPE = "embed"
    OPTIONS_CLASS = EmbedOptions

    def parse_directive(self, title, options, content, children, state):
        # Title contains the URL
        url = title.strip() if title else ""
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "url": url,
                "width": options.width,
                "height": options.height,
                "title": options.title or "Embedded content",
            },
        )

    def render(self, renderer, text, **attrs):
        url = escape_html(attrs.get("url", ""))
        width = escape_html(attrs.get("width", "100%"))
        height = escape_html(attrs.get("height", "400px"))
        title = escape_html(attrs.get("title", ""))

        return (
            f'<iframe src="{url}" '
            f'width="{width}" height="{height}" '
            f'title="{title}" frameborder="0" '
            f'allowfullscreen loading="lazy"></iframe>'
        )
```

Usage:

```markdown
:::{embed} https://www.youtube.com/embed/dQw4w9WgXcQ
:width: 560px
:height: 315px
:title: Video Tutorial
:::
```

## Registration

Custom directives must be registered with the Patitas parser. The standard approach is to add them to the directive registry in `bengal/directives/registry.py`:

```python
# In bengal/directives/registry.py, add to _DIRECTIVE_MAP:
_DIRECTIVE_MAP: dict[str, str] = {
    # ... existing directives ...
    "alert": "your_module.alert_directive",
    "callout": "your_module.alert_directive",
}
```

:::{note}
Currently, custom directives require modification to the Bengal codebase or a fork. A plugin system for external directive registration is on the roadmap.
:::

## Testing Directives

Test both parse and render phases by instantiating your directive class directly:

```python
import pytest
from your_directives import AlertDirective  # Your custom directive

def test_alert_directive_parse():
    directive = AlertDirective()

    # Test parse_directive
    token = directive.parse_directive(
        title="warning",
        options={},
        content="Test content",
        children=[],
        state=None,
    )

    assert token.attrs["level"] == "warning"

def test_alert_directive_render():
    directive = AlertDirective()

    html = directive.render(
        renderer=None,
        text="<p>Test content</p>",
        level="warning",
    )

    assert 'class="alert alert-warning"' in html
    assert "<p>Test content</p>" in html
```

For built-in directives, use `get_directive()` to retrieve registered classes:

```python
from bengal.directives import get_directive

def test_dropdown_directive():
    DropdownDirective = get_directive("dropdown")
    directive = DropdownDirective()
    # ... test implementation
```

## Related

- [Directives Reference](/docs/reference/directives/) for built-in directives
- [Build Pipeline](/docs/reference/architecture/core/pipeline/) for understanding when directives are processed
