"""Unit tests for NotebookConverter."""

from __future__ import annotations

from pathlib import Path

from bengal.content.notebook.converter import NotebookConverter


def test_convert_minimal_notebook(tmp_path: Path) -> None:
    """Convert a minimal notebook to markdown."""
    nb_content = """{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": ["# Hello", "\\n", "World"]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": ["print(42)"],
      "outputs": []
    }
  ],
  "metadata": {
    "kernelspec": {"name": "python3", "language": "python"}
  },
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    nb_path = tmp_path / "test.ipynb"
    nb_path.write_text(nb_content, encoding="utf-8")

    content, metadata = NotebookConverter.convert(nb_path)

    assert "Hello" in content
    assert "World" in content
    assert "```python" in content
    assert "print(42)" in content
    assert metadata["type"] == "notebook"
    assert metadata["notebook"]["kernel_name"] == "python3"
    assert metadata["notebook"]["cell_count"] == 2


def test_convert_with_pre_read_content(tmp_path: Path) -> None:
    """Converter accepts pre-read content to avoid double read."""
    nb_content = """{
  "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Test"]}],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    nb_path = tmp_path / "test.ipynb"
    nb_path.write_text(nb_content, encoding="utf-8")

    content, metadata = NotebookConverter.convert(nb_path, nb_content)

    assert "# Test" in content
    assert metadata["type"] == "notebook"
