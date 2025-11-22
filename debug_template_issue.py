#!/usr/bin/env python3
"""
Debug the template macro issue.
"""

from pathlib import Path

from bengal.autodoc.template_safety import create_safe_environment


def debug_macro_issue():
    """Debug the macro issue step by step."""
    print("🔍 Debugging template macro issue...")

    # Create template environment
    template_dirs = [Path("bengal/autodoc/templates")]
    env = create_safe_environment(template_dirs)

    # Test 1: Simple safe_section call
    print("\n1️⃣ Testing simple safe_section...")
    simple_template = """
{% from 'macros/safe_macros.md.jinja2' import safe_section %}
{% call safe_section("test") %}
Hello World
{% endcall %}
"""

    try:
        result = env.from_string(simple_template).render()
        print("✅ Simple safe_section works")
    except Exception as e:
        print(f"❌ Simple safe_section failed: {e}")

    # Test 2: Safe_for call
    print("\n2️⃣ Testing safe_for...")
    safe_for_template = """
{% from 'macros/safe_macros.md.jinja2' import safe_for %}
{% call safe_for(['item1', 'item2']) %}
Item: {{ item }}
{% endcall %}
"""

    try:
        result = env.from_string(safe_for_template).render()
        print("✅ Safe_for works")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Safe_for failed: {e}")

    # Test 3: Nested macro calls (the problematic case)
    print("\n3️⃣ Testing nested macro calls...")
    nested_template = """
{% from 'macros/safe_macros.md.jinja2' import safe_section, safe_for %}
{% call safe_section("test") %}
  {% call safe_for(['item1', 'item2']) %}
  Item: {{ item }}
  {% endcall %}
{% endcall %}
"""

    try:
        result = env.from_string(nested_template).render()
        print("✅ Nested macros work")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Nested macros failed: {e}")

    # Test 4: CLI partial content
    print("\n4️⃣ Testing CLI partial content...")
    cli_partial_template = """
{% from 'macros/safe_macros.md.jinja2' import safe_render, safe_for %}
{% set options = [{'name': 'test-option', 'description': 'Test option'}] %}
{% if options %}
## Options
{% call safe_for(options, "*No options available.*") %}
{% call safe_render("option", item) %}
### `{{ item.name }}`
{{ item.description }}
{% endcall %}
{% endcall %}
{% endif %}
"""

    try:
        result = env.from_string(cli_partial_template).render()
        print("✅ CLI partial content works")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ CLI partial content failed: {e}")


if __name__ == "__main__":
    debug_macro_issue()
