#!/usr/bin/env python3
"""Test Kida from import + extends."""

import sys

sys.path.insert(0, "/Users/llane/Documents/github/python/bengal")

from kida import DictLoader, Environment


def test_from_import_in_child():
    """Test that {% from %} works in child templates with {% extends %}."""
    loader = DictLoader(
        {
            "macros.html": """{% macro greet(name) %}Hello, {{ name }}!{% endmacro %}""",
            "base.html": """<!DOCTYPE html>
<html>
<body>
{% block content %}DEFAULT{% endblock %}
</body>
</html>""",
            "child.html": """{% extends "base.html" %}
{% from "macros.html" import greet %}
{% block content %}
{{ greet("World") }}
{% endblock %}""",
        }
    )

    env = Environment(loader=loader)

    try:
        result = env.get_template("child.html").render()
        print("=== Result ===")
        print(result)
        print()
        if "Hello, World!" in result:
            print("✅ SUCCESS: Macro was called correctly!")
        else:
            print("❌ FAILURE: Expected 'Hello, World!' in output")
    except Exception as e:
        import traceback

        print(f"❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_from_import_in_child()
