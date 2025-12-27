"""Tests for {% match %} pattern matching (Kida-native feature)."""

import pytest


class TestMatchStatement:
    """Tests for {% match %} pattern matching."""

    def test_simple_match_string(self, env):
        """Match with string literals."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}A
            {% case "b" %}B
            {% case _ %}default
        {% end %}
        """)
        assert "A" in template.render(x="a")
        assert "B" in template.render(x="b")
        assert "default" in template.render(x="z")

    def test_match_integer(self, env):
        """Match with integer values."""
        template = env.from_string("""
        {% match status %}
            {% case 200 %}OK
            {% case 404 %}Not Found
            {% case 500 %}Error
            {% case _ %}Unknown
        {% end %}
        """)
        assert "OK" in template.render(status=200)
        assert "Not Found" in template.render(status=404)
        assert "Unknown" in template.render(status=999)

    def test_match_without_default(self, env):
        """Match without wildcard produces no output for unmatched values."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}A
            {% case "b" %}B
        {% end %}
        """)
        assert "A" in template.render(x="a")
        assert template.render(x="z").strip() == ""

    def test_match_with_expression(self, env):
        """Match subject can be any expression."""
        template = env.from_string("""
        {% match page.type %}
            {% case "post" %}Post
            {% case "gallery" %}Gallery
            {% case _ %}Page
        {% end %}
        """)
        assert "Post" in template.render(page={"type": "post"})
        assert "Page" in template.render(page={"type": "other"})

    def test_match_case_with_expression(self, env):
        """Case patterns can be expressions."""
        template = env.from_string("""
        {% match value %}
            {% case expected %}Matched expected
            {% case _ %}No match
        {% end %}
        """)
        assert "Matched expected" in template.render(value=42, expected=42)
        assert "No match" in template.render(value=42, expected=99)

    def test_match_nested_content(self, env):
        """Match cases can contain complex nested content."""
        template = env.from_string("""
        {% match item.type %}
            {% case "user" %}
                <div class="user">
                    {{ item.name }}
                </div>
            {% case "group" %}
                <div class="group">
                    {% for member in item.members %}
                        <span>{{ member }}</span>
                    {% end %}
                </div>
        {% end %}
        """)
        result = template.render(item={"type": "user", "name": "Alice"})
        assert "Alice" in result
        assert "user" in result

    def test_match_with_endmatch(self, env):
        """Both {% end %} and {% endmatch %} work."""
        template1 = env.from_string("""
        {% match x %}{% case "a" %}A{% end %}
        """)
        template2 = env.from_string("""
        {% match x %}{% case "a" %}A{% endmatch %}
        """)
        assert template1.render(x="a").strip() == template2.render(x="a").strip()

    def test_match_error_no_cases(self, env):
        """Match must have at least one case."""
        # Note: ParseError is raised, not TemplateSyntaxError
        from bengal.rendering.kida.parser.errors import ParseError

        with pytest.raises(ParseError, match="at least one"):
            env.from_string("{% match x %}{% end %}")

    def test_match_error_invalid_block_inside(self, env):
        """Invalid keywords inside match block raise errors."""
        from bengal.rendering.kida.parser.errors import ParseError

        with pytest.raises(ParseError, match="Expected 'case' or 'end'"):
            env.from_string("{% match x %}{% for i in items %}{% end %}{% end %}")


class TestMatchEdgeCases:
    """Edge cases for match statement."""

    def test_nested_match(self, env):
        """Match blocks can be nested."""
        template = env.from_string("""
        {% match outer %}
            {% case "a" %}
                {% match inner %}
                    {% case 1 %}A1
                    {% case 2 %}A2
                {% end %}
            {% case "b" %}B
        {% end %}
        """)
        assert "A1" in template.render(outer="a", inner=1)
        assert "A2" in template.render(outer="a", inner=2)
        assert "B" in template.render(outer="b", inner=999)

    def test_match_with_filters(self, env):
        """Match subject can include filters."""
        template = env.from_string("""
        {% match name | lower %}
            {% case "alice" %}Found Alice
            {% case _ %}Unknown
        {% end %}
        """)
        assert "Found Alice" in template.render(name="ALICE")
        assert "Found Alice" in template.render(name="Alice")

    def test_match_boolean(self, env):
        """Match works with boolean values."""
        template = env.from_string("""
        {% match flag %}
            {% case true %}Enabled
            {% case false %}Disabled
        {% end %}
        """)
        assert "Enabled" in template.render(flag=True)
        assert "Disabled" in template.render(flag=False)

    def test_match_none(self, env):
        """Match works with None value."""
        template = env.from_string("""
        {% match value %}
            {% case none %}No value
            {% case _ %}Has value: {{ value }}
        {% end %}
        """)
        assert "No value" in template.render(value=None)
        assert "Has value: 42" in template.render(value=42)

    def test_first_match_wins(self, env):
        """First matching case is used (no fall-through)."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}First
            {% case "a" %}Second
        {% end %}
        """)
        result = template.render(x="a")
        assert "First" in result
        assert "Second" not in result

    def test_match_in_loop(self, env):
        """Match works inside a for loop."""
        template = env.from_string("""
        {% for item in items %}
            {% match item.type %}
                {% case "a" %}[A]
                {% case "b" %}[B]
                {% case _ %}[?]
            {% end %}
        {% end %}
        """)
        items = [{"type": "a"}, {"type": "b"}, {"type": "c"}]
        result = template.render(items=items)
        assert "[A]" in result
        assert "[B]" in result
        assert "[?]" in result

    def test_match_with_complex_expression(self, env):
        """Match with complex expressions."""
        template = env.from_string("""
        {% match x + y %}
            {% case 10 %}Ten
            {% case 20 %}Twenty
            {% case _ %}Other
        {% end %}
        """)
        assert "Ten" in template.render(x=3, y=7)
        assert "Twenty" in template.render(x=15, y=5)
        assert "Other" in template.render(x=1, y=1)

    def test_match_empty_cases(self, env):
        """Match with empty case bodies."""
        template = env.from_string("""
        {% match x %}
            {% case "a" %}
            {% case "b" %}B
        {% end %}
        """)
        # Case "a" has empty body - should produce no output
        assert template.render(x="a").strip() == ""
        assert "B" in template.render(x="b")

    def test_match_with_output_in_case(self, env):
        """Match case with variable output."""
        template = env.from_string("""
        {% match status %}
            {% case "active" %}Status: {{ status | upper }}
            {% case _ %}Unknown status
        {% end %}
        """)
        assert "Status: ACTIVE" in template.render(status="active")

    def test_wildcard_only_match(self, env):
        """Match with only wildcard case."""
        template = env.from_string("""
        {% match x %}
            {% case _ %}Always matches
        {% end %}
        """)
        assert "Always matches" in template.render(x="anything")
        assert "Always matches" in template.render(x=123)
        assert "Always matches" in template.render(x=None)


class TestMatchWithInheritance:
    """Tests for match in template inheritance context."""

    def test_match_in_block(self, env_with_loader):
        """Match works inside template blocks."""
        env_with_loader.loader._mapping["child_match.html"] = """
        {% extends "base.html" %}
        {% block body %}
            {% match page_type %}
                {% case "home" %}Welcome Home
                {% case "about" %}About Us
                {% case _ %}Generic Page
            {% end %}
        {% endblock %}
        """
        template = env_with_loader.get_template("child_match.html")
        result = template.render(page_type="home")
        assert "Welcome Home" in result


class TestMatchParser:
    """Tests for match parser behavior."""

    def test_match_keyword_recognized(self, env):
        """match keyword is recognized."""
        # Should not raise - match is a valid keyword
        template = env.from_string("{% match x %}{% case 1 %}One{% end %}")
        assert "One" in template.render(x=1)

    def test_case_keyword_recognized(self, env):
        """case keyword is recognized inside match."""
        template = env.from_string("{% match x %}{% case 1 %}One{% end %}")
        assert "One" in template.render(x=1)

    def test_case_outside_match_error(self, env):
        """case keyword outside match raises error."""
        from bengal.rendering.kida.parser.errors import ParseError

        with pytest.raises(ParseError):
            env.from_string("{% case 1 %}One{% end %}")
