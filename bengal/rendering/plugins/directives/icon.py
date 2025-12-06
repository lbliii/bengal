"""
Icon directive for Mistune.

Provides inline SVG icons from Bengal's icon library: ```{icon} name```

Syntax:
    ```{icon} terminal
    :size: 24
    :class: my-icon-class
    ```

Supports looking up icons from the theme's `assets/icons/` directory
and inlining them as SVG for full CSS styling support with `currentColor`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from typing import Any

logger = get_logger(__name__)

__all__ = ["IconDirective", "render_icon"]

# Icon registry - maps icon names to SVG content
# Populated lazily when icons are first requested
_icon_cache: dict[str, str] = {}
_icons_dir: Path | None = None


def _set_icons_directory(path: Path) -> None:
    """Set the icons directory (called during site initialization)."""
    global _icons_dir
    _icons_dir = path
    _icon_cache.clear()


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

    # Try to find icons directory
    icons_dir = _icons_dir
    if icons_dir is None:
        # Fallback to default theme location
        icons_dir = Path(__file__).parents[3] / "themes" / "default" / "assets" / "icons"

    if not icons_dir.exists():
        logger.debug("icons_dir_not_found", path=str(icons_dir))
        return None

    icon_path = icons_dir / f"{name}.svg"
    if not icon_path.exists():
        logger.warning("icon_not_found", name=name, searched=str(icons_dir))
        return None

    try:
        svg_content = icon_path.read_text(encoding="utf-8")
        _icon_cache[name] = svg_content
        return svg_content
    except OSError as e:
        logger.error("icon_load_error", name=name, error=str(e))
        return None


def get_available_icons() -> list[str]:
    """
    Get list of available icon names.

    Returns:
        List of icon names (without .svg extension)
    """
    icons_dir = _icons_dir
    if icons_dir is None:
        icons_dir = Path(__file__).parents[3] / "themes" / "default" / "assets" / "icons"

    if not icons_dir.exists():
        return []

    return [p.stem for p in icons_dir.glob("*.svg")]


class IconDirective(DirectivePlugin):
    """
    Icon directive for inline SVG icons.

    Syntax:
        ```{icon} terminal
        ```

        ```{icon} docs
        :size: 16
        :class: text-muted
        ```

    Options:
        :size: Icon size in pixels (default: 24)
        :class: Additional CSS classes
        :aria-label: Accessibility label (default: icon name)

    The icon is inlined as an SVG element with:
        - width/height set to specified size
        - class="bengal-icon icon-{name} {extra-classes}"
        - aria-hidden="true" (unless aria-label provided)
        - fill="currentColor" on applicable elements

    Available icons are loaded from the theme's `assets/icons/` directory.
    """

    DIRECTIVE_NAMES = ["icon", "svg-icon"]

    def parse(self, block: Any, m: Any, state: Any) -> dict[str, Any]:
        """
        Parse icon directive.

        Args:
            block: Block parser
            m: Regex match object
            state: Parser state

        Returns:
            Dict with icon data for rendering
        """
        # Extract icon name (title)
        name = self.parse_title(m)
        if not name:
            logger.warning("icon_directive_empty", info="Icon directive requires a name")
            return {"type": "icon", "attrs": {"name": "", "error": True}, "children": []}

        # Clean the name
        name = name.strip().lower().replace(" ", "-")

        # Parse options
        options = dict(self.parse_options(m))

        size = options.get("size", "24")
        try:
            size = int(size)
        except ValueError:
            size = 24

        css_class = options.get("class", "")
        aria_label = options.get("aria-label", "")

        return {
            "type": "icon",
            "attrs": {
                "name": name,
                "size": size,
                "class": css_class,
                "aria_label": aria_label,
            },
            "children": [],
        }

    def __call__(self, directive: Any, md: Any) -> None:
        """
        Register icon directive with Mistune.

        Args:
            directive: FencedDirective instance
            md: Markdown instance
        """
        directive.register("icon", self.parse)
        directive.register("svg-icon", self.parse)  # Alias

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("icon", render_icon)


def render_icon(renderer: Any, text: str, **attrs: Any) -> str:
    """
    Render icon directive to inline SVG.

    Args:
        renderer: Mistune renderer
        text: Rendered children content (unused for icons)
        **attrs: Directive attributes (name, size, class, aria_label)

    Returns:
        Inline SVG HTML or empty span with error class
    """
    name = attrs.get("name", "")
    if not name or attrs.get("error"):
        return '<span class="bengal-icon bengal-icon-error" aria-hidden="true">⚠️</span>'

    size = attrs.get("size", 24)
    css_class = attrs.get("class", "")
    aria_label = attrs.get("aria_label", "")

    # Load the SVG content
    svg_content = _load_icon(name)
    if svg_content is None:
        return f'<span class="bengal-icon bengal-icon-missing" aria-hidden="true" title="Icon not found: {name}">❓</span>'

    # Build class list
    classes = ["bengal-icon", f"icon-{name}"]
    if css_class:
        classes.extend(css_class.split())
    class_attr = " ".join(classes)

    # Accessibility attributes
    if aria_label:
        aria_attrs = f'aria-label="{_escape_attr(aria_label)}" role="img"'
    else:
        aria_attrs = 'aria-hidden="true"'

    # Modify SVG to set size and add attributes
    # Replace width/height in opening <svg> tag
    import re

    # Remove existing width/height/class attributes
    svg_modified = re.sub(r'\s+(width|height)="[^"]*"', "", svg_content)
    svg_modified = re.sub(r'\s+class="[^"]*"', "", svg_modified)

    # Add our attributes to <svg> tag
    svg_modified = re.sub(
        r"<svg\s",
        f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
        svg_modified,
        count=1,
    )

    return svg_modified


def _escape_attr(value: str) -> str:
    """Escape HTML attribute value."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

