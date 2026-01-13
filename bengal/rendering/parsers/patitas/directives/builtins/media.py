"""Media directives for semantic embeds.

Provides:
- figure: Semantic image with caption
- audio: Self-hosted audio files
- gallery: Responsive image gallery

Use cases:
- Documentation images with captions
- Audio podcasts/recordings
- Image galleries/screenshots

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's media directives exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
from bengal.rendering.parsers.patitas.nodes import Directive

if TYPE_CHECKING:
    from bengal.rendering.parsers.patitas.location import SourceLocation
    from bengal.rendering.parsers.patitas.nodes import Block
    from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder

__all__ = ["FigureDirective", "AudioDirective", "GalleryDirective"]


# =============================================================================
# Figure Directive
# =============================================================================


# Image path pattern: relative or absolute paths, or URLs
IMAGE_PATH_PATTERN = re.compile(
    r"^(?:https?://[\w\-./]+|(?:/|\./)(?:(?!\.\./)[a-zA-Z0-9_\-/])+)\.(?:png|jpg|jpeg|gif|webp|svg|avif)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class FigureOptions(DirectiveOptions):
    """Options for figure directive."""

    alt: str = ""
    caption: str = ""
    width: str = ""
    height: str = ""
    align: str = ""
    link: str = ""
    target: str = "_self"
    loading: str = "lazy"
    css_class: str = ""


class FigureDirective:
    """
    Semantic figure directive for images with captions.
    
    Syntax:
        :::{figure} /images/architecture.png
        :alt: System Architecture Diagram
        :caption: High-level system architecture
        :width: 80%
        :align: center
        :::
    
    Output:
        <figure class="figure align-center" style="width: 80%">
          <img src="..." alt="..." loading="lazy">
          <figcaption>Caption text</figcaption>
        </figure>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("figure",)
    token_type: ClassVar[str] = "figure"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[FigureOptions]] = FigureOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: FigureOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build figure AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,  # Image path is in title
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[FigureOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render figure to HTML."""
        opts = node.options  # Direct typed access!

        image_path = node.title.strip() if node.title else ""

        # Validate image path
        if not IMAGE_PATH_PATTERN.match(image_path):
            sb.append(
                f'<div class="figure figure-error">\n'
                f'  <p class="error">Figure Error: Invalid image path: {html_escape(repr(image_path))}</p>\n'
                f"  <p>Path: <code>{html_escape(image_path)}</code></p>\n"
                f"</div>\n"
            )
            return

        alt = opts.alt
        caption = opts.caption
        width = opts.width
        height = opts.height
        align = opts.align
        link = opts.link
        target = opts.target
        loading = opts.loading
        css_class = opts.css_class

        # Build class string
        classes = ["figure"]
        if align:
            classes.append(f"align-{align}")
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        # Build style string
        style_str = f' style="width: {width}"' if width else ""

        # Build img tag
        img_attrs = [f'src="{html_escape(image_path)}"']
        img_attrs.append(f'alt="{html_escape(alt)}"')
        img_attrs.append(f'loading="{loading}"')
        if height:
            img_attrs.append(f'style="height: {height}"')

        img_tag = f"<img {' '.join(img_attrs)}>"

        # Wrap in link if specified
        if link:
            safe_link = html_escape(link)
            target_attr = f' target="{target}"' if target == "_blank" else ""
            rel_attr = ' rel="noopener noreferrer"' if target == "_blank" else ""
            img_tag = f'<a href="{safe_link}"{target_attr}{rel_attr}>{img_tag}</a>'

        sb.append(f'<figure class="{class_str}"{style_str}>\n')
        sb.append(f"  {img_tag}\n")
        if caption:
            sb.append(f"  <figcaption>{html_escape(caption)}</figcaption>\n")
        sb.append("</figure>\n")


# =============================================================================
# Audio Directive
# =============================================================================

# Audio path pattern
AUDIO_PATH_PATTERN = re.compile(
    r"^(?:https?://|/|\./)[\w\-./]+\.(?:mp3|ogg|wav|flac|m4a|aac)$", re.IGNORECASE
)

# MIME types by extension
AUDIO_MIME_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


@dataclass(frozen=True, slots=True)
class AudioOptions(DirectiveOptions):
    """Options for audio directive."""

    title: str = ""
    controls: bool = True
    autoplay: bool = False
    loop: bool = False
    muted: bool = False
    preload: str = "metadata"
    css_class: str = ""


class AudioDirective:
    """
    Self-hosted audio directive using HTML5 audio element.
    
    Syntax:
        :::{audio} /assets/podcast-ep1.mp3
        :title: Episode 1: Getting Started
        :controls: true
        :::
    
    Output:
        <figure class="audio-embed">
          <audio title="..." controls preload="metadata">
            <source src="..." type="audio/mpeg">
            <p>Fallback text</p>
          </audio>
        </figure>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("audio",)
    token_type: ClassVar[str] = "audio_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[AudioOptions]] = AudioOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: AudioOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build audio AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,  # Audio path is in title
            options=options,  # Pass typed options directly
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[AudioOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render audio embed to HTML."""
        opts = node.options  # Direct typed access!

        audio_path = node.title.strip() if node.title else ""

        # Validate audio path
        if not AUDIO_PATH_PATTERN.match(audio_path):
            sb.append(
                f'<div class="audio-embed audio-error">\n'
                f'  <p class="error">Audio Error: Invalid audio path: {html_escape(repr(audio_path))}</p>\n'
                f"  <p>Path: <code>{html_escape(audio_path)}</code></p>\n"
                f"</div>\n"
            )
            return

        title = opts.title
        if not title:
            sb.append(
                f'<div class="audio-embed audio-error">\n'
                f'  <p class="error">Audio Error: Missing required :title: option</p>\n'
                f"  <p>Path: <code>{html_escape(audio_path)}</code></p>\n"
                f"</div>\n"
            )
            return

        controls = opts.controls
        autoplay = opts.autoplay
        loop = opts.loop
        muted = opts.muted
        preload = opts.preload
        css_class = opts.css_class

        # Determine MIME type
        mime_type = "audio/mpeg"
        for ext, mime in AUDIO_MIME_TYPES.items():
            if audio_path.lower().endswith(ext):
                mime_type = mime
                break

        # Build class string
        classes = ["audio-embed"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        # Build audio attributes
        audio_attrs = [f'title="{html_escape(title)}"']
        if controls:
            audio_attrs.append("controls")
        if autoplay:
            audio_attrs.append("autoplay")
        if loop:
            audio_attrs.append("loop")
        if muted:
            audio_attrs.append("muted")
        audio_attrs.append(f'preload="{preload}"')

        attrs_str = " ".join(audio_attrs)

        sb.append(f'<figure class="{class_str}">\n')
        sb.append(f"  <audio {attrs_str}>\n")
        sb.append(f'    <source src="{html_escape(audio_path)}" type="{mime_type}">\n')
        sb.append(
            f"    <p>Your browser doesn't support HTML5 audio. "
            f'<a href="{html_escape(audio_path)}">Download the audio</a>.</p>\n'
        )
        sb.append("  </audio>\n")
        sb.append("</figure>\n")


# =============================================================================
# Gallery Directive
# =============================================================================

# Markdown image pattern: ![alt](src) or ![alt](src "title")
GALLERY_IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)')


@dataclass(frozen=True, slots=True)
class GalleryOptions(DirectiveOptions):
    """Options for gallery directive."""

    columns: int = 3
    lightbox: bool = True
    gap: str = "1rem"
    aspect_ratio: str = "4/3"
    css_class: str = ""


class GalleryDirective:
    """
    Responsive image gallery directive.
    
    Syntax:
        :::{gallery}
        :columns: 3
        :lightbox: true
        :gap: 1rem
        :aspect-ratio: 4/3
    
        ![Image 1](/images/photo1.jpg)
        ![Image 2](/images/photo2.jpg "Caption")
        :::
    
    Output:
        <div class="gallery" style="--gallery-columns: 3; ...">
          <figure class="gallery__item">
            <a href="..." class="gallery__link">
              <img src="..." alt="..." loading="lazy">
            </a>
            <figcaption>Caption</figcaption>
          </figure>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("gallery",)
    token_type: ClassVar[str] = "gallery"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[GalleryOptions]] = GalleryOptions
    preserves_raw_content: ClassVar[bool] = True  # Needs raw content for image parsing

    def parse(
        self,
        name: str,
        title: str | None,
        options: GalleryOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build gallery AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=tuple(children),
            raw_content=content,  # Preserve raw content for image parsing
        )

    def render(
        self,
        node: Directive[GalleryOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render gallery to HTML."""
        opts = node.options  # Direct typed access!

        columns = opts.columns
        lightbox = opts.lightbox
        gap = opts.gap
        aspect_ratio = opts.aspect_ratio
        css_class = opts.css_class

        # Parse images from raw content
        images = self._parse_images(node.raw_content or "")

        if not images:
            sb.append("<!-- gallery: no images found -->\n")
            return

        # Build class string
        classes = ["gallery"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        # Build style with CSS custom properties
        style_parts = [
            f"--gallery-columns: {columns}",
            f"--gallery-gap: {gap}",
            f"--gallery-aspect-ratio: {aspect_ratio}",
        ]
        style_str = "; ".join(style_parts)

        # Lightbox attribute
        lightbox_attr = f' data-lightbox="{str(lightbox).lower()}"'

        # Generate unique gallery ID
        gallery_id = id(node)

        sb.append(f'<div class="{class_str}" style="{style_str}"{lightbox_attr}>\n')

        for img in images:
            src = html_escape(img["src"])
            alt = html_escape(img["alt"])
            caption = img["title"] or img["alt"]

            sb.append('  <figure class="gallery__item">\n')

            if lightbox:
                sb.append(
                    f'    <a href="{src}" class="gallery__link" data-gallery="gallery-{gallery_id}">\n'
                )

            sb.append(
                f'      <img src="{src}" alt="{alt}" loading="lazy" class="gallery__image">\n'
            )

            if lightbox:
                sb.append("    </a>\n")

            if caption:
                sb.append(
                    f'    <figcaption class="gallery__caption">{html_escape(caption)}</figcaption>\n'
                )

            sb.append("  </figure>\n")

        sb.append("</div>\n")

    def _parse_images(self, content: str) -> list[dict[str, str]]:
        """Extract images from markdown content."""
        images = []
        for match in GALLERY_IMAGE_PATTERN.finditer(content):
            alt = match.group(1) or ""
            src = match.group(2)
            title = match.group(3) or ""
            images.append({"src": src, "alt": alt, "title": title})
        return images
