"""
Icon directive for Mistune.

Provides inline SVG icons from Bengal's icon library.

Architecture:
    Module-level icon cache preserved for performance.

Syntax:

```markdown
:::{icon} terminal
:size: 24
:class: my-icon-class
:::
```
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["IconDirective", "IconOptions", "get_available_icons"]

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
    """Load an icon SVG by name."""
    if name in _icon_cache:
        return _icon_cache[name]

    icons_dir = _icons_dir
    if icons_dir is None:
        # Path: bengal/directives/icon.py -> bengal/themes/default/assets/icons
        icons_dir = Path(__file__).parents[1] / "themes" / "default" / "assets" / "icons"

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
    """Get list of available icon names."""
    icons_dir = _icons_dir
    if icons_dir is None:
        # Path: bengal/directives/icon.py -> bengal/themes/default/assets/icons
        icons_dir = Path(__file__).parents[1] / "themes" / "default" / "assets" / "icons"

    if not icons_dir.exists():
        return []

    return [p.stem for p in icons_dir.glob("*.svg")]


@dataclass
class IconOptions(DirectiveOptions):
    """
    Options for icon directive.

    Attributes:
        size: Icon size in pixels
        css_class: Additional CSS classes
        aria_label: Accessibility label
    """

    size: int = 24
    css_class: str = ""
    aria_label: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "aria-label": "aria_label",
    }

    def __post_init__(self) -> None:
        """Validate size falls back to default on invalid input."""
        # Handle case where size is passed as invalid string that got coerced to 0
        if self.size <= 0:
            self.size = 24


class IconDirective(BengalDirective):
    """
    Icon directive for inline SVG icons.

    Syntax:
        :::{icon} terminal
        :::

        :::{icon} docs
        :size: 16
        :class: text-muted
        :::

    Options:
        :size: Icon size in pixels (default: 24)
        :class: Additional CSS classes
        :aria-label: Accessibility label (default: icon name)
    """

    NAMES: ClassVar[list[str]] = ["icon", "svg-icon"]
    TOKEN_TYPE: ClassVar[str] = "icon"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = IconOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["icon", "svg-icon"]

    def parse_directive(
        self,
        title: str,
        options: IconOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build icon token."""
        if not title:
            logger.warning("icon_directive_empty", info="Icon directive requires a name")
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"name": "", "error": True},
                children=[],
            )

        # Clean the name
        name = title.strip().lower().replace(" ", "-")

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "name": name,
                "size": options.size,
                "css_class": options.css_class,
                "aria_label": options.aria_label,
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render icon directive to inline SVG."""
        name = attrs.get("name", "")
        if not name or attrs.get("error"):
            return '<span class="bengal-icon bengal-icon--error" aria-hidden="true">⚠️</span>'

        size = attrs.get("size", 24)
        css_class = attrs.get("css_class", "")
        aria_label = attrs.get("aria_label", "")

        # Load the SVG content
        svg_content = _load_icon(name)
        if svg_content is None:
            return (
                f'<span class="bengal-icon bengal-icon--missing" aria-hidden="true" '
                f'title="Icon not found: {name}">❓</span>'
            )

        # Build class list
        classes = ["bengal-icon", f"icon-{name}"]
        if css_class:
            classes.extend(css_class.split())
        class_attr = " ".join(classes)

        # Accessibility attributes
        if aria_label:
            aria_attrs = f'aria-label="{self.escape_html(aria_label)}" role="img"'
        else:
            aria_attrs = 'aria-hidden="true"'

        # Modify SVG to set size and add attributes
        svg_modified = re.sub(r'\s+(width|height)="[^"]*"', "", svg_content)
        svg_modified = re.sub(r'\s+class="[^"]*"', "", svg_modified)

        svg_modified = re.sub(
            r"<svg\s",
            f'<svg width="{size}" height="{size}" class="{class_attr}" {aria_attrs} ',
            svg_modified,
            count=1,
        )

        return svg_modified


# Backward compatibility
