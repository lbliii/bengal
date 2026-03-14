---
title: Custom Directives
description: Create custom MyST directive blocks for specialized content
weight: 40
---

Directives are block-level content elements that extend Markdown with custom rendering. Bengal uses MyST-style syntax (`:::{name}`) and provides a base class for creating your own directives.

## Shortcodes vs Directives

| Use | Shortcode | Directive |
|-----|-----------|-----------|
| **When** | Simple HTML, no validation | Validation, nesting, complex logic |
| **How** | Template file in `templates/shortcodes/` | Python class |
| **Syntax** | `{{< name args >}}` | `:::{name}` |

Use a **shortcode** when output is simple HTML from args and you want template authors to add or customize without code. Use a **directive** when you need validation (e.g., YouTube 11-char ID), parent-child nesting, or structured errors.

See [Template Shortcodes](/docs/extending/shortcodes/) for the template-only path.

## Directive Basics

Directives in Bengal:

- Parse content using the MyST fenced syntax
- Support typed options with automatic coercion
- Can define parent-child nesting relationships
- Register automatically when added to the directive factory

## Creating a Custom Directive

Implement the `DirectiveHandler` protocol (or use the `BengalDirective` alias). You need `names`, `token_type`, `parse()`, and `render()`:

```python
from collections.abc import Sequence
from html import escape as html_escape

from patitas.nodes import Directive

from bengal.directives import DirectiveHandler  # or BengalDirective

class AlertDirective:
    """Custom alert box directive."""

    names = ("alert", "callout")
    token_type = "alert"

    def parse(self, name, title, options, content, children, location):
        """Build the directive AST node."""
        level = title.strip() if title else "info"
        return Directive(
            location=location,
            name=name,
            title=title,
            options={"level": level, "class": getattr(options, "class_", "") or ""},
            children=children,
        )

    def render(self, node, rendered_children, sb):
        """Append HTML to the StringBuilder."""
        level = node.options.get("level", "info")
        css_class = node.options.get("class", "")
        classes = f"alert alert-{level} {css_class}".strip()
        sb.append(f'<div class="{html_escape(classes)}">{rendered_children}</div>')
```

Usage in Markdown:

```markdown
:::{alert} warning
:class: my-custom-class

This is a warning message.
:::
```

## Class Attributes

### names (Required)

Tuple of directive names that trigger this handler:

```python
names = ("dropdown", "details", "collapsible")
```

All names map to the same directive class.

### token_type (Required)

String identifier for the AST node:

```python
token_type = "dropdown"
```

Used internally to match parse and render phases.

### options_class (Optional)

Typed dataclass for parsing directive options. Use `DirectiveOptions` as base:

```python
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape

from patitas.nodes import Directive

from bengal.directives import DirectiveHandler, DirectiveOptions

@dataclass(frozen=True, slots=True)
class DropdownOptions(DirectiveOptions):
    open: bool = False
    icon: str | None = None

class DropdownDirective:
    """Collapsible dropdown directive."""

    names = ("dropdown", "details")
    token_type = "dropdown"
    options_class = DropdownOptions

    def parse(self, name, title, options, content, children, location):
        effective_title = title or "Details"
        return Directive(
            location=location,
            name=name,
            title=effective_title,
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        title = node.title or "Details"
        opts = node.options
        is_open = opts.open
        open_attr = " open" if is_open else ""
        sb.append(f'<details class="dropdown"{open_attr}>\n')
        sb.append(f"  <summary>{html_escape(title)}</summary>\n")
        sb.append('  <div class="dropdown-content">\n')
        sb.append(rendered_children)
        sb.append("  </div>\n")
        sb.append("</details>\n")
```

### contract (Optional)

Define valid parent-child nesting relationships:

```python
from bengal.directives import DirectiveContract

class StepDirective:
    names = ("step",)
    token_type = "step"
    contract = DirectiveContract(requires_parent=("steps",))

    def parse(self, name, title, options, content, children, location):
        # ...
    def render(self, node, rendered_children, sb):
        # ...
```

This ensures `:::{step}` can only appear inside `:::{steps}`.

## Methods to Implement

### parse

Build the `Directive` AST node from parsed components:

```python
def parse(
    self,
    name: str,           # Directive name used (e.g. "alert")
    title: str | None,  # Text after directive name
    options: object,    # Parsed options (DirectiveOptions or dict-like)
    content: str,       # Raw content inside directive
    children: Sequence[Block],  # Parsed child blocks
    location: SourceLocation,    # Source location for errors
) -> Directive:
    return Directive(
        location=location,
        name=name,
        title=title or "Default",
        options={"level": "info"},  # dict or typed options instance
        children=tuple(children),
    )
```

### render

Append HTML to the `StringBuilder`. Do not return a value:

```python
def render(
    self,
    node: Directive,        # The directive AST node from parse()
    rendered_children: str,  # Pre-rendered HTML of children
    sb: StringBuilder,     # Append output here
) -> None:
    title = node.title or "Details"
    sb.append(f"<details><summary>{html_escape(title)}</summary>")
    sb.append(rendered_children)
    sb.append("</details>")
```

## HTML Escaping

Always escape user content to prevent XSS. Use `html.escape`:

```python
from html import escape as html_escape

def render(self, node, rendered_children, sb):
    title = html_escape(node.title or "")
    sb.append(f'<div class="alert">{title}</div>')
```

For attribute values, use `quote=True`:

```python
from html import escape as html_escape
url = html_escape(node.options.get("url", ""), quote=True)
sb.append(f'<a href="{url}">...</a>')
```

## Example: Embed Directive

A directive for embedding external content via iframe:

```python
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape

from patitas.nodes import Directive

from bengal.directives import DirectiveOptions

@dataclass(frozen=True, slots=True)
class EmbedOptions(DirectiveOptions):
    width: str = "100%"
    height: str = "400px"
    title: str = ""

class EmbedDirective:
    """Embed external content via iframe."""

    names = ("embed", "iframe")
    token_type = "embed"
    options_class = EmbedOptions

    def parse(self, name, title, options, content, children, location):
        url = title.strip() if title else ""
        return Directive(
            location=location,
            name=name,
            title=url,  # URL stored in title
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        opts = node.options
        url = html_escape(node.title or "", quote=True)
        width = html_escape(opts.width or "100%", quote=True)
        height = html_escape(opts.height or "400px", quote=True)
        title = html_escape(opts.title or "Embedded content", quote=True)
        sb.append(
            f'<iframe src="{url}" width="{width}" height="{height}" '
            f'title="{title}" frameborder="0" allowfullscreen loading="lazy"></iframe>'
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

Note: The URL goes in the title position (text after the directive name). Options use `:key: value` syntax.

## Registration

Custom directives must be registered with the Patitas parser. Add them to the directive registry builder in `bengal/parsing/backends/patitas/directives/registry.py`:

```python
# In create_default_registry(), add your handler:
from your_module import AlertDirective

builder = DirectiveRegistryBuilder()
# ... existing directives ...
builder.register(AlertDirective())
# ...
return builder.build()
```

:::{note}
Currently, custom directives require modification to the Bengal codebase or a fork. A plugin system for external directive registration is on the roadmap.
:::

## Testing Directives

Test both parse and render phases by instantiating your directive class:

```python
import pytest
from html import escape as html_escape

from patitas.location import SourceLocation
from patitas.stringbuilder import StringBuilder

from your_directives import AlertDirective

def test_alert_directive_parse():
    directive = AlertDirective()
    loc = SourceLocation(path="test.md", line=1, column=1, offset=0)

    node = directive.parse(
        name="alert",
        title="warning",
        options=object(),  # or a real options instance
        content="",
        children=(),
        location=loc,
    )

    assert node.options.get("level", "info") == "warning"

def test_alert_directive_render():
    directive = AlertDirective()
    sb = StringBuilder()
    # Create a minimal Directive node (use your parse() or construct manually)
    from patitas.nodes import Directive
    loc = SourceLocation(path="test.md", line=1, column=1, offset=0)
    node = Directive(
        location=loc,
        name="alert",
        title="warning",
        options={"level": "warning", "class": ""},
        children=(),
    )

    directive.render(node, "<p>Test content</p>", sb)
    html = str(sb)

    assert 'class="alert alert-warning"' in html
    assert "<p>Test content</p>" in html
```

**Testing with Parser Integration**:

```python
from bengal.parsing.backends.patitas import (
    ParseConfig,
    RenderConfig,
    parse_config_context,
    render_config_context,
)
from bengal.parsing.backends.patitas.renderers.html import HtmlRenderer
from bengal.directives import create_default_registry
from patitas.parser import Parser

def test_directive_full_integration():
    registry = create_default_registry()
    source = """
:::{note}
This is a note.
:::
"""
    with parse_config_context(ParseConfig(directive_registry=registry)):
        parser = Parser(source.strip())
        ast = parser.parse()

    with render_config_context(RenderConfig(directive_registry=registry)):
        renderer = HtmlRenderer()
        html = renderer.render(ast)

    assert "admonition" in html
    assert "note" in html
```

For built-in directives, use `get_directive()` to retrieve the handler class:

```python
from bengal.directives import get_directive

def test_dropdown_directive():
    handler_cls = get_directive("dropdown")
    assert handler_cls is not None
    directive = handler_cls()
    # ... test parse/render
```

## Related

- [Directives Reference](/docs/reference/directives/) for built-in directives
- [Build Pipeline](/docs/reference/architecture/core/pipeline/) for understanding when directives are processed
