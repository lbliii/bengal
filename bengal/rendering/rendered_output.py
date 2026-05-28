"""Helpers for reading rendered page HTML after the write phase."""

from __future__ import annotations

from typing import Any


def get_rendered_html(page: Any) -> str:
    """Return rendered HTML from a page-like object or its written output."""
    rendered = getattr(page, "rendered_html", None)
    if isinstance(rendered, str) and rendered:
        return rendered

    output_path = getattr(page, "output_path", None)
    if (
        output_path is None
        or not hasattr(output_path, "is_file")
        or output_path.is_file() is not True
    ):
        return rendered if isinstance(rendered, str) else ""

    try:
        written = output_path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""
    return written if isinstance(written, str) else ""
