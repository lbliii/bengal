"""
Inline icon plugin for Mistune.

Provides inline icon syntax for use in table cells, paragraphs, etc.

Syntax:
    {icon}`terminal`           -> 24px icon (default)
    {icon}`terminal:16`        -> 16px icon
    {icon}`terminal:32`        -> 32px icon
    {icon}`docs:48:primary`    -> 48px icon with class

This works inside table cells and other inline contexts where
the block-level :::{icon} directive cannot be used.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["InlineIconPlugin"]

# Icon cache shared with directive (import from there if available)
_icon_cache: dict[str, str] = {}
_icons_dir: Path | None = None


def _get_icons_dir() -> Path:
    """Get the icons directory path."""
    global _icons_dir
    if _icons_dir is None:
        _icons_dir = Path(__file__).parents[2] / "themes" / "default" / "assets" / "icons"
    return _icons_dir


def _load_icon(name: str) -> str | None:
    """
    Load an icon SVG by name.

    Args:
        name: Icon name (without .svg extension)

    Returns:
        SVG content string, or None if not found
    """
    if name in _icon_cache:
        return _icon_cache[name]

    icons_dir = _get_icons_dir()
    if not icons_dir.exists():
        return None

    icon_path = icons_dir / f"{name}.svg"
    if not icon_path.exists():
        logger.debug("inline_icon_not_found", name=name)
        return None

    try:
        svg_content = icon_path.read_text(encoding="utf-8")
        _icon_cache[name] = svg_content
        return svg_content
    except OSError:
        return None


class InlineIconPlugin:
    """
    Mistune plugin for inline icon syntax.

    Syntax:
        {icon}`name`              -> 24px icon
        {icon}`name:size`         -> Custom size (e.g., name:16, name:32)
        {icon}`name:size:class`   -> Custom size and CSS class

    Examples:
        | Column | Icon |
        |--------|------|
        | Terminal | {icon}`terminal` |
        | Docs | {icon}`docs:16` |
        | Rosette | {icon}`bengal-rosette:32:icon-primary` |

    Works in table cells, paragraphs, and other inline contexts.
    """

    def __init__(self) -> None:
        """Initialize inline icon plugin."""
        # Pattern matches after Mistune converts `text` to <code>text</code>
        # {icon}<code>terminal</code> or {icon}<code>terminal:32</code>
        self.html_pattern = re.compile(r"\{icon\}<code>([^<]+)</code>")

        # Fallback for raw patterns (shouldn't happen in practice)
        self.raw_pattern = re.compile(r"\{icon\}`([^`]+)`")

        # Pattern to split by <pre> blocks
        self._pre_pattern = re.compile(r"(<pre[^>]*>.*?</pre>)", re.DOTALL)

    def __call__(self, md: Any) -> Any:
        """
        Register the plugin with Mistune.

        Icon substitution happens in parser.py after HTML is generated.
        """
        return md

    def _substitute_icons(self, html: str) -> str:
        """
        Substitute {icon}<code>...</code> patterns with inline SVG.

        Skips patterns inside <pre> code blocks to preserve literal syntax
        in code examples.

        Args:
            html: HTML content that may contain icon patterns

        Returns:
            HTML with icon patterns replaced by SVG
        """
        # Quick rejection
        if "{icon}" not in html:
            return html

        def replace_html_icon(match: re.Match[str]) -> str:
            """Replace HTML icon pattern with SVG."""
            content = match.group(1)
            return self._render_icon(content)

        def replace_raw_icon(match: re.Match[str]) -> str:
            """Replace raw icon pattern (fallback)."""
            content = match.group(1)
            return self._render_icon(content)

        # Split by <pre> blocks to avoid processing code examples
        parts = self._pre_pattern.split(html)

        result_parts = []
        for i, part in enumerate(parts):
            # Odd indices are the <pre>...</pre> blocks (captured groups)
            if i % 2 == 1:
                # Inside <pre> block - preserve as-is
                result_parts.append(part)
            else:
                # Outside <pre> - safe to substitute icons
                processed = self.html_pattern.sub(replace_html_icon, part)
                processed = self.raw_pattern.sub(replace_raw_icon, processed)
                result_parts.append(processed)

        return "".join(result_parts)

    def _render_icon(self, content: str) -> str:
        """
        Render an icon from the content string.

        Args:
            content: Icon specification (e.g., "terminal", "docs:32", "bengal-rosette:48:primary")

        Returns:
            Inline SVG HTML or fallback indicator
        """
        # Parse content: name[:size[:class]]
        parts = content.strip().split(":")
        name = parts[0].strip().lower().replace(" ", "-")

        # Default values
        size = 24
        css_class = ""

        # Parse optional size
        if len(parts) >= 2 and parts[1].strip():
            try:
                size = int(parts[1].strip())
            except ValueError:
                # If not a number, treat as class
                css_class = parts[1].strip()

        # Parse optional class
        if len(parts) >= 3 and parts[2].strip():
            css_class = parts[2].strip()

        # Load the SVG content
        svg_content = _load_icon(name)
        if svg_content is None:
            return f'<span class="bengal-icon bengal-icon--missing" title="Icon not found: {name}">❓</span>'

        # Build class list
        classes = ["bengal-icon", f"icon-{name}"]
        if css_class:
            # Support multiple classes separated by space
            classes.extend(css_class.split())
        class_attr = " ".join(classes)

        # Modify SVG to set size and add attributes
        # Remove existing width/height/class attributes
        svg_modified = re.sub(r'\s+(width|height)="[^"]*"', "", svg_content)
        svg_modified = re.sub(r'\s+class="[^"]*"', "", svg_modified)

        # Add our attributes to <svg> tag
        svg_modified = re.sub(
            r"<svg\s",
            f'<svg width="{size}" height="{size}" class="{class_attr}" aria-hidden="true" ',
            svg_modified,
            count=1,
        )

        return svg_modified
