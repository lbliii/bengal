"""
Integration tests for native notebook support.

Tests that .ipynb files are discovered, rendered, and that the source
notebook is copied to output for download links.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions

_MINIMAL_NOTEBOOK = """{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": ["# Demo Notebook", "\\n", "This is a test."]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": ["print(42)"],
      "outputs": []
    }
  ],
  "metadata": {"kernelspec": {"name": "python3", "language": "python"}},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""


class TestNotebookFeature:
    """Test native notebook discovery, rendering, and output."""

    def test_notebook_builds_and_copies_ipynb_to_output(self, tmp_path: Path) -> None:
        """Notebook is discovered, rendered, and .ipynb copied to output dir."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "bengal.toml").write_text("""
[site]
title = "Notebook Test"
baseurl = "/"

[build]
output_dir = "public"

[theme]
name = "default"
""")

        content_dir = site_dir / "content"
        content_dir.mkdir()

        (content_dir / "_index.md").write_text("""---
title: Home
---
Welcome.
""")

        notebooks_dir = content_dir / "notebooks"
        notebooks_dir.mkdir()

        (notebooks_dir / "_index.md").write_text("""---
title: Notebooks
content_type: notebook
---
""")

        (notebooks_dir / "demo.ipynb").write_text(_MINIMAL_NOTEBOOK, encoding="utf-8")

        site = Site.from_config(site_dir)
        site.build(BuildOptions(incremental=False))

        # HTML page exists
        html_path = site_dir / "public" / "notebooks" / "demo" / "index.html"
        assert html_path.exists(), f"Expected {html_path}"
        html_content = html_path.read_text()
        assert "Demo Notebook" in html_content
        assert "This is a test" in html_content
        assert "print(42)" in html_content

        # .ipynb copied alongside for download
        ipynb_path = site_dir / "public" / "notebooks" / "demo" / "demo.ipynb"
        assert ipynb_path.exists(), f"Expected .ipynb at {ipynb_path}"
        ipynb_content = ipynb_path.read_text()
        assert "Demo Notebook" in ipynb_content
        assert "print(42)" in ipynb_content
