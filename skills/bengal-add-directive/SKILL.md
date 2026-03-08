---
name: bengal-add-directive
description: Adds a new MyST directive to Bengal. Use when creating custom content blocks (admonitions, cards, tabs), extending the rendering system, or adding a directive.
---

# Bengal Add Directive

Add a new MyST directive to Bengal's rendering system. Bengal uses the DirectiveHandler protocol in `bengal/parsing/backends/patitas/directives/`.

## Overview

1. **DirectiveHandler** — Implement parse() and render() methods
2. **DirectiveOptions** — Frozen dataclass for typed :key: value options
3. **DirectiveContract** — Optional nesting validation
4. **Registration** — Add to create_default_registry() in registry.py

## Procedure

### Step 1: Define Options (if needed)

```python
# bengal/parsing/backends/patitas/directives/options.py (or new file)

from dataclasses import dataclass
from bengal.parsing.backends.patitas.directives.options import DirectiveOptions

@dataclass(frozen=True, slots=True)
class NewDirectiveOptions(DirectiveOptions):
    icon: str | None = None
    class_: str | None = None
```

### Step 2: Create the Handler

```python
# bengal/parsing/backends/patitas/directives/builtins/new_directive.py

from __future__ import annotations

from collections.abc import Sequence
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Directive

from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract
from bengal.parsing.backends.patitas.directives.options import NewDirectiveOptions

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder


class NewDirective:
    names: ClassVar[tuple[str, ...]] = ("new-directive",)
    token_type: ClassVar[str] = "new-directive"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[NewDirectiveOptions]] = NewDirectiveOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: NewDirectiveOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        return Directive(
            location=location,
            name=name,
            title=title or "",
            options=options,
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[NewDirectiveOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        opts = node.options
        title = node.title or "Title"
        css_class = opts.class_ or ""
        sb.append(f'<div class="directive-new {html_escape(css_class)}">\n')
        sb.append(f'  <h3>{html_escape(title)}</h3>\n')
        sb.append(rendered_children)
        sb.append("</div>\n")
```

### Step 3: Register the Directive

In `bengal/parsing/backends/patitas/directives/registry.py`:

```python
# Add import
from bengal.parsing.backends.patitas.directives.builtins.new_directive import NewDirective

# In create_default_registry(), add:
builder.register(NewDirective())
```

### Step 4: Add Tests

```python
# tests/unit/parsing/directives/test_new_directive.py

def test_parse_creates_directive():
    handler = NewDirective()
    node = handler.parse(
        name="new-directive",
        title="My Title",
        options=NewDirectiveOptions.from_raw({}),
        content="",
        children=[],
        location=...,
    )
    assert node.title == "My Title"
```

## Directive with Children

Use DirectiveContract for nesting:

```python
from bengal.parsing.backends.patitas.directives.contracts import DirectiveContract

# Parent: requires tab-item children
TAB_SET_CONTRACT = DirectiveContract(
    requires_children=("tab-item",),
    allows_children=("tab-item",),
)

# Child: must be inside tab-set
TAB_ITEM_CONTRACT = DirectiveContract(requires_parent=("tab-set",))
```

## Existing Directives to Reference

| Directive | File | Example Of |
|-----------|------|------------|
| note | builtins/admonition.py | Simple directive with options |
| tab-set, tab-item | builtins/tabs.py | Parent with children |
| card, cards | builtins/cards.py | Grid layout |
| steps, step | builtins/steps.py | Contract-based nesting |

## Checklist

- [ ] Options class (frozen dataclass) if directive has :key: value options
- [ ] Handler with names, token_type, parse(), render()
- [ ] Registered in create_default_registry()
- [ ] Unit tests for parse and render
- [ ] Integration test with content using the directive

## Additional Resources

See [references/add-directive-guide.md](references/add-directive-guide.md) for contract patterns and option type coercion details.
