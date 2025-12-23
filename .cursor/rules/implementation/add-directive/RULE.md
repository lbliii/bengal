---
description: Step-by-step guide for adding new MyST directives to Bengal
alwaysApply: false
globs: ["bengal/directives/**/*.py"]
---

# Add New Directive

Step-by-step guide for adding MyST directives to Bengal's rendering system.

**Shortcut**: `::new-directive`

**Works with**: `modules/types-as-contracts`, `modules/architecture-patterns`

---

## Overview

Bengal directives follow a contract-based pattern:

1. **DirectiveContract** - Frozen dataclass defining allowed children, args
2. **Directive class** - Implementation with `render()` method
3. **Registration** - Register in the directive registry
4. **Theme templates** - HTML templates for rendering

---

## Procedure

### Step 1: Define the Contract (Types First!)

```python
# bengal/directives/contracts.py (or new file)

from dataclasses import dataclass

@dataclass(frozen=True)
class NewDirectiveContract:
    """
    Contract for the ::new-directive.

    Type signature IS the validation spec.

    Example usage:
        :::{new-directive} required_arg
        :optional_arg: value

        Content here
        :::
    """
    # Directive name
    name: str = "new-directive"

    # Required positional arguments
    required_args: tuple[str, ...] = ("title",)

    # Optional keyword arguments with defaults
    optional_args: frozenset[str] = frozenset({"icon", "class"})

    # Allowed child directives (empty = no children)
    allowed_children: frozenset[str] = frozenset()

    # Whether body content is required
    has_body: bool = True
```

### Step 2: Create the Directive Class

```python
# bengal/directives/new_directive.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.directives.base import Directive, DirectiveResult

if TYPE_CHECKING:
    from bengal.rendering.context import RenderContext


@dataclass
class NewDirective(Directive):
    """
    Renders a [description of what it does].

    Syntax:
        :::{new-directive} Title Text
        :icon: star
        :class: highlight

        Body content with **markdown**.
        :::

    Attributes:
        title: The directive title (required)
        icon: Optional icon name
        css_class: Optional CSS class
        body: Markdown body content
    """
    title: str
    icon: str | None = None
    css_class: str | None = None
    body: str = ""
    children: list[Directive] = field(default_factory=list)

    @classmethod
    def from_token(cls, token: dict, context: RenderContext) -> NewDirective:
        """
        Create directive from parsed token.

        Args:
            token: Parsed directive token with attrs and body
            context: Current render context

        Returns:
            NewDirective instance
        """
        attrs = token.get("attrs", {})

        return cls(
            title=token.get("arg", ""),
            icon=attrs.get("icon"),
            css_class=attrs.get("class"),
            body=token.get("body", ""),
        )

    def render(self, context: RenderContext) -> DirectiveResult:
        """
        Render the directive to HTML.

        Args:
            context: Render context with template access

        Returns:
            DirectiveResult with rendered HTML
        """
        # Render body markdown
        rendered_body = context.render_markdown(self.body)

        # Use template
        html = context.render_template(
            "directives/new-directive.html",
            directive=self,
            body=rendered_body,
        )

        return DirectiveResult(html=html)
```

### Step 3: Create the Template

```html
<!-- bengal/themes/default/templates/directives/new-directive.html -->

<div class="directive-new {{ directive.css_class or '' }}">
  <div class="directive-header">
    {% if directive.icon %}
    <span class="icon">{{ icon(directive.icon) }}</span>
    {% endif %}
    <span class="title">{{ directive.title }}</span>
  </div>
  <div class="directive-body">
    {{ body | safe }}
  </div>
</div>
```

### Step 4: Register the Directive

```python
# bengal/directives/__init__.py (or registry.py)

from bengal.directives.new_directive import NewDirective
from bengal.directives.registry import DirectiveRegistry

# Register the directive
DirectiveRegistry.register("new-directive", NewDirective)
```

### Step 5: Add Tests

```python
# tests/unit/directives/test_new_directive.py

import pytest
from bengal.directives.new_directive import NewDirective


class TestNewDirectiveContract:
    """Test the directive contract."""

    def test_contract_is_frozen(self):
        """Contract should be immutable."""
        from bengal.directives.contracts import NewDirectiveContract
        contract = NewDirectiveContract()

        with pytest.raises(AttributeError):
            contract.name = "changed"

    def test_required_args(self):
        """Title should be required."""
        from bengal.directives.contracts import NewDirectiveContract
        contract = NewDirectiveContract()

        assert "title" in contract.required_args


class TestNewDirective:
    """Test directive functionality."""

    def test_from_token(self, render_context):
        """Should create from token."""
        token = {
            "arg": "My Title",
            "attrs": {"icon": "star"},
            "body": "Content here",
        }

        directive = NewDirective.from_token(token, render_context)

        assert directive.title == "My Title"
        assert directive.icon == "star"
        assert directive.body == "Content here"

    def test_render_produces_html(self, render_context):
        """Should render to HTML."""
        directive = NewDirective(title="Test", body="Content")

        result = directive.render(render_context)

        assert "<div class=\"directive-new" in result.html
        assert "Test" in result.html


# tests/integration/directives/test_new_directive_integration.py

def test_directive_renders_in_page(site_with_content):
    """Directive should render when used in content."""
    # Create test page with directive
    page_content = '''
---
title: Test Page
---

# Test

:::{new-directive} Hello World
:icon: star

This is the body content.
:::
'''
    site_with_content.add_page("test.md", page_content)
    site_with_content.build()

    output = site_with_content.read_output("test/index.html")

    assert "directive-new" in output
    assert "Hello World" in output
```

### Step 6: Add CSS (Optional)

```css
/* bengal/themes/default/static/css/directives.css */

.directive-new {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin: 1rem 0;
  padding: 1rem;
}

.directive-new .directive-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.directive-new .directive-body {
  color: var(--color-text-secondary);
}
```

---

## Checklist

- [ ] **Contract defined** as frozen dataclass
- [ ] **Directive class** with `from_token()` and `render()`
- [ ] **Template created** in themes/default/templates/directives/
- [ ] **Registered** in DirectiveRegistry
- [ ] **Unit tests** for contract and directive
- [ ] **Integration test** with actual content
- [ ] **CSS styles** added (if visual directive)
- [ ] **Documentation** added to site/content/docs/

---

## Existing Directives to Reference

| Directive | File | Good Example Of |
|-----------|------|-----------------|
| `note` | `bengal/directives/admonitions.py` | Simple admonition |
| `tabs` | `bengal/directives/tabs.py` | Parent with children |
| `code-block` | `bengal/directives/code.py` | Syntax highlighting |
| `toctree` | `bengal/directives/toctree.py` | Page queries |

---

## Common Patterns

### Directive with Children

```python
@dataclass(frozen=True)
class TabsContract:
    allowed_children: frozenset[str] = frozenset({"tab-item"})

@dataclass
class TabsDirective(Directive):
    children: list[TabItemDirective] = field(default_factory=list)

    def render(self, context: RenderContext) -> DirectiveResult:
        rendered_children = [
            child.render(context) for child in self.children
        ]
        ...
```

### Directive with Validation

```python
def from_token(cls, token: dict, context: RenderContext) -> NewDirective:
    title = token.get("arg", "")

    if not title:
        raise DirectiveError(
            f"new-directive requires a title argument",
            location=token.get("location"),
        )

    return cls(title=title, ...)
```

---

## Related

- `bengal/directives/base.py` - Base directive class
- `bengal/directives/contracts.py` - Contract definitions
- `bengal/directives/registry.py` - Directive registry
- `modules/types-as-contracts` - Type-first philosophy
