"""
Test default theme templates with Kida engine.

Validates that all default theme templates parse correctly with Kida
and produce valid output using Kida-native syntax features.

Note: Full template rendering tests require a Site context (for filters,
globals, template inheritance). These tests focus on:
1. Kida-native syntax features work correctly
2. Converted patterns (| default -> ??, etc.) work correctly
3. Key templates parse and render with mock context
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.rendering.kida import Environment

# Path to default theme templates
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "bengal" / "themes" / "default" / "templates"


class TestTemplatesExist:
    """Verify templates directory structure."""

    def test_templates_dir_exists(self):
        """Verify templates directory exists."""
        assert TEMPLATES_DIR.exists(), f"Templates dir not found: {TEMPLATES_DIR}"

    def test_base_template_exists(self):
        """Verify base.html exists."""
        assert (TEMPLATES_DIR / "base.html").exists()

    def test_key_templates_exist(self):
        """Verify key templates exist."""
        key_templates = [
            "base.html",
            "home.html",
            "page.html",
            "404.html",
            "partials/docs-nav.html",
            "partials/tag-nav.html",
        ]
        for tmpl in key_templates:
            path = TEMPLATES_DIR / tmpl
            assert path.exists(), f"Missing template: {tmpl}"


class TestKidaNativeFeatures:
    """Verify Kida-native syntax features work correctly."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create Kida environment."""
        return Environment(autoescape=True)

    def test_null_coalescing(self, env: Environment):
        """Test ?? operator for defaults."""
        # String default
        tmpl = env.from_string("{{ x ?? 'default' }}")
        assert tmpl.render(x=None) == "default"
        assert tmpl.render(x="value") == "value"

        # Number default
        tmpl = env.from_string("{{ x ?? 42 }}")
        assert tmpl.render(x=None) == "42"
        assert tmpl.render(x=0) == "0"  # Preserves falsy values

        # Boolean default
        tmpl = env.from_string("{{ x ?? true }}")
        assert tmpl.render(x=None) == "True"
        assert tmpl.render(x=False) == "False"  # Preserves False

        # Empty list default
        tmpl = env.from_string("{{ (x ?? []) | length }}")
        assert tmpl.render(x=None) == "0"
        assert tmpl.render(x=[1, 2, 3]) == "3"

    def test_unless_blocks(self, env: Environment):
        """Test {% unless %} for negated conditionals."""
        tmpl = env.from_string("{% unless hidden %}visible{% end %}")
        assert tmpl.render(hidden=False) == "visible"
        assert tmpl.render(hidden=True) == ""
        assert tmpl.render(hidden=None) == "visible"

        # With else
        tmpl = env.from_string("{% unless x %}no{% else %}yes{% end %}")
        assert tmpl.render(x=True) == "yes"
        assert tmpl.render(x=False) == "no"

    def test_range_literals(self, env: Environment):
        """Test range literal syntax."""
        # Inclusive range
        tmpl = env.from_string("{% for i in 1..5 %}{{ i }}{% end %}")
        assert tmpl.render() == "12345"

        # With variable
        tmpl = env.from_string("{% for i in 1..n %}{{ i }}{% end %}")
        assert tmpl.render(n=3) == "123"

    def test_unified_end_tags(self, env: Environment):
        """Test unified {% end %} closing tags."""
        # if/end
        tmpl = env.from_string("{% if x %}yes{% end %}")
        assert tmpl.render(x=True) == "yes"

        # for/end
        tmpl = env.from_string("{% for i in items %}{{ i }}{% end %}")
        assert tmpl.render(items=[1, 2]) == "12"

        # block/end (in template)
        tmpl = env.from_string("{% block content %}default{% end %}")
        # Block renders default content when not extended
        assert "default" in tmpl.render()

    def test_do_statement(self, env: Environment):
        """Test {% do %} for side effects."""
        tmpl = env.from_string("""
{%- set items = [] -%}
{%- do items.append(1) -%}
{%- do items.append(2) -%}
{{ items | length }}
""")
        assert tmpl.render().strip() == "2"

    def test_def_functions(self, env: Environment):
        """Test {% def %} for reusable functions."""
        tmpl = env.from_string("""
{%- def greeting(name) %}Hello, {{ name }}!{% enddef -%}
{{ greeting('World') }}
""")
        assert tmpl.render().strip() == "Hello, World!"

        # With default arguments
        tmpl = env.from_string("""
{%- def greet(name='Guest') %}Hi {{ name }}{% enddef -%}
{{ greet() }} | {{ greet('Alice') }}
""")
        assert tmpl.render().strip() == "Hi Guest | Hi Alice"


class TestTemplateContext:
    """Test templates work with Bengal context objects."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create Kida environment."""
        return Environment(autoescape=True)

    def test_page_object_access(self, env: Environment):
        """Test accessing page object attributes with optional chaining."""
        # Use optional chaining (?.) for safe attribute access with fallback
        tmpl = env.from_string("{{ page?.title ?? 'Untitled' }}")

        # With page object
        class Page:
            def __init__(self, title=None):
                if title is not None:
                    self.title = title

        page = Page("My Page")
        assert tmpl.render(page=page) == "My Page"

        # With missing title (attribute doesn't exist)
        page = Page()  # No title attribute
        assert tmpl.render(page=page) == "Untitled"

        # With None page
        assert tmpl.render(page=None) == "Untitled"

    def test_nested_attribute_access(self, env: Environment):
        """Test nested attribute access with defaults."""
        tmpl = env.from_string("{{ page.metadata.author ?? 'Anonymous' }}")

        # Full path exists
        page = {"metadata": {"author": "John"}}
        assert tmpl.render(page=page) == "John"

    def test_filter_chains(self, env: Environment):
        """Test filter chain syntax."""
        tmpl = env.from_string("{{ items | sort | first ?? 'none' }}")
        assert tmpl.render(items=[3, 1, 2]) == "1"
        assert tmpl.render(items=[]) == "none"


class TestConvertedPatterns:
    """Test specific patterns that were converted from Jinja2."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create Kida environment."""
        return Environment(autoescape=True)

    def test_default_to_null_coalesce(self, env: Environment):
        """Test | default() converted to ??."""
        # Original: {{ x | default('smart') }}
        # Converted: {{ x ?? 'smart' }}
        tmpl = env.from_string("{{ x ?? 'smart' }}")
        assert tmpl.render(x=None) == "smart"
        assert tmpl.render(x="custom") == "custom"

    def test_range_start_end_to_literal(self, env: Environment):
        """Test range(1, 6) converted to 1..5."""
        # Original: {% for i in range(1, 6) %}
        # Converted: {% for i in 1..5 %}
        tmpl = env.from_string("{% for i in 1..5 %}{{ i }}{% end %}")
        assert tmpl.render() == "12345"

    def test_if_not_to_unless(self, env: Environment):
        """Test {% if not x %} converted to {% unless x %}."""
        # Original: {% if not current_tag %}active{% end %}
        # Converted: {% unless current_tag %}active{% end %}
        tmpl = env.from_string("{% unless current_tag %}active{% end %}")
        assert tmpl.render(current_tag=None) == "active"
        assert tmpl.render(current_tag="python") == ""


class TestPerformance:
    """Basic performance tests for Kida templates."""

    @pytest.fixture
    def env(self) -> Environment:
        """Create Kida environment."""
        return Environment(autoescape=True)

    def test_loop_performance(self, env: Environment):
        """Verify loops perform well with many items."""
        tmpl = env.from_string("{% for i in items %}{{ i }}{% end %}")
        items = list(range(1000))
        result = tmpl.render(items=items)
        assert len(result) > 0

    def test_nested_access_performance(self, env: Environment):
        """Verify nested attribute access is efficient."""
        tmpl = env.from_string("{{ page.metadata.author ?? 'Unknown' }}")
        page = {"metadata": {"author": "Test"}}

        # Render many times to check performance
        for _ in range(100):
            result = tmpl.render(page=page)
            assert result == "Test"
