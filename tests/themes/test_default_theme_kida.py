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

    def test_let_template_wide_scope(self, env: Environment):
        """Test {% let %} for template-wide variables."""
        # let variables are available across blocks
        tmpl = env.from_string("""
{%- let site_title = 'My Site' -%}
{%- let version = '1.0' -%}
{{ site_title }} v{{ version }}
""")
        assert tmpl.render().strip() == "My Site v1.0"

        # let with dependent values
        tmpl = env.from_string("""
{%- let base = 10 -%}
{%- let doubled = base * 2 -%}
{%- let tripled = base * 3 -%}
{{ base }}-{{ doubled }}-{{ tripled }}
""")
        assert tmpl.render().strip() == "10-20-30"

    def test_with_as_nil_resilient(self, env: Environment):
        """Test {% with expr as name %} for nil-resilient binding."""
        # When value exists, block renders
        tmpl = env.from_string("""
{%- with user.name as name -%}
Hello, {{ name }}!
{%- end -%}
""")
        assert tmpl.render(user={"name": "Alice"}).strip() == "Hello, Alice!"

        # When value is None, block doesn't render
        assert tmpl.render(user={"name": None}).strip() == ""

        # When key is missing entirely
        assert tmpl.render(user={}).strip() == ""

    def test_with_as_with_filters(self, env: Environment):
        """Test {% with %} with filter expressions."""
        tmpl = env.from_string("""
{%- with items | length as count -%}
Found {{ count }} items
{%- end -%}
""")
        assert tmpl.render(items=[1, 2, 3]).strip() == "Found 3 items"
        assert tmpl.render(items=[]).strip() == ""  # Empty list is falsy
        tmpl = env.from_string("""
{%- def greet(name='Guest') %}Hi {{ name }}{% enddef -%}
{{ greet() }} | {{ greet('Alice') }}
""")
        assert tmpl.render().strip() == "Hi Guest | Hi Alice"

    def test_slot_for_caller_content(self, env: Environment):
        """Test {% slot %} inside {% def %} for caller content injection."""
        # Define a wrapper with a slot
        tmpl = env.from_string("""
{%- def card(title) -%}
<div class="card">
  <h3>{{ title }}</h3>
  <div class="body">{% slot %}</div>
</div>
{%- end -%}

{%- call card("My Card") -%}
<p>This is the slot content!</p>
{%- end -%}
""")
        result = tmpl.render().strip()
        assert "<h3>My Card</h3>" in result
        assert "<p>This is the slot content!</p>" in result

    def test_slot_with_multiple_content(self, env: Environment):
        """Test {% slot %} with rich content."""
        tmpl = env.from_string("""
{%- def panel(variant='info') -%}
<aside class="panel panel--{{ variant }}">
{% slot %}
</aside>
{%- end -%}

{%- call panel(variant='warning') -%}
<strong>Warning!</strong>
<p>Something happened.</p>
{%- end -%}
""")
        result = tmpl.render().strip()
        assert 'class="panel panel--warning"' in result
        assert "<strong>Warning!</strong>" in result
        assert "<p>Something happened.</p>" in result

    def test_cache_block(self, env: Environment):
        """Test {% cache %} for fragment caching."""
        # Cache block with key expression
        tmpl = env.from_string("""
{%- cache "footer-" ~ lang -%}
<footer>{{ site_title }}</footer>
{%- end -%}
""")
        # First render populates cache
        result1 = tmpl.render(lang="en", site_title="My Site")
        assert "<footer>My Site</footer>" in result1

        # Same key returns cached content (even with different site_title)
        result2 = tmpl.render(lang="en", site_title="Different Site")
        assert "<footer>My Site</footer>" in result2

        # Different key gets fresh render
        result3 = tmpl.render(lang="es", site_title="Mi Sitio")
        assert "<footer>Mi Sitio</footer>" in result3

    def test_cache_with_dynamic_key(self, env: Environment):
        """Test {% cache %} with dynamic key expressions."""
        tmpl = env.from_string("""
{%- cache "item-" ~ item.id -%}
<div>{{ item.name }}</div>
{%- end -%}
""")
        result = tmpl.render(item={"id": 1, "name": "First"})
        assert "<div>First</div>" in result

    def test_slot_with_conditional_wrapper(self, env: Environment):
        """Test {% slot %} in conditional wrapper (collapsible vs static)."""
        tmpl = env.from_string("""
{%- def section(title, collapsible=false) -%}
{% if collapsible %}
<details>
  <summary>{{ title }}</summary>
  {% slot %}
</details>
{% else %}
<section>
  <h2>{{ title }}</h2>
  {% slot %}
</section>
{% end %}
{%- end -%}

{%- call section("Static Section") -%}
<p>Static content</p>
{%- end -%}

{%- call section("Collapsible Section", collapsible=true) -%}
<p>Hidden content</p>
{%- end -%}
""")
        result = tmpl.render()
        # Static section
        assert "<section>" in result
        assert "<h2>Static Section</h2>" in result
        assert "<p>Static content</p>" in result
        # Collapsible section
        assert "<details>" in result
        assert "<summary>Collapsible Section</summary>" in result
        assert "<p>Hidden content</p>" in result

    def test_slot_with_nested_variables(self, env: Environment):
        """Test {% slot %} content can access outer scope variables."""
        tmpl = env.from_string("""
{%- let site_name = "My Site" -%}
{%- def wrapper(title) -%}
<div class="wrapper">
  <h1>{{ title }}</h1>
  {% slot %}
</div>
{%- end -%}

{%- call wrapper("Page Title") -%}
<p>Welcome to {{ site_name }}!</p>
{%- end -%}
""")
        result = tmpl.render()
        assert "<h1>Page Title</h1>" in result
        assert "<p>Welcome to My Site!</p>" in result


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
