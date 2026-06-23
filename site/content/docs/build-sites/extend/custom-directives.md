---


title: Custom Directives
description: Create custom MyST directive blocks for specialized content
weight: 40
aliases:
  - /docs/extending/custom-directives/
aliases:
  - /docs/build-sites/extend/custom-directives/
  - /docs/extending/custom-directives/
---

Directives are block-level content elements that extend Markdown with custom rendering. Bengal uses MyST-style syntax (`:::{name}`) and provides a structural `DirectiveHandler` protocol for creating your own directives.

The public API lives in `bengal.parsing.backends.patitas.directives`. There is no `bengal.directives` package — import from the path shown in every example below.

## Shortcodes vs Directives

| Use | Shortcode | Directive |
|-----|-----------|-----------|
| **When** | Simple HTML, no validation | Validation, nesting, complex logic |
| **How** | Template file in `templates/shortcodes/` | Python class |
| **Syntax** | `{{< name args >}}` | `:::{name}` |

Use a **shortcode** when output is simple HTML from args and you want template authors to add or customize without code. Use a **directive** when you need validation (e.g., YouTube 11-char ID), parent-child nesting, or structured errors.

See [Template Shortcodes](../shortcodes/) for the template-only path.

## Directive Basics

Directives in Bengal:

- Parse content using the MyST fenced syntax
- Support typed options with automatic coercion (frozen dataclasses)
- Can define parent-child nesting relationships via contracts
- Are registered through a `DirectiveRegistryBuilder`

A directive is a **stateless handler** that implements the `DirectiveHandler`
protocol. It is *structural* typing — you do not subclass anything. A handler
declares two class attributes and two methods:

- `names: tuple[str, ...]` — directive names this handler responds to.
- `token_type: str` — token type identifier used for AST dispatch.
- `parse(self, name, title, options, content, children, location)` — builds a
  `Directive` AST node.
- `render(self, node, rendered_children, sb)` — **appends** HTML to a
  `StringBuilder`. It returns `None`; it does not return a string.

:::{warning} Handlers must be stateless
Multiple threads may call the same handler instance concurrently. Keep all
state in the (immutable) AST node or in the method arguments. Options are
**frozen dataclasses**, so read them with attribute access (`options.width`),
never mutate them.
:::

## Creating a Custom Directive

Implement the `DirectiveHandler` protocol:

```python
from typing import ClassVar

from patitas.nodes import Directive

class AlertDirective:
    """Custom alert box directive."""

    # Required: names that trigger this directive
    names: ClassVar[tuple[str, ...]] = ("alert", "callout")

    # Required: token type for the AST
    token_type: ClassVar[str] = "alert"

    def parse(self, name, title, options, content, children, location):
        """Build the directive AST node."""
        return Directive(
            location=location,
            name=name,
            title=title or "info",
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        """Append HTML to the StringBuilder (returns None)."""
        level = node.title or "info"
        sb.append(f'<div class="alert alert-{level}">')
        sb.append(rendered_children)
        sb.append("</div>")
```

Usage in Markdown:

```markdown
:::{alert} warning
:class: my-custom-class

This is a warning message.
:::
```

## Handler Attributes

### names (Required)

A tuple of directive names that trigger this handler:

```python
from typing import ClassVar

class DropdownHandler:
    names: ClassVar[tuple[str, ...]] = ("dropdown", "details", "collapsible")
```

All names map to the same handler instance.

### token_type (Required)

String identifier for the AST node, used to match the parse and render phases:

```python
from typing import ClassVar

class DropdownHandler:
    names: ClassVar[tuple[str, ...]] = ("dropdown",)
    token_type: ClassVar[str] = "dropdown"
```

### options_class (Optional)

A frozen-dataclass subclass of `DirectiveOptions` for typed option parsing.
Options are parsed from `:key: value` lines and coerced to the field's type
automatically:

```python
from dataclasses import dataclass
from typing import ClassVar

from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives import DirectiveOptions

@dataclass(frozen=True, slots=True)
class DropdownOptions(DirectiveOptions):
    open: bool = False
    icon: str | None = None

class DropdownHandler:
    names: ClassVar[tuple[str, ...]] = ("dropdown",)
    token_type: ClassVar[str] = "dropdown"
    options_class: ClassVar[type[DropdownOptions]] = DropdownOptions

    def parse(self, name, title, options, content, children, location):
        # options is a DropdownOptions instance (frozen — read, don't mutate)
        return Directive(
            location=location,
            name=name,
            title=title or "Details",
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        is_open = " open" if node.options.open else ""
        sb.append(f"<details{is_open}>")
        sb.append(f"<summary>{node.title}</summary>")
        sb.append(rendered_children)
        sb.append("</details>")
```

`DirectiveOptions` also ships with reusable bases such as `StyledOptions`
(adds `class_` and `name`) and typed option classes for the built-ins
(`AdmonitionOptions`, `FigureOptions`, `TabSetOptions`, and more).

### contract (Optional)

Define valid parent-child nesting relationships with `DirectiveContract`:

```python
from typing import ClassVar

from bengal.parsing.backends.patitas.directives import DirectiveContract

class StepHandler:
    names: ClassVar[tuple[str, ...]] = ("step",)
    token_type: ClassVar[str] = "step"
    contract: ClassVar[DirectiveContract] = DirectiveContract(
        allows_parent=("steps",),
    )
```

This ensures `:::{step}` is only valid inside `:::{steps}`. A
`ContractViolation` is raised when nesting rules are broken.

## Methods to Implement

### parse

Build the `Directive` AST node from the parsed components. The node fields are
`location`, `name`, `title`, `options`, `children`, and an optional
`raw_content`:

```python
from patitas.nodes import Directive

def parse(self, name, title, options, content, children, location):
    return Directive(
        location=location,   # SourceLocation for error messages
        name=name,           # The directive name actually used
        title=title,         # Optional text after the directive name
        options=options,     # Typed options (frozen dataclass)
        children=tuple(children),  # Parsed child blocks
    )
```

### render

Append HTML to the `StringBuilder`. `render()` returns `None` — write output
with `sb.append(...)` (or `sb.append_line(...)`), do not build and return a
string:

```python
def render(self, node, rendered_children, sb):
    sb.append(f"<details><summary>{node.title}</summary>")
    sb.append(rendered_children)  # pre-rendered HTML of child blocks
    sb.append("</details>")
```

### Parse-only and render-only handlers

If you only need to customize one phase, the `DirectiveParseOnly` and
`DirectiveRenderOnly` protocols document that intent (they require only the
relevant method plus `names`/`token_type`):

```python
from bengal.parsing.backends.patitas.directives import (
    DirectiveParseOnly,
    DirectiveRenderOnly,
)
```

## Example: Embed Directive

A directive for embedding external content via an iframe. HTML is escaped with
the standard library's `html.escape`:

```python
from dataclasses import dataclass
from html import escape as escape_html
from typing import ClassVar

from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives import DirectiveOptions

@dataclass(frozen=True, slots=True)
class EmbedOptions(DirectiveOptions):
    width: str = "100%"
    height: str = "400px"
    title: str = ""

class EmbedDirective:
    """Embed external content via iframe."""

    names: ClassVar[tuple[str, ...]] = ("embed", "iframe")
    token_type: ClassVar[str] = "embed"
    options_class: ClassVar[type[EmbedOptions]] = EmbedOptions

    def parse(self, name, title, options, content, children, location):
        # Title contains the URL
        return Directive(
            location=location,
            name=name,
            title=(title or "").strip(),
            options=options,
            children=tuple(children),
        )

    def render(self, node, rendered_children, sb):
        opts = node.options
        url = escape_html(node.title or "")
        width = escape_html(opts.width)
        height = escape_html(opts.height)
        title = escape_html(opts.title or "Embedded content")
        sb.append(
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

Directives are registered through a `DirectiveRegistryBuilder`, which produces
an immutable `DirectiveRegistry`. The built-in registry is assembled in
`bengal/parsing/backends/patitas/directives/registry.py` by
`create_default_registry()`; you can build your own registry that includes both
the built-ins and your custom handlers:

```python
from bengal.parsing.backends.patitas.directives import (
    DirectiveRegistryBuilder,
    create_default_registry,
)

# Start from the built-in handlers, then add your own.
base = create_default_registry()
builder = DirectiveRegistryBuilder()
builder.register_all(list(base.handlers))
builder.register(AlertDirective())
registry = builder.build()

assert registry.has("alert")
handler = registry.get("alert")
```

:::{note}
External plugin registration is wired through Bengal's plugin system
(`create_default_registry(plugin_registry=...)` applies plugin-contributed
directives). The custom handlers above also work directly against the
registry builder shown here.
:::

## Testing Directives

Test the two phases by instantiating your handler directly. `parse()` returns a
`Directive` node; `render()` appends to a `StringBuilder`:

```python
from patitas.stringbuilder import StringBuilder
from patitas.location import SourceLocation

from your_directives import AlertDirective  # your custom handler

def test_alert_directive_parse():
    handler = AlertDirective()
    node = handler.parse(
        name="alert",
        title="warning",
        options=None,
        content="Test content",
        children=(),
        location=SourceLocation(lineno=1, col_offset=0),
    )
    assert node.name == "alert"
    assert node.title == "warning"

def test_alert_directive_render():
    handler = AlertDirective()
    node = handler.parse(
        name="alert",
        title="warning",
        options=None,
        content="",
        children=(),
        location=SourceLocation(lineno=1, col_offset=0),
    )
    sb = StringBuilder()
    handler.render(node, "<p>Test content</p>", sb)
    html = sb.build()
    assert 'class="alert alert-warning"' in html
    assert "<p>Test content</p>" in html
```

For full parse-and-render integration, use the public `PatitasParser`. It wires
up the directive registry (including typed option parsing) the same way a real
build does:

```python
from bengal.parsing.backends.patitas import PatitasParser

def test_directive_full_integration():
    parser = PatitasParser()
    source = """:::{note}
This is a note.
:::"""
    html = parser.parse(source, metadata={})
    assert "admonition" in html
    assert "note" in html
```

To register your own handlers for the parse, build a registry and drive the
lower-level parse/render contexts directly:

```python
from bengal.parsing.backends.patitas import (
    ParseConfig,
    RenderConfig,
    parse_config_context,
    render_config_context,
)
from bengal.parsing.backends.patitas.directives import create_default_registry
```

To look up a built-in handler, query the registry rather than a global getter:

```python
from bengal.parsing.backends.patitas.directives import create_default_registry

def test_dropdown_handler_is_registered():
    registry = create_default_registry()
    handler = registry.get("dropdown")
    assert handler is not None
```

## Related

- [Directives Reference](/docs/reference/directives/) for built-in directives
- [Build Pipeline](https://github.com/lbliii/bengal/tree/main/docs/architecture/core/pipeline/) for understanding when directives are processed
