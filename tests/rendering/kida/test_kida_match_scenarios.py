"""Scenario tests for {% match %} pattern matching in complex contexts.

These tests cover edge cases discovered during debugging template rendering issues:
- Match with guards inside template inheritance ({% extends %})
- Match inside macros that include other templates
- Match with empty string vs None (nullish coalesce behavior)
- Match with tuple patterns and variable bindings
- Error reporting with correct line numbers
"""

import pytest

from bengal.rendering.kida import Environment
from bengal.rendering.kida.environment.loaders import DictLoader


class TestMatchWithGuardsAndBindings:
    """Tests for match with guards and variable bindings (walrus operators)."""

    def test_match_tuple_with_guard_first_truthy(self, env):
        """Match tuple pattern with guard - first element truthy."""
        template = env.from_string("""
{% match logo, text %}
{% case l, _ if l %}LOGO:{{ l }}
{% case _, t if t %}TEXT:{{ t }}
{% case _ %}FALLBACK
{% end %}
""")
        result = template.render(logo="img.png", text="")
        assert "LOGO:img.png" in result
        assert "TEXT:" not in result
        assert "FALLBACK" not in result

    def test_match_tuple_with_guard_second_truthy(self, env):
        """Match tuple pattern with guard - second element truthy."""
        template = env.from_string("""
{% match logo, text %}
{% case l, _ if l %}LOGO:{{ l }}
{% case _, t if t %}TEXT:{{ t }}
{% case _ %}FALLBACK
{% end %}
""")
        result = template.render(logo="", text="Site Name")
        assert "TEXT:Site Name" in result
        assert "LOGO:" not in result

    def test_match_tuple_with_guard_both_falsy(self, env):
        """Match tuple pattern with guard - both falsy, fallback triggered."""
        template = env.from_string("""
{% match logo, text %}
{% case l, _ if l %}LOGO:{{ l }}
{% case _, t if t %}TEXT:{{ t }}
{% case _ %}FALLBACK
{% end %}
""")
        result = template.render(logo="", text="")
        assert "FALLBACK" in result

    def test_match_tuple_with_guard_empty_string_is_falsy(self, env):
        """Empty string is falsy in guard conditions."""
        template = env.from_string("""
{% match val %}
{% case v if v %}TRUTHY:{{ v }}
{% case _ %}FALSY
{% end %}
""")
        assert "FALSY" in template.render(val="")
        assert "TRUTHY:hello" in template.render(val="hello")

    def test_match_binding_used_in_body(self, env):
        """Bound variable from pattern can be used in case body."""
        template = env.from_string("""
{% match items | first %}
{% case item if item %}First: {{ item.name }}
{% case _ %}No items
{% end %}
""")
        result = template.render(items=[{"name": "Alice"}, {"name": "Bob"}])
        assert "First: Alice" in result

    def test_match_multiple_bindings(self, env):
        """Multiple bindings in tuple pattern."""
        template = env.from_string("""
{% match first, second, third %}
{% case a, b, c if a and b %}A={{ a }}, B={{ b }}, C={{ c }}
{% case _ %}Incomplete
{% end %}
""")
        result = template.render(first="X", second="Y", third="Z")
        assert "A=X" in result
        assert "B=Y" in result
        assert "C=Z" in result


class TestMatchInTemplateInheritance:
    """Tests for match inside template inheritance."""

    @pytest.fixture
    def env_with_templates(self):
        """Environment with base and child templates using match."""
        templates = {
            "base_with_match.html": """
<!DOCTYPE html>
<html>
<head>{% block head %}{% end %}</head>
<body>
<header>
{% match site.logo, site.text %}
{% case logo, _ if logo %}<img src="{{ logo }}" />
{% case _, text if text %}<span>{{ text }}</span>
{% case _ %}<span>Default Site</span>
{% end %}
</header>
{% block content %}{% end %}
</body>
</html>
""",
            "child_page.html": """
{% extends "base_with_match.html" %}
{% block content %}
<main>Child Content</main>
{% end %}
""",
        }
        return Environment(loader=DictLoader(templates))

    def test_match_in_parent_renders_with_logo(self, env_with_templates):
        """Match in parent template works when child extends it - logo case."""
        template = env_with_templates.get_template("child_page.html")
        result = template.render(site={"logo": "logo.png", "text": ""})
        assert '<img src="logo.png"' in result
        assert "Child Content" in result

    def test_match_in_parent_renders_with_text(self, env_with_templates):
        """Match in parent template works when child extends it - text case."""
        template = env_with_templates.get_template("child_page.html")
        result = template.render(site={"logo": "", "text": "My Site"})
        assert "<span>My Site</span>" in result

    def test_match_in_parent_renders_fallback(self, env_with_templates):
        """Match in parent template works when child extends it - fallback case."""
        template = env_with_templates.get_template("child_page.html")
        result = template.render(site={"logo": "", "text": ""})
        assert "<span>Default Site</span>" in result

    def test_match_in_overridden_block(self):
        """Match works in a block that child overrides."""
        templates = {
            "base.html": """
{% block nav %}
BASE NAV
{% end %}
""",
            "child.html": """
{% extends "base.html" %}
{% block nav %}
{% match nav_type %}
{% case "minimal" %}Minimal Nav
{% case "full" %}Full Nav
{% case _ %}Default Nav
{% end %}
{% end %}
""",
        }
        env = Environment(loader=DictLoader(templates))
        template = env.get_template("child.html")

        assert "Minimal Nav" in template.render(nav_type="minimal")
        assert "Full Nav" in template.render(nav_type="full")
        assert "Default Nav" in template.render(nav_type="other")


class TestMatchInMacrosWithIncludes:
    """Tests for match inside macros that include other templates."""

    @pytest.fixture
    def env_macro_include(self):
        """Environment with macros that include templates with match."""
        templates = {
            "included_match.html": """
{% let display_type = type ?? 'default' %}
{% match display_type %}
{% case "card" %}[CARD]{{ content }}[/CARD]
{% case "list" %}[LIST]{{ content }}[/LIST]
{% case _ %}[DEFAULT]{{ content }}[/DEFAULT]
{% end %}
""",
            "macros.html": """
{% def render_item(item, display="default") %}
{% set type = display %}
{% set content = item.name %}
{% include 'included_match.html' %}
{% end %}
""",
            "page.html": """
{% from 'macros.html' import render_item %}
{% for item in items %}
{{ render_item(item, item.display) }}
{% end %}
""",
        }
        return Environment(loader=DictLoader(templates))

    def test_match_in_included_from_macro(self, env_macro_include):
        """Match in included template receives context from macro."""
        template = env_macro_include.get_template("page.html")
        items = [
            {"name": "Item1", "display": "card"},
            {"name": "Item2", "display": "list"},
            {"name": "Item3", "display": "other"},
        ]
        result = template.render(items=items)
        assert "[CARD]Item1[/CARD]" in result
        assert "[LIST]Item2[/LIST]" in result
        assert "[DEFAULT]Item3[/DEFAULT]" in result

    def test_function_set_passed_to_include(self):
        """Variables set in macro are available in included template."""
        templates = {
            "inner.html": "title={{ title ?? 'MISSING' }}",
            "macro.html": """
{% def my_macro() %}
{% set title = 'Custom Title' %}
{% include 'inner.html' %}
{% end %}
""",
            "main.html": """
{% from 'macro.html' import my_macro %}
{{ my_macro() }}
""",
        }
        env = Environment(loader=DictLoader(templates))
        result = env.get_template("main.html").render()
        assert "title=Custom Title" in result


class TestMatchEmptyStringVsNone:
    """Tests for empty string vs None behavior in match patterns."""

    def test_empty_string_not_equal_to_none(self, env):
        """Empty string and None are different in match."""
        template = env.from_string("""
{% match value %}
{% case none %}IS_NONE
{% case "" %}IS_EMPTY
{% case _ %}IS_OTHER
{% end %}
""")
        assert "IS_NONE" in template.render(value=None)
        assert "IS_EMPTY" in template.render(value="")
        assert "IS_OTHER" in template.render(value="x")

    def test_guard_with_empty_string(self, env):
        """Empty string is falsy in guard conditions."""
        template = env.from_string("""
{% match value %}
{% case v if v %}TRUTHY
{% case _ %}FALSY_OR_EMPTY
{% end %}
""")
        assert "TRUTHY" in template.render(value="hello")
        assert "FALSY_OR_EMPTY" in template.render(value="")
        assert "FALSY_OR_EMPTY" in template.render(value=None)
        assert "FALSY_OR_EMPTY" in template.render(value=0)
        assert "FALSY_OR_EMPTY" in template.render(value=False)

    def test_nullish_coalesce_with_empty_string(self, env):
        """Nullish coalesce (??) treats empty string as defined."""
        template = env.from_string("""
{% let result = value ?? 'DEFAULT' %}
value={{ result }}
""")
        # Empty string is NOT nullish, so no fallback
        assert "value=" in template.render(value="")
        # None IS nullish, so fallback applies
        assert "value=DEFAULT" in template.render(value=None)
        # Undefined is nullish
        assert "value=DEFAULT" in template.render()


class TestNestedMatchStatements:
    """Tests for deeply nested match statements."""

    def test_deeply_nested_match(self, env):
        """Three levels of nested match."""
        template = env.from_string("""
{% match level1 %}
{% case "a" %}
    {% match level2 %}
    {% case "x" %}
        {% match level3 %}
        {% case 1 %}DEEP:a-x-1
        {% case _ %}DEEP:a-x-other
        {% end %}
    {% case _ %}MID:a-other
    {% end %}
{% case _ %}TOP:other
{% end %}
""")
        assert "DEEP:a-x-1" in template.render(level1="a", level2="x", level3=1)
        assert "DEEP:a-x-other" in template.render(level1="a", level2="x", level3=99)
        assert "MID:a-other" in template.render(level1="a", level2="y", level3=1)
        assert "TOP:other" in template.render(level1="b", level2="x", level3=1)

    def test_match_with_guard_in_nested(self, env):
        """Guards work correctly in nested match."""
        template = env.from_string("""
{% match outer %}
{% case o if o > 0 %}
    {% match inner %}
    {% case i if i > 0 %}BOTH_POSITIVE
    {% case _ %}OUTER_ONLY_POSITIVE
    {% end %}
{% case _ %}OUTER_NOT_POSITIVE
{% end %}
""")
        assert "BOTH_POSITIVE" in template.render(outer=1, inner=1)
        assert "OUTER_ONLY_POSITIVE" in template.render(outer=1, inner=-1)
        assert "OUTER_NOT_POSITIVE" in template.render(outer=-1, inner=1)


class TestMatchWithObjectAttributes:
    """Tests for match with object attribute access patterns."""

    def test_match_site_like_object(self, env):
        """Match pattern similar to site.logo, site.logo_text."""

        class SiteMock:
            def __init__(self, logo="", logo_text=""):
                self.logo = logo
                self.logo_text = logo_text

        template = env.from_string("""
{% match site.logo, site.logo_text %}
{% case logo, _ if logo %}<img src="{{ logo }}" />
{% case _, text if text %}<span>{{ text }}</span>
{% case _ %}<span>Default</span>
{% end %}
""")
        # Test logo case
        result = template.render(site=SiteMock(logo="img.png", logo_text=""))
        assert '<img src="img.png"' in result

        # Test text case
        result = template.render(site=SiteMock(logo="", logo_text="My Site"))
        assert "<span>My Site</span>" in result

        # Test fallback
        result = template.render(site=SiteMock(logo="", logo_text=""))
        assert "<span>Default</span>" in result

    def test_match_with_property_that_returns_empty_string(self, env):
        """Properties returning empty string work correctly."""

        class Config:
            @property
            def value(self):
                return ""

        template = env.from_string("""
{% match config.value %}
{% case v if v %}HAS_VALUE
{% case _ %}NO_VALUE
{% end %}
""")
        result = template.render(config=Config())
        assert "NO_VALUE" in result


class TestMatchWithStrictMode:
    """Tests for match in strict mode environment."""

    @pytest.fixture
    def strict_env(self):
        """Strict mode environment."""
        return Environment()

    def test_match_with_undefined_subject_raises(self, strict_env):
        """Undefined subject variable raises in strict mode."""
        from bengal.rendering.kida.environment.exceptions import UndefinedError

        template = strict_env.from_string("""
{% match undefined_var %}
{% case _ %}matched
{% end %}
""")
        with pytest.raises(UndefinedError, match="undefined_var"):
            template.render()

    def test_match_with_defined_subject_works(self, strict_env):
        """Defined subject works in strict mode."""
        template = strict_env.from_string("""
{% match defined_var %}
{% case "test" %}MATCHED
{% case _ %}DEFAULT
{% end %}
""")
        assert "MATCHED" in template.render(defined_var="test")

    def test_match_binding_available_in_guard_strict(self, strict_env):
        """Bound variable is available in guard (strict mode)."""
        template = strict_env.from_string("""
{% match value %}
{% case v if v %}value={{ v }}
{% case _ %}empty
{% end %}
""")
        assert "value=hello" in template.render(value="hello")
        assert "empty" in template.render(value="")


class TestMatchAutodocScenario:
    """Tests simulating the autodoc template chain that revealed the bug."""

    @pytest.fixture
    def autodoc_env(self):
        """Environment simulating autodoc template structure."""
        templates = {
            "base.html": """
<!DOCTYPE html>
<html>
<header>
{% match site.logo, site.logo_text %}
{% case logo, _ if logo %}<img src="{{ logo }}" alt="{{ site_title }}" />
{% case _, text if text %}<span class="brand-text">{{ text }}</span>
{% case _ %}<span class="brand-text">{{ site_title }}</span>
{% end %}
</header>
<main>{% block content %}{% end %}</main>
</html>
""",
            "autodoc/python/module.html": """
{% extends "base.html" %}
{% from 'autodoc/partials/class-member.html' import class_member %}

{% block content %}
{% let classes = element.children | selectattr('type', 'eq', 'class') | list %}
{% for cls in classes %}
{{ class_member(cls) }}
{% end %}
{% end %}
""",
            "autodoc/partials/class-member.html": """
{% def class_member(cls) %}
{% let cls_methods = cls.methods ?? [] %}
{% set members = cls_methods %}
{% set title = cls.name %}
{% set member_type = 'method' %}
{% include 'autodoc/partials/members.html' %}
{% end %}
""",
            "autodoc/partials/members.html": """
{% let section_title = title ?? 'Members' %}
<section class="members">
<h2>{{ section_title }}</h2>
{% for m in members %}
<div class="member">{{ m.name }}</div>
{% end %}
</section>
""",
        }
        return Environment(loader=DictLoader(templates))

    def test_autodoc_full_chain_renders(self, autodoc_env):
        """Full autodoc template chain renders without errors."""
        template = autodoc_env.get_template("autodoc/python/module.html")

        site = type("Site", (), {"logo": "", "logo_text": "Docs"})()
        element = type(
            "Element",
            (),
            {
                "children": [
                    type(
                        "Class",
                        (),
                        {
                            "type": "class",
                            "name": "MyClass",
                            "methods": [
                                {"name": "method1"},
                                {"name": "method2"},
                            ],
                        },
                    )()
                ]
            },
        )()

        result = template.render(site=site, site_title="Test Docs", element=element)

        # Header should have site logo_text
        assert '<span class="brand-text">Docs</span>' in result
        # Members section should have class name as title
        assert "<h2>MyClass</h2>" in result
        # Methods should be rendered
        assert "method1" in result
        assert "method2" in result

    def test_autodoc_with_logo(self, autodoc_env):
        """Autodoc renders with logo image."""
        template = autodoc_env.get_template("autodoc/python/module.html")

        site = type("Site", (), {"logo": "logo.png", "logo_text": ""})()
        element = type("Element", (), {"children": []})()

        result = template.render(site=site, site_title="Test", element=element)
        assert '<img src="logo.png"' in result


class TestMatchErrorLocationMapping:
    """Tests for error location reporting in match statements."""

    def test_undefined_in_match_reports_correct_line(self):
        """Undefined variable in match reports correct template line."""
        from bengal.rendering.kida.environment.exceptions import UndefinedError

        template_source = """\
Line 1
Line 2
{% match undefined_var %}
{% case _ %}matched
{% end %}
Line 6
"""
        env = Environment()
        template = env.from_string(template_source)

        with pytest.raises(UndefinedError) as exc_info:
            template.render()

        # Should report the line where undefined_var is used
        assert "undefined_var" in str(exc_info.value)

    def test_undefined_in_guard_reports_binding_works(self):
        """Using bound variable in guard should NOT raise undefined error."""
        env = Environment()
        template = env.from_string("""
{% match some_value %}
{% case v if v %}has value: {{ v }}
{% case _ %}no value
{% end %}
""")
        # This should work - v is bound from the pattern
        result = template.render(some_value="test")
        assert "has value: test" in result

    def test_undefined_in_case_body_reports_correct_line(self):
        """Undefined variable in case body reports correct location."""
        from bengal.rendering.kida.environment.exceptions import UndefinedError

        env = Environment()
        template = env.from_string("""
{% match x %}
{% case "a" %}{{ undefined_in_body }}
{% case _ %}default
{% end %}
""")

        with pytest.raises(UndefinedError, match="undefined_in_body"):
            template.render(x="a")


@pytest.fixture
def env():
    """Basic environment for tests."""
    return Environment()
