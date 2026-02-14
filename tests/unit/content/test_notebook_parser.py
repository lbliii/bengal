"""Unit tests for notebook parsing in ContentParser."""

from __future__ import annotations

from pathlib import Path

from bengal.content.discovery.content_parser import ContentParser


def test_parse_file_ipynb_branches_to_converter(tmp_path: Path) -> None:
    """ContentParser branches to notebook converter for .ipynb files."""
    nb_content = """{
  "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Test"]}],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
"""
    nb_path = tmp_path / "demo.ipynb"
    nb_path.write_text(nb_content, encoding="utf-8")

    parser = ContentParser(tmp_path)
    content, metadata = parser.parse_file(nb_path)

    assert "# Test" in content
    assert metadata.get("type") == "notebook"
    assert "notebook" in metadata
