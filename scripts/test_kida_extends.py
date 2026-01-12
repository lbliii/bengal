#!/usr/bin/env python3
"""Test Kida extends with blocks."""

import sys

sys.path.insert(0, "/Users/llane/Documents/github/python/bengal")

import tempfile
from pathlib import Path


def test_extends():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "bengal.yaml").write_text("site:\n  title: Test\ntheme: default\n")
        (root / "content").mkdir()
        (root / "content" / "test.md").write_text("---\ntitle: Test\n---\nHello")
        (root / "templates").mkdir()

        from bengal.core.site import Site

        site = Site(root)

        from kida import Environment, FileSystemLoader

        # Create test templates
        (root / "templates" / "parent.html").write_text("""<!DOCTYPE html>
<html>
<body>
{% block content %}DEFAULT{% endblock %}
</body>
</html>""")

        (root / "templates" / "child.html").write_text("""{% extends "parent.html" %}
{% block content %}
CHILD CONTENT
{% endblock %}""")

        env = Environment(loader=FileSystemLoader([root / "templates"]))

        try:
            result = env.get_template("child.html").render({})
            print("Simple extends SUCCESS!")
            print(result)
        except Exception as e:
            import traceback

            print(f"ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    test_extends()
