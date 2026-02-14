"""
Notebook content support for Bengal.

Converts Jupyter notebooks (.ipynb) to Markdown for rendering.
Requires the optional `bengal[notebooks]` extra (nbformat).
"""

from __future__ import annotations

__all__ = ["NotebookConverter"]

from bengal.content.notebook.converter import NotebookConverter
