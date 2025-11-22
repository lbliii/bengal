#!/usr/bin/env python3
"""
Debug the Jinja2 template logic to see why classes aren't rendering.
"""

from pathlib import Path

from jinja2 import Template

from bengal.autodoc.extractors.python import PythonExtractor
from bengal.autodoc.template_safety import create_safe_environment


def debug_template_logic():
    """Debug the template logic step by step."""

    # Extract content
    extractor = PythonExtractor()
    elements = extractor.extract(Path("bengal/core/site.py"))
    module_element = elements[0]

    print(f"📦 Module: {module_element.name}")
    print(f"👥 Children: {len(module_element.children)}")

    # Create template environment
    template_dirs = [Path("bengal/autodoc/templates")]
    env = create_safe_environment(template_dirs)

    # Test the filtering logic directly
    test_template = Template("""
{%- set all_classes = element.children | selectattr('element_type', 'equalto', 'class') | list -%}
All classes: {{ all_classes | length }}
{% for cls in all_classes %}
  - {{ cls.name }} (type: {{ cls.element_type }})
{% endfor %}

{%- set public_classes = [] -%}
{%- for cls in all_classes -%}
  {%- if not cls.name.startswith('_') -%}
    {%- set _ = public_classes.append(cls) -%}
  {%- endif -%}
{%- endfor -%}

Public classes: {{ public_classes | length }}
{% for cls in public_classes %}
  - {{ cls.name }}
{% endfor %}

{% if public_classes %}
HAS PUBLIC CLASSES - SHOULD RENDER
{% else %}
NO PUBLIC CLASSES - WILL NOT RENDER
{% endif %}
""")

    context = {"element": module_element}
    result = test_template.render(context)
    print("🧪 Template logic test:")
    print(result)

    # Test the actual classes partial
    print("\n🧪 Testing actual classes partial...")
    classes_template = env.get_template("python/partials/module_classes.md.jinja2")
    classes_result = classes_template.render(context)

    print(f"📄 Classes partial result ({len(classes_result)} chars):")
    print("=" * 50)
    print(classes_result)
    print("=" * 50)


if __name__ == "__main__":
    debug_template_logic()
