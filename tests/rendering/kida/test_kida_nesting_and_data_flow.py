"""Test advanced nesting and data flow in Kida templates.

Tests comprehensive combinations and deep nesting scenarios across:
- Layouts (extends/block)
- Partials (include)
- Functions (def)
- Macros
- Data flow through multiple layers
- Edge cases with deep nesting

This test suite ensures that complex template structures work correctly
and that data flows properly through all layers of nesting.
"""

import pytest

from bengal.rendering.kida import DictLoader, Environment


@pytest.fixture
def env():
    """Create a Kida environment for testing."""
    return Environment()


# =============================================================================
# Deep Nesting: Layouts
# =============================================================================


class TestDeepLayoutNesting:
    """Test deep nesting of layout inheritance (extends/block)."""

    def test_three_level_inheritance(self):
        """Three-level inheritance chain."""
        loader = DictLoader(
            {
                "level1.html": "<html>{% block content %}L1{% endblock %}</html>",
                "level2.html": '{% extends "level1.html" %}{% block content %}L2{% endblock %}',
                "level3.html": '{% extends "level2.html" %}{% block content %}L3{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("level3.html").render()
        assert result == "<html>L3</html>"

    def test_four_level_inheritance(self):
        """Four-level inheritance chain."""
        loader = DictLoader(
            {
                "base.html": "<!DOCTYPE html><html>{% block body %}BASE{% endblock %}</html>",
                "layout.html": '{% extends "base.html" %}{% block body %}LAYOUT{% endblock %}',
                "section.html": '{% extends "layout.html" %}{% block body %}SECTION{% endblock %}',
                "page.html": '{% extends "section.html" %}{% block body %}PAGE{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("page.html").render()
        assert result == "<!DOCTYPE html><html>PAGE</html>"

    def test_multiple_blocks_deep_nesting(self):
        """Multiple blocks at different inheritance levels."""
        loader = DictLoader(
            {
                "base.html": (
                    "<html>"
                    "{% block head %}<head>BASE HEAD</head>{% endblock %}"
                    "{% block body %}<body>BASE BODY</body>{% endblock %}"
                    "</html>"
                ),
                "mid.html": (
                    '{% extends "base.html" %}{% block head %}<head>MID HEAD</head>{% endblock %}'
                ),
                "child.html": (
                    '{% extends "mid.html" %}{% block body %}<body>CHILD BODY</body>{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<head>MID HEAD</head>" in result
        assert "<body>CHILD BODY</body>" in result
        assert "BASE" not in result

    def test_nested_blocks_in_inheritance(self):
        """Nested blocks within inheritance chain."""
        loader = DictLoader(
            {
                "base.html": (
                    "<div>"
                    "{% block outer %}"
                    "{% block inner %}DEFAULT INNER{% endblock %}"
                    "{% endblock %}"
                    "</div>"
                ),
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block outer %}"
                    "OUTER: {% block inner %}CHILD INNER{% endblock %}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "OUTER:" in result
        assert "CHILD INNER" in result
        assert "DEFAULT INNER" not in result


# =============================================================================
# Deep Nesting: Partials
# =============================================================================


class TestDeepPartialNesting:
    """Test deep nesting of partial includes."""

    def test_three_level_partial_chain(self):
        """Three-level partial inclusion chain."""
        loader = DictLoader(
            {
                "partial1.html": "<div>P1{% include 'partial2.html' %}</div>",
                "partial2.html": "<span>P2{% include 'partial3.html' %}</span>",
                "partial3.html": "<p>P3</p>",
                "main.html": "{% include 'partial1.html' %}",
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "<div>P1" in result
        assert "<span>P2" in result
        assert "<p>P3</p>" in result

    def test_partial_with_context_flow(self):
        """Partial chain with context variables flowing through."""
        loader = DictLoader(
            {
                "outer.html": "<outer>{{ value }}{% include 'middle.html' %}</outer>",
                "middle.html": "<middle>{{ value }}{% include 'inner.html' %}</middle>",
                "inner.html": "<inner>{{ value }}</inner>",
                "main.html": "{% include 'outer.html' %}",
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render(value="TEST")
        assert "<outer>TEST" in result
        assert "<middle>TEST" in result
        assert "<inner>TEST</inner>" in result

    def test_partial_with_set_variables(self):
        """Partials with set variables that flow through."""
        loader = DictLoader(
            {
                "setup.html": "{% set x = 10 %}{% include 'use.html' %}",
                "use.html": "Value: {{ x }}",
                "main.html": "{% include 'setup.html' %}",
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "Value: 10" in result


# =============================================================================
# Deep Nesting: Functions (def)
# =============================================================================


class TestDeepDefNesting:
    """Test deep nesting of function definitions."""

    def test_three_level_def_nesting(self):
        """Three levels of nested def calls."""
        tmpl_str = (
            "{% def level1(x) %}"
            "L1[{{ x }}]"
            "{% def level2(y) %}"
            "L2[{{ y }}]"
            "{% def level3(z) %}"
            "L3[{{ z }}]"
            "{% enddef %}"
            "{{ level3('z') }}"
            "{% enddef %}"
            "{{ level2('y') }}"
            "{% enddef %}"
            "{{ level1('x') }}"
        )
        env = Environment()
        result = env.from_string(tmpl_str).render()
        assert "L1[x]" in result
        assert "L2[y]" in result
        assert "L3[z]" in result

    def test_recursive_def_deep(self):
        """Deep recursive function calls."""
        tmpl_str = (
            "{% def factorial(n) %}"
            "{% if n <= 1 %}"
            "1"
            "{% else %}"
            "{{ n }}*{{ factorial(n - 1) }}"
            "{% endif %}"
            "{% enddef %}"
            "{{ factorial(4) }}"
        )
        env = Environment()
        result = env.from_string(tmpl_str).render()
        # Should contain the multiplication chain
        assert "4" in result
        assert "3" in result
        assert "2" in result
        assert "1" in result

    def test_def_with_outer_scope_access(self):
        """Def accessing variables from multiple outer scopes."""
        tmpl_str = (
            "{% set global_var = 'GLOBAL' %}"
            "{% def outer(x) %}"
            "{% set outer_var = 'OUTER' %}"
            "{% def inner(y) %}"
            "{{ global_var }}-{{ outer_var }}-{{ x }}-{{ y }}"
            "{% enddef %}"
            "{{ inner('INNER') }}"
            "{% enddef %}"
            "{{ outer('X') }}"
        )
        env = Environment()
        result = env.from_string(tmpl_str).render()
        assert "GLOBAL" in result
        assert "OUTER" in result
        assert "X" in result
        assert "INNER" in result


# =============================================================================
# Combinations: Layouts + Partials
# =============================================================================


class TestLayoutPartialCombinations:
    """Test combinations of layouts and partials."""

    def test_layout_with_partial_in_block(self):
        """Layout with partial included in block."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "header.html": "<header>Header</header>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "header.html" %}Content{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<html>" in result
        assert "<header>Header</header>" in result
        assert "Content" in result

    def test_layout_with_partial_in_base(self):
        """Layout with partial included in base template."""
        loader = DictLoader(
            {
                "base.html": (
                    '<html>{% include "header.html" %}{% block content %}{% endblock %}</html>'
                ),
                "header.html": "<header>Header</header>",
                "child.html": '{% extends "base.html" %}{% block content %}Content{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<header>Header</header>" in result
        assert "Content" in result

    def test_multi_level_layout_with_partials(self):
        """Multi-level layout with partials at each level."""
        loader = DictLoader(
            {
                "base.html": (
                    '<html>{% include "base_header.html" %}{% block content %}{% endblock %}</html>'
                ),
                "base_header.html": "<header>Base Header</header>",
                "mid.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "mid_content.html" %}{% endblock %}'
                ),
                "mid_content.html": "<div>Mid Content</div>",
                "child.html": (
                    '{% extends "mid.html" %}'
                    '{% block content %}{% include "child_content.html" %}{% endblock %}'
                ),
                "child_content.html": "<section>Child Content</section>",
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<header>Base Header</header>" in result
        assert "<section>Child Content</section>" in result

    def test_partial_in_partial_in_layout(self):
        """Partial including another partial, all in a layout."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "outer_partial.html": 'Outer{% include "inner_partial.html" %}',
                "inner_partial.html": "Inner",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "outer_partial.html" %}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Outer" in result
        assert "Inner" in result


# =============================================================================
# Combinations: Layouts + Defs
# =============================================================================


class TestLayoutDefCombinations:
    """Test combinations of layouts and defs."""

    def test_def_in_layout_block(self):
        """Def defined and used in layout block."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def card(title) %}<div>{{ title }}</div>{% enddef %}"
                    "{{ card('Test') }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<div>Test</div>" in result

    def test_def_in_base_used_in_child(self):
        """Def defined in base, used in child block."""
        loader = DictLoader(
            {
                "base.html": (
                    "{% def helper(text) %}<strong>{{ text }}</strong>{% enddef %}"
                    "<html>{% block content %}{% endblock %}</html>"
                ),
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}{{ helper('Hello') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<strong>Hello</strong>" in result

    def test_def_with_outer_scope_in_layout(self):
        """Def accessing outer scope variables in layout context."""
        loader = DictLoader(
            {
                "base.html": ("<html>{% block content %}{% endblock %}</html>"),
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% set site_name = 'Bengal' %}"
                    "{% def show_site() %}{{ site_name }}{% enddef %}"
                    "{{ show_site() }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Bengal" in result

    def test_nested_defs_in_layout(self):
        """Nested defs within layout blocks."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def outer(x) %}"
                    "{% def inner(y) %}{{ x }}-{{ y }}{% enddef %}"
                    "{{ inner('inner') }}"
                    "{% enddef %}"
                    "{{ outer('outer') }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "outer-inner" in result


# =============================================================================
# Combinations: Partials + Defs
# =============================================================================


class TestPartialDefCombinations:
    """Test combinations of partials and defs."""

    def test_def_in_partial(self):
        """Def defined in partial."""
        loader = DictLoader(
            {
                "partial.html": "{% def greet(name) %}Hello {{ name }}!{% enddef %}{{ greet('World') }}",
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "Hello World!" in result

    def test_def_used_in_partial(self):
        """Def defined in main, used in partial."""
        loader = DictLoader(
            {
                "partial.html": "{{ format('Test') }}",
                "main.html": (
                    "{% def format(text) %}<b>{{ text }}</b>{% enddef %}"
                    '{% include "partial.html" %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "<b>Test</b>" in result

    def test_partial_with_def_accessing_context(self):
        """Partial with def that accesses context variables."""
        loader = DictLoader(
            {
                "partial.html": ("{% def show_value() %}{{ value }}{% enddef %}{{ show_value() }}"),
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render(value=42)
        assert "42" in result

    def test_nested_partials_with_defs(self):
        """Nested partials, each with their own defs."""
        loader = DictLoader(
            {
                "inner.html": "{% def inner_func() %}INNER{% enddef %}{{ inner_func() }}",
                "outer.html": (
                    "{% def outer_func() %}OUTER{% enddef %}"
                    "{{ outer_func() }}"
                    '{% include "inner.html" %}'
                ),
                "main.html": '{% include "outer.html" %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "OUTER" in result
        assert "INNER" in result


# =============================================================================
# Combinations: All Three (Layouts + Partials + Defs)
# =============================================================================


class TestAllThreeCombinations:
    """Test combinations of layouts, partials, and defs together."""

    def test_layout_partial_def_together(self):
        """Layout with partial that uses def."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "component.html": (
                    "{% def render_item(item) %}<li>{{ item }}</li>{% enddef %}"
                    "{{ render_item('Item') }}"
                ),
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "component.html" %}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<li>Item</li>" in result

    def test_def_in_layout_block_calling_partial_def(self):
        """Def in layout block that calls a def from a partial."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "utils.html": "{% def format(text) %}<em>{{ text }}</em>{% enddef %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "utils.html" import format %}'
                    "{% block content %}"
                    "{% def wrapper(x) %}{{ format(x) }}{% enddef %}"
                    "{{ wrapper('Test') }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<em>Test</em>" in result

    def test_multi_level_with_all_features(self):
        """Multi-level layout with partials and defs at each level.

        Note: Defs defined in mid.html are available to partials included
        in mid.html's blocks, but when child.html extends mid.html and
        overrides the block, the defs from mid.html may not be accessible
        to partials included in child.html's block override.
        """
        loader = DictLoader(
            {
                "base.html": (
                    "{% def base_helper() %}BASE{% enddef %}"
                    "<html>"
                    '{% include "base_header.html" %}'
                    "{% block content %}{% endblock %}"
                    "</html>"
                ),
                "base_header.html": "{{ base_helper() }}",
                "mid.html": (
                    '{% extends "base.html" %}'
                    "{% def mid_helper() %}MID{% enddef %}"
                    "{% block content %}{{ mid_helper() }}{% endblock %}"
                ),
                "child.html": (
                    '{% extends "mid.html" %}'
                    "{% def child_helper() %}CHILD{% enddef %}"
                    "{% block content %}{{ child_helper() }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "BASE" in result
        assert "CHILD" in result
        # MID may not appear if child overrides the block completely


# =============================================================================
# Data Flow: Variables Through Layers
# =============================================================================


class TestDataFlowThroughLayers:
    """Test how data flows through multiple template layers."""

    def test_context_through_layout_chain(self):
        """Context variables flow through layout inheritance chain."""
        loader = DictLoader(
            {
                "base.html": "<html>{{ title }}{% block content %}{% endblock %}</html>",
                "mid.html": '{% extends "base.html" %}{% block content %}{{ title }}{% endblock %}',
                "child.html": '{% extends "mid.html" %}{% block content %}{{ title }}{% endblock %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render(title="Test")
        # Appears in base template and in child's block (mid's block is overridden)
        # So 2 occurrences: base template + child block
        assert result.count("Test") == 2
        assert "<html>Test" in result

    def test_set_variable_through_partials(self):
        """Set variable flows through partial chain."""
        loader = DictLoader(
            {
                "level1.html": "{% set x = 1 %}{% include 'level2.html' %}",
                "level2.html": "{% set y = 2 %}{{ x }}{{ y }}{% include 'level3.html' %}",
                "level3.html": "{% set z = 3 %}{{ x }}{{ y }}{{ z }}",
                "main.html": "{% include 'level1.html' %}",
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_context_to_def_to_partial(self):
        """Context → def → partial data flow."""
        loader = DictLoader(
            {
                "partial.html": "{{ processed }}",
                "main.html": (
                    "{% def process(value) %}{{ value|upper }}{% enddef %}"
                    "{% set processed = process('test') %}"
                    '{% include "partial.html" %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "TEST" in result

    def test_nested_data_flow(self):
        """Complex nested data flow: context → layout → partial → def."""
        loader = DictLoader(
            {
                "base.html": ("<html>{{ site_name }}{% block content %}{% endblock %}</html>"),
                "partial.html": (
                    "{% def show_site() %}{{ site_name }}{% enddef %}{{ show_site() }}"
                ),
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "partial.html" %}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render(site_name="Bengal")
        # Should appear twice: once in base, once via def in partial
        assert result.count("Bengal") >= 2


# =============================================================================
# Edge Cases: Deep Nesting
# =============================================================================


class TestDeepNestingEdgeCases:
    """Edge cases with very deep nesting."""

    def test_def_in_block_in_layout(self):
        """Def defined in base template, used in child block.

        Note: Defs defined in base templates are accessible in child blocks.
        However, there is a KNOWN BUG: defs are NOT accessible when called
        inside conditionals ({% if %}) within blocks during inheritance.
        Defs work fine in loops ({% for %}) and directly in blocks.
        This test verifies the basic case (direct call) works.
        """
        loader = DictLoader(
            {
                "base.html": (
                    "{% def inner() %}Inner{% enddef %}"
                    "<html>{% block content %}{% endblock %}</html>"
                ),
                "child.html": (
                    '{% extends "base.html" %}{% block content %}{{ inner() }}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Inner" in result

    def test_include_in_def_in_block(self):
        """Include inside def inside block."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "partial.html": "Partial",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% def wrapper() %}"
                    '{% include "partial.html" %}'
                    "{% enddef %}"
                    "{% block content %}"
                    "{{ wrapper() }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Partial" in result

    def test_block_in_partial_in_layout(self):
        """Block inside partial inside layout.

        Note: Blocks defined in partials don't work the same way as blocks
        in templates. Blocks need to be in the template itself for inheritance.
        This test verifies the default behavior when blocks are in partials.
        """
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "partial.html": "{% block section %}Default{% endblock %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "partial.html" %}{% endblock %}'
                    "{% block section %}Override{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        # Blocks in partials don't participate in inheritance the same way
        # The partial's default will be used, not the override
        assert "Default" in result

    def test_loop_in_def_in_block_in_layout(self):
        """Loop inside def inside block inside layout."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def render_list(items) %}"
                    "{% for item in items %}{{ item }}{% endfor %}"
                    "{% enddef %}"
                    "{{ render_list([1, 2, 3]) }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_conditional_in_partial_in_def_in_layout(self):
        """Conditional inside partial inside def inside layout block."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "partial.html": "{% if show %}Visible{% endif %}",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def render_partial() %}"
                    '{% include "partial.html" %}'
                    "{% enddef %}"
                    "{{ render_partial() }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result_true = env.get_template("child.html").render(show=True)
        result_false = env.get_template("child.html").render(show=False)
        assert "Visible" in result_true
        assert "Visible" not in result_false


# =============================================================================
# Call/Slot Patterns with Nesting
# =============================================================================


class TestCallSlotNesting:
    """Test call/slot patterns with various nesting scenarios."""

    def test_call_in_block(self):
        """Call block inside layout block."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def card(title) %}<div>{{ title }}{% slot %}</div>{% enddef %}"
                    "{% call card('Test') %}Content{% endcall %}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<div>Test" in result
        assert "Content" in result

    def test_call_in_partial(self):
        """Call block inside partial."""
        loader = DictLoader(
            {
                "partial.html": (
                    "{% def wrapper() %}<div>{% slot %}</div>{% enddef %}"
                    "{% call wrapper() %}Partial Content{% endcall %}"
                ),
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "<div>" in result
        assert "Partial Content" in result

    def test_nested_calls_in_layout(self):
        """Nested call blocks in layout."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% def outer() %}<outer>{% slot %}</outer>{% enddef %}"
                    "{% def inner() %}<inner>{% slot %}</inner>{% enddef %}"
                    "{% call outer() %}{% call inner() %}Nested{% endcall %}{% endcall %}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "<outer>" in result
        assert "<inner>Nested</inner>" in result
        assert "</outer>" in result


# =============================================================================
# Capture with Nesting
# =============================================================================


class TestCaptureNesting:
    """Test capture blocks with various nesting scenarios."""

    def test_capture_in_block(self):
        """Capture block inside layout block."""
        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    "{% block content %}"
                    "{% capture content %}Captured{% endcapture %}"
                    "{{ content }}"
                    "{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Captured" in result

    def test_capture_in_def(self):
        """Capture block inside def."""
        loader = DictLoader(
            {
                "main.html": (
                    "{% def make_content() %}"
                    "{% capture result %}Result{% endcapture %}"
                    "{{ result }}"
                    "{% enddef %}"
                    "{{ make_content() }}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "Result" in result

    def test_capture_in_partial(self):
        """Capture block inside partial."""
        loader = DictLoader(
            {
                "partial.html": "{% capture x %}Partial{% endcapture %}{{ x }}",
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "Partial" in result


# =============================================================================
# Import/From with Nesting
# =============================================================================


class TestImportNesting:
    """Test import/from statements with nesting."""

    def test_from_import_in_layout_block(self):
        """From import in layout block."""
        loader = DictLoader(
            {
                "macros.html": "{% def helper(x) %}{{ x }}{% enddef %}",
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% from "macros.html" import helper %}'
                    "{% block content %}{{ helper('Test') }}{% endblock %}"
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "Test" in result

    def test_from_import_in_partial(self):
        """From import in partial."""
        loader = DictLoader(
            {
                "macros.html": "{% def format(x) %}<b>{{ x }}</b>{% enddef %}",
                "partial.html": '{% from "macros.html" import format %}{{ format("Test") }}',
                "main.html": '{% include "partial.html" %}',
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("main.html").render()
        assert "<b>Test</b>" in result

    def test_import_chain_through_layers(self):
        """Import chain through layout → partial → def."""
        loader = DictLoader(
            {
                "utils.html": "{% def util(x) %}{{ x|upper }}{% enddef %}",
                "base.html": "<html>{% block content %}{% endblock %}</html>",
                "partial.html": (
                    '{% from "utils.html" import util %}'
                    "{% def use_util() %}{{ util('test') }}{% enddef %}"
                    "{{ use_util() }}"
                ),
                "child.html": (
                    '{% extends "base.html" %}'
                    '{% block content %}{% include "partial.html" %}{% endblock %}'
                ),
            }
        )
        env = Environment(loader=loader)
        result = env.get_template("child.html").render()
        assert "TEST" in result
