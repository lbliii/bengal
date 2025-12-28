"""Tests for patitas directive system."""

from __future__ import annotations

import pytest

from bengal.rendering.parsers.patitas import parse, parse_to_ast
from bengal.rendering.parsers.patitas.directives import (
    AdmonitionOptions,
    DirectiveOptions,
    DirectiveRegistryBuilder,
    create_default_registry,
)
from bengal.rendering.parsers.patitas.directives.builtins import (
    AdmonitionDirective,
)
from bengal.rendering.parsers.patitas.nodes import Directive


class TestDirectiveParsing:
    """Tests for directive lexer and parser."""

    def test_simple_directive(self) -> None:
        """Parse a simple directive."""
        source = """
:::{note}
This is a note.
:::
"""
        ast = parse_to_ast(source.strip())
        assert len(ast) == 1
        assert isinstance(ast[0], Directive)
        assert ast[0].name == "note"
        assert ast[0].title is None

    def test_directive_with_title(self) -> None:
        """Parse directive with title."""
        source = """
:::{warning} Important Warning
This is a warning.
:::
"""
        ast = parse_to_ast(source.strip())
        assert len(ast) == 1
        assert isinstance(ast[0], Directive)
        assert ast[0].name == "warning"
        assert ast[0].title == "Important Warning"

    def test_directive_with_options(self) -> None:
        """Parse directive with options."""
        source = """
:::{note}
:class: custom-class
:name: my-note

Content here.
:::
"""
        ast = parse_to_ast(source.strip())
        assert len(ast) == 1
        assert isinstance(ast[0], Directive)
        assert ast[0].name == "note"

        options = dict(ast[0].options)
        assert options.get("class") == "custom-class"
        assert options.get("name") == "my-note"

    def test_nested_directives(self) -> None:
        """Parse nested directives with different colon counts."""
        source = """
::::{note}
Outer note.

:::{warning}
Inner warning.
:::

::::
"""
        ast = parse_to_ast(source.strip())
        assert len(ast) == 1
        assert isinstance(ast[0], Directive)
        assert ast[0].name == "note"

        # Should have children including inner directive
        children = ast[0].children
        assert any(isinstance(c, Directive) and c.name == "warning" for c in children)

    def test_named_closer(self) -> None:
        """Parse directive with named closer."""
        source = """
:::{note}
Content here.
:::{/note}
"""
        ast = parse_to_ast(source.strip())
        assert len(ast) == 1
        assert isinstance(ast[0], Directive)
        assert ast[0].name == "note"

    def test_directive_with_code_block(self) -> None:
        """Directives containing code blocks work correctly."""
        source = """
:::{note}
Example:

```python
print("hello")
```
:::
"""
        ast = parse_to_ast(source.strip())
        assert len(ast) == 1
        assert isinstance(ast[0], Directive)
        # The code block should be preserved inside

    def test_colon_sequences_in_code_block(self) -> None:
        """Colon sequences inside code blocks are not treated as directives."""
        source = """
```markdown
:::{note}
This is inside a code block.
:::
```
"""
        ast = parse_to_ast(source.strip())
        # Should be a fenced code block, not a directive
        from bengal.rendering.parsers.patitas.nodes import FencedCode

        assert len(ast) == 1
        assert isinstance(ast[0], FencedCode)
        assert ":::{note}" in ast[0].code


class TestDirectiveOptions:
    """Tests for DirectiveOptions typed parsing."""

    def test_basic_option_parsing(self) -> None:
        """Parse basic string options."""
        raw = {"name": "my-note", "class": "custom"}
        # Base class has no fields, so just verify from_raw works without error
        DirectiveOptions.from_raw(raw)

    def test_admonition_options(self) -> None:
        """Parse admonition-specific options."""
        raw = {"collapsible": "true", "open": "false"}
        opts = AdmonitionOptions.from_raw(raw)
        assert opts.collapsible is True
        assert opts.open is False

    def test_bool_coercion(self) -> None:
        """Boolean options are coerced correctly."""
        # True values
        for val in ["true", "yes", "1", ""]:
            raw = {"collapsible": val}
            opts = AdmonitionOptions.from_raw(raw)
            assert opts.collapsible is True

        # False values
        for val in ["false", "no", "0", "anything"]:
            raw = {"collapsible": val}
            opts = AdmonitionOptions.from_raw(raw)
            assert opts.collapsible is False

    def test_class_alias(self) -> None:
        """'class' alias works for 'class_' field."""
        raw = {"class": "my-class"}
        from bengal.rendering.parsers.patitas.directives.options import StyledOptions

        opts = StyledOptions.from_raw(raw)
        assert opts.class_ == "my-class"


class TestDirectiveContracts:
    """Tests for DirectiveContract validation."""

    def test_requires_parent(self) -> None:
        """Contract requires_parent validation."""
        from bengal.rendering.parsers.patitas.directives.contracts import TAB_ITEM_CONTRACT

        # Valid: has required parent
        result = TAB_ITEM_CONTRACT.validate_parent("tab-item", "tab-set")
        assert result is None  # No violation

        # Invalid: wrong parent
        result = TAB_ITEM_CONTRACT.validate_parent("tab-item", "note")
        assert result is not None
        assert result.violation_type == "wrong_parent"

        # Invalid: no parent
        result = TAB_ITEM_CONTRACT.validate_parent("tab-item", None)
        assert result is not None
        assert result.violation_type == "missing_parent"

    def test_requires_children(self) -> None:
        """Contract requires_children validation."""
        from bengal.rendering.parsers.patitas.directives.contracts import TAB_SET_CONTRACT
        from bengal.rendering.parsers.patitas.location import SourceLocation

        loc = SourceLocation(1, 1)

        # Create child directives
        tab_item = Directive(loc, "tab-item", None, frozenset(), ())
        note = Directive(loc, "note", None, frozenset(), ())

        # Valid: has required children
        violations = TAB_SET_CONTRACT.validate_children("tab-set", [tab_item])
        assert len(violations) == 0

        # Invalid: wrong children
        violations = TAB_SET_CONTRACT.validate_children("tab-set", [note])
        assert any(v.violation_type == "forbidden_child" for v in violations)


class TestDirectiveRegistry:
    """Tests for DirectiveRegistry."""

    def test_register_handler(self) -> None:
        """Register and retrieve directive handlers."""
        builder = DirectiveRegistryBuilder()
        builder.register(AdmonitionDirective())
        registry = builder.build()

        # Can retrieve by name
        handler = registry.get("note")
        assert handler is not None
        assert isinstance(handler, AdmonitionDirective)

        # All admonition names work
        assert registry.has("warning")
        assert registry.has("tip")
        assert registry.has("danger")

    def test_default_registry(self) -> None:
        """Default registry has built-in directives."""
        registry = create_default_registry()

        # Admonitions
        assert registry.has("note")
        assert registry.has("warning")

        # Dropdown
        assert registry.has("dropdown")

        # Tabs
        assert registry.has("tab-set")
        assert registry.has("tab-item")

    def test_duplicate_registration_fails(self) -> None:
        """Cannot register same directive name twice."""
        builder = DirectiveRegistryBuilder()
        builder.register(AdmonitionDirective())

        with pytest.raises(ValueError, match="already registered"):
            builder.register(AdmonitionDirective())


class TestDirectiveRendering:
    """Tests for directive HTML rendering."""

    def test_render_note(self) -> None:
        """Render a note directive."""
        source = """
:::{note}
This is a note.
:::
"""
        html = parse(source.strip())
        assert "directive" in html
        assert "note" in html or "admonition" in html

    def test_render_with_title(self) -> None:
        """Render directive with custom title."""
        source = """
:::{note} Custom Title
Content here.
:::
"""
        html = parse(source.strip())
        assert "Custom Title" in html

    def test_render_with_registry(self) -> None:
        """Render using custom directive registry."""
        from bengal.rendering.parsers.patitas.renderers.html import HtmlRenderer

        registry = create_default_registry()
        renderer = HtmlRenderer(directive_registry=registry)

        source = """
:::{note}
This is a note.
:::
"""
        ast = parse_to_ast(source.strip())
        html = renderer.render(ast)

        # Should use AdmonitionDirective's render method
        assert "admonition" in html
        assert "note" in html
