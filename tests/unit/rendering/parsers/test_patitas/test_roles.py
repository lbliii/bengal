"""Tests for patitas role system."""

from __future__ import annotations

import pytest
from patitas.nodes import Paragraph, Role, Text

from bengal.parsing.backends.patitas import parse, parse_to_ast
from bengal.parsing.backends.patitas.roles import (
    RoleRegistryBuilder,
    create_default_registry,
)
from bengal.parsing.backends.patitas.roles.builtins import (
    AbbrRole,
    KbdRole,
    MathRole,
    RefRole,
    SubRole,
    SupRole,
)


class TestRoleParsing:
    """Tests for role lexer and parser."""

    def test_simple_role(self) -> None:
        """Parse a simple role."""
        source = "Press {kbd}`Ctrl+C` to copy."
        ast = parse_to_ast(source)

        assert len(ast) == 1
        assert isinstance(ast[0], Paragraph)

        # Find the Role node in children
        roles = [c for c in ast[0].children if isinstance(c, Role)]
        assert len(roles) == 1
        assert roles[0].name == "kbd"
        assert roles[0].content == "Ctrl+C"

    def test_role_in_paragraph(self) -> None:
        """Role is parsed within paragraph text."""
        source = "See {ref}`installation` for setup."
        ast = parse_to_ast(source)

        assert len(ast) == 1
        para = ast[0]
        assert isinstance(para, Paragraph)

        # Should have text, role, text
        children = para.children
        roles = [c for c in children if isinstance(c, Role)]
        texts = [c for c in children if isinstance(c, Text)]

        assert len(roles) == 1
        assert roles[0].name == "ref"
        assert len(texts) >= 2

    def test_multiple_roles(self) -> None:
        """Multiple roles in same paragraph."""
        source = "Press {kbd}`Ctrl+C` or {kbd}`Cmd+C` to copy."
        ast = parse_to_ast(source)

        assert len(ast) == 1
        para = ast[0]
        roles = [c for c in para.children if isinstance(c, Role)]
        assert len(roles) == 2
        assert all(r.name == "kbd" for r in roles)

    def test_role_with_special_content(self) -> None:
        """Roles can contain special characters."""
        source = "Equation: {math}`E = mc^2`"
        ast = parse_to_ast(source)

        roles = [c for c in ast[0].children if isinstance(c, Role)]
        assert len(roles) == 1
        assert roles[0].content == "E = mc^2"

    def test_invalid_role_syntax(self) -> None:
        """Invalid role syntax is treated as literal text."""
        # Missing backtick
        source = "This {notarole} is plain text."
        ast = parse_to_ast(source)

        para = ast[0]
        roles = [c for c in para.children if isinstance(c, Role)]
        assert len(roles) == 0  # No roles parsed

    def test_role_with_hyphen_name(self) -> None:
        """Role names can contain hyphens."""
        source = "{my-role}`content`"
        ast = parse_to_ast(source)

        roles = [c for c in ast[0].children if isinstance(c, Role)]
        assert len(roles) == 1
        assert roles[0].name == "my-role"


class TestRoleHandlers:
    """Tests for built-in role handlers."""

    def test_ref_role_simple(self) -> None:
        """Ref role with simple target."""
        handler = RefRole()
        from patitas.location import SourceLocation

        loc = SourceLocation(1, 1)
        role = handler.parse("ref", "target-id", loc)

        assert role.name == "ref"
        assert role.content == "target-id"
        assert role.target == "target-id"

    def test_ref_role_with_text(self) -> None:
        """Ref role with explicit display text."""
        handler = RefRole()
        from patitas.location import SourceLocation

        loc = SourceLocation(1, 1)
        role = handler.parse("ref", "Display Text <target-id>", loc)

        assert role.content == "Display Text"
        assert role.target == "target-id"

    def test_kbd_role(self) -> None:
        """Kbd role renders key shortcuts."""
        handler = KbdRole()
        from patitas.location import SourceLocation
        from patitas.stringbuilder import StringBuilder

        loc = SourceLocation(1, 1)
        role = handler.parse("kbd", "Ctrl+C", loc)

        sb = StringBuilder()
        handler.render(role, sb)
        html = sb.build()

        assert "<kbd>" in html
        assert "Ctrl" in html
        assert "C" in html

    def test_abbr_role(self) -> None:
        """Abbr role parses abbreviation and expansion."""
        handler = AbbrRole()
        from patitas.location import SourceLocation

        loc = SourceLocation(1, 1)
        role = handler.parse("abbr", "HTML (HyperText Markup Language)", loc)

        assert role.content == "HTML"
        assert role.target == "HyperText Markup Language"

    def test_math_role(self) -> None:
        """Math role preserves content."""
        handler = MathRole()
        from patitas.location import SourceLocation
        from patitas.stringbuilder import StringBuilder

        loc = SourceLocation(1, 1)
        role = handler.parse("math", "E = mc^2", loc)

        sb = StringBuilder()
        handler.render(role, sb)
        html = sb.build()

        assert "math" in html
        assert "E = mc^2" in html

    def test_sub_role(self) -> None:
        """Sub role renders subscript."""
        handler = SubRole()
        from patitas.location import SourceLocation
        from patitas.stringbuilder import StringBuilder

        loc = SourceLocation(1, 1)
        role = handler.parse("sub", "2", loc)

        sb = StringBuilder()
        handler.render(role, sb)
        html = sb.build()

        assert "<sub>" in html
        assert "2" in html

    def test_sup_role(self) -> None:
        """Sup role renders superscript."""
        handler = SupRole()
        from patitas.location import SourceLocation
        from patitas.stringbuilder import StringBuilder

        loc = SourceLocation(1, 1)
        role = handler.parse("sup", "2", loc)

        sb = StringBuilder()
        handler.render(role, sb)
        html = sb.build()

        assert "<sup>" in html
        assert "2" in html


class TestRoleRegistry:
    """Tests for RoleRegistry."""

    def test_register_handler(self) -> None:
        """Register and retrieve role handlers."""
        builder = RoleRegistryBuilder()
        builder.register(RefRole())
        registry = builder.build()

        handler = registry.get("ref")
        assert handler is not None
        assert isinstance(handler, RefRole)

    def test_default_registry(self) -> None:
        """Default registry has built-in roles."""
        registry = create_default_registry()

        assert registry.has("ref")
        assert registry.has("doc")
        assert registry.has("kbd")
        assert registry.has("abbr")
        assert registry.has("math")
        assert registry.has("sub")
        assert registry.has("sup")

    def test_duplicate_registration_fails(self) -> None:
        """Cannot register same role name twice."""
        builder = RoleRegistryBuilder()
        builder.register(RefRole())

        with pytest.raises(ValueError, match="already registered"):
            builder.register(RefRole())


class TestRoleRendering:
    """Tests for role HTML rendering."""

    def test_render_kbd(self) -> None:
        """Render kbd role."""
        source = "Press {kbd}`Ctrl+C` to copy."
        html = parse(source)

        assert "role" in html
        assert "kbd" in html

    def test_render_ref(self) -> None:
        """Render ref role."""
        source = "See {ref}`installation` for setup."
        html = parse(source)

        assert "role" in html
        assert "ref" in html

    def test_render_multiple_roles(self) -> None:
        """Render multiple roles in one paragraph."""
        source = "Use {kbd}`Ctrl+C` and {kbd}`Ctrl+V`."
        html = parse(source)

        # Should have two kbd references
        assert html.count("role") >= 2
