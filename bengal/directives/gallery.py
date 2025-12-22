"""
Gallery directive for responsive image galleries.

Provides a responsive grid layout for displaying images with optional
lightbox support for image previews.

Usage:
    :::{gallery}
    :columns: 3
    :lightbox: true
    :gap: 1rem

    ![Alt text 1](/images/photo1.jpg)
    ![Alt text 2](/images/photo2.jpg)
    ![Alt text 3](/images/photo3.jpg)
    :::

Architecture:
    Uses typed GalleryOptions and parses markdown image syntax
    to extract images from content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.utils.logger import get_logger

__all__ = ["GalleryDirective", "GalleryOptions", "GalleryImage"]

logger = get_logger(__name__)

# Markdown image pattern: ![alt](src) or ![alt](src "title")
IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')


@dataclass
class GalleryImage:
    """Parsed image from markdown syntax.

    Attributes:
        src: Image source URL
        alt: Alternative text for accessibility
        title: Optional image title
    """

    src: str
    alt: str
    title: str = ""


@dataclass
class GalleryOptions(DirectiveOptions):
    """
    Options for gallery directive.

    Attributes:
        columns: Number of columns in the grid (default: 3)
        lightbox: Enable lightbox for image previews (default: True)
        gap: Gap between images using CSS units (default: "1rem")
        css_class: Additional CSS classes for the container
        aspect_ratio: Aspect ratio for images (default: "4/3")

    Example:
        :::{gallery}
        :columns: 4
        :lightbox: true
        :gap: 0.5rem
        :aspect-ratio: 16/9
        :class: my-custom-gallery

        ![Photo 1](/images/photo1.jpg)
        ![Photo 2](/images/photo2.jpg)
        :::
    """

    columns: int = 3
    lightbox: bool = True
    gap: str = "1rem"
    css_class: str = ""
    aspect_ratio: str = "4/3"

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "aspect-ratio": "aspect_ratio",
    }


class GalleryDirective(BengalDirective):
    """
    Responsive image gallery directive.

    Parses markdown images from content and renders them as a responsive
    CSS grid with optional lightbox support.

    Syntax:
        :::{gallery}
        :columns: 3
        :lightbox: true
        :gap: 1rem
        :aspect-ratio: 4/3
        :class: custom-class

        ![Image 1](/images/photo1.jpg)
        ![Image 2](/images/photo2.jpg "Caption for photo 2")
        ![Image 3](/images/photo3.jpg)
        :::

    Options:
        :columns: int - Number of columns (default: 3)
        :lightbox: bool - Enable lightbox previews (default: true)
        :gap: string - CSS gap value (default: "1rem")
        :aspect-ratio: string - Image aspect ratio (default: "4/3")
        :class: string - Additional CSS classes
    """

    # Directive names to register
    NAMES: ClassVar[list[str]] = ["gallery"]

    # Token type for AST
    TOKEN_TYPE: ClassVar[str] = "gallery"

    # Typed options class
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = GalleryOptions

    # For backward compatibility with health check introspection
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["gallery"]

    def parse_directive(
        self,
        title: str,
        options: GalleryOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """
        Build gallery token from parsed components.

        Args:
            title: Gallery title (usually empty for gallery)
            options: Typed gallery options
            content: Raw content string containing markdown images
            children: Parsed nested content tokens (unused)
            state: Parser state

        Returns:
            DirectiveToken for the gallery
        """
        # Parse images from raw content
        images = self._parse_images(content)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title,
                "columns": options.columns,
                "lightbox": options.lightbox,
                "gap": options.gap,
                "aspect_ratio": options.aspect_ratio,
                "css_class": options.css_class,
                "images": [{"src": img.src, "alt": img.alt, "title": img.title} for img in images],
            },
            children=[],  # Gallery doesn't use child tokens
        )

    def _parse_images(self, content: str) -> list[GalleryImage]:
        """
        Extract images from markdown content.

        Parses markdown image syntax: ![alt](src) or ![alt](src "title")

        Args:
            content: Raw markdown content

        Returns:
            List of GalleryImage instances
        """
        images = []
        for match in IMAGE_PATTERN.finditer(content):
            alt = match.group(1) or ""
            src = match.group(2)
            title = match.group(3) or ""
            images.append(GalleryImage(src=src, alt=alt, title=title))
        return images

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render gallery to HTML.

        Renders as a responsive CSS grid with figure/img elements.
        Uses CSS custom properties for layout control.

        Args:
            renderer: Mistune renderer instance
            text: Pre-rendered children HTML (unused for gallery)
            **attrs: Token attributes

        Returns:
            HTML string
        """
        columns = attrs.get("columns", 3)
        lightbox = attrs.get("lightbox", True)
        gap = attrs.get("gap", "1rem")
        aspect_ratio = attrs.get("aspect_ratio", "4/3")
        css_class = attrs.get("css_class", "")
        images = attrs.get("images", [])

        if not images:
            return "<!-- gallery: no images found -->\n"

        # Build class string
        class_str = self.build_class_string("gallery", css_class)

        # Build style with CSS custom properties
        style_parts = [
            f"--gallery-columns: {columns}",
            f"--gallery-gap: {gap}",
            f"--gallery-aspect-ratio: {aspect_ratio}",
        ]
        style_str = "; ".join(style_parts)

        # Lightbox attribute
        lightbox_attr = f' data-lightbox="{str(lightbox).lower()}"'

        # Build HTML
        html_parts = [f'<div class="{class_str}" style="{style_str}"{lightbox_attr}>\n']

        for _i, img in enumerate(images):
            src = self.escape_html(img.get("src", ""))
            alt = self.escape_html(img.get("alt", ""))
            title = img.get("title", "")
            caption = title or alt

            # Use figure for semantic markup
            html_parts.append('  <figure class="gallery__item">\n')

            if lightbox:
                # Wrap in link for lightbox
                html_parts.append(
                    f'    <a href="{src}" class="gallery__link" '
                    f'data-gallery="gallery-{id(self)}">\n'
                )

            html_parts.append(
                f'      <img src="{src}" alt="{alt}" loading="lazy" class="gallery__image">\n'
            )

            if lightbox:
                html_parts.append("    </a>\n")

            # Add caption if available
            if caption:
                html_parts.append(
                    f'    <figcaption class="gallery__caption">'
                    f"{self.escape_html(caption)}</figcaption>\n"
                )

            html_parts.append("  </figure>\n")

        html_parts.append("</div>\n")

        return "".join(html_parts)
