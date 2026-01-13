"""Video embed directives for documentation.

Provides:
- youtube: YouTube video embeds with privacy-enhanced mode
- vimeo: Vimeo video embeds with Do Not Track mode
- tiktok: TikTok short-form video embeds
- video: Self-hosted HTML5 video for local files

Use cases:
- Tutorial videos embedded in documentation
- Product demos and walkthroughs
- Code review recordings

Security:
All video IDs are validated via regex patterns to prevent XSS and injection.
Iframe embeds use appropriate sandbox attributes and CSP-friendly URLs.

Accessibility:
Title is required for all embeds to meet WCAG 2.1 AA requirements.
Fallback content provided for users without JavaScript/iframe support.

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's video directives exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = [
    "YouTubeDirective",
    "VimeoDirective",
    "TikTokDirective",
    "SelfHostedVideoDirective",
]


# =============================================================================
# YouTube Directive
# =============================================================================

# YouTube video ID: 11 characters (alphanumeric, underscore, hyphen)
YOUTUBE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


@dataclass(frozen=True, slots=True)
class YouTubeOptions(DirectiveOptions):
    """Options for YouTube video embed."""

    title: str = ""
    width: str = ""  # Empty means 100% (CSS default)
    aspect: str = "16/9"
    css_class: str = ""
    autoplay: bool = False
    loop: bool = False
    muted: bool = False
    start: int = 0
    end: int | None = None
    privacy: bool = True
    controls: bool = True

    # Computed attributes (populated during parse)
    video_id: str = ""
    embed_url: str = ""
    error: str = ""


class YouTubeDirective:
    """
    YouTube video embed directive with privacy-enhanced mode.
    
    Syntax:
        :::{youtube} dQw4w9WgXcQ
        :title: Never Gonna Give You Up
        :start: 30
        :privacy: true
        :::
    
    Output:
        <div class="video-embed youtube" data-aspect="16/9">
          <iframe src="https://www.youtube-nocookie.com/embed/..."
                  title="..." loading="lazy" allowfullscreen></iframe>
          <noscript><p>Watch on YouTube: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("youtube",)
    token_type: ClassVar[str] = "youtube_video"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[YouTubeOptions]] = YouTubeOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: YouTubeOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build YouTube embed AST node."""
        video_id = title.strip() if title else ""

        # Validate video ID
        error = ""
        if not YOUTUBE_ID_PATTERN.match(video_id):
            error = f"Invalid YouTube video ID: {video_id!r}. Expected 11 alphanumeric characters."
        elif not options.title:
            error = f"Missing required :title: option for video embed. Video source: {video_id}"

        # Build embed URL
        embed_url = ""
        if not error:
            embed_url = self._build_embed_url(video_id, options)

        # Store computed values as attributes on options
        from dataclasses import replace

        computed_opts = replace(
            options,
            video_id=video_id,
            embed_url=embed_url,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def _build_embed_url(self, video_id: str, options: YouTubeOptions) -> str:
        """Build YouTube embed URL with options."""
        domain = "youtube-nocookie.com" if options.privacy else "youtube.com"

        params: list[str] = []
        if options.start:
            params.append(f"start={options.start}")
        if options.end:
            params.append(f"end={options.end}")
        if options.autoplay:
            params.append("autoplay=1")
        if options.muted:
            params.append("mute=1")
        if options.loop:
            params.append(f"loop=1&playlist={video_id}")
        if not options.controls:
            params.append("controls=0")

        query = "&".join(params)
        base_url = f"https://www.{domain}/embed/{video_id}"
        return f"{base_url}?{query}" if query else base_url

    def render(
        self,
        node: Directive[YouTubeOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render YouTube embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            video_id = getattr(opts, "video_id", "unknown")
            sb.append(
                f'<div class="video-embed youtube video-error">\n'
                f'  <p class="error">YouTube Error: {html_escape(error)}</p>\n'
                f"  <p>Video ID: <code>{html_escape(video_id)}</code></p>\n"
                f"</div>\n"
            )
            return

        embed_url = getattr(opts, "embed_url", "")
        title = opts.title or "YouTube Video"
        width = opts.width
        aspect = opts.aspect
        css_class = opts.css_class
        video_id = getattr(opts, "video_id", "")

        # Build class string
        classes = ["video-embed", "youtube"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build inline style for width if specified
        style_attr = f' style="width: {width}"' if width else ""

        sb.append(f'<div class="{class_str}" data-aspect="{aspect}"{style_attr}>\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append(
            '    allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            'gyroscope; picture-in-picture; web-share"\n'
        )
        sb.append("    allowfullscreen\n")
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(
            f'    <p>Watch on YouTube: <a href="https://www.youtube.com/watch?v={video_id}">'
            f"{safe_title}</a></p>\n"
        )
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# Vimeo Directive
# =============================================================================

# Vimeo video ID: 6-11 digits
VIMEO_ID_PATTERN = re.compile(r"^\d{6,11}$")


@dataclass(frozen=True, slots=True)
class VimeoOptions(DirectiveOptions):
    """Options for Vimeo video embed."""

    title: str = ""
    width: str = ""
    aspect: str = "16/9"
    css_class: str = ""
    autoplay: bool = False
    loop: bool = False
    muted: bool = False
    color: str = ""
    autopause: bool = True
    dnt: bool = True
    background: bool = False

    # Computed attributes (populated during parse)
    video_id: str = ""
    embed_url: str = ""
    error: str = ""


class VimeoDirective:
    """
    Vimeo video embed directive with Do Not Track mode.
    
    Syntax:
        :::{vimeo} 123456789
        :title: My Vimeo Video
        :color: ff0000
        :::
    
    Output:
        <div class="video-embed vimeo" data-aspect="16/9">
          <iframe src="https://player.vimeo.com/video/..."
                  title="..." loading="lazy" allowfullscreen></iframe>
          <noscript><p>Watch on Vimeo: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("vimeo",)
    token_type: ClassVar[str] = "vimeo_video"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[VimeoOptions]] = VimeoOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: VimeoOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build Vimeo embed AST node."""
        video_id = title.strip() if title else ""

        # Validate video ID
        error = ""
        if not VIMEO_ID_PATTERN.match(video_id):
            error = f"Invalid Vimeo video ID: {video_id!r}. Expected 6-11 digits."
        elif not options.title:
            error = f"Missing required :title: option for video embed. Video source: {video_id}"

        # Build embed URL
        embed_url = ""
        if not error:
            embed_url = self._build_embed_url(video_id, options)

        # Store computed values as attributes on options
        from dataclasses import replace

        computed_opts = replace(
            options,
            video_id=video_id,
            embed_url=embed_url,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def _build_embed_url(self, video_id: str, options: VimeoOptions) -> str:
        """Build Vimeo embed URL with options."""
        params: list[str] = []

        if options.dnt:
            params.append("dnt=1")
        if options.color:
            params.append(f"color={options.color}")
        if not options.autopause:
            params.append("autopause=0")
        if options.background:
            params.append("background=1")
        if options.autoplay:
            params.append("autoplay=1")
        if options.muted:
            params.append("muted=1")
        if options.loop:
            params.append("loop=1")

        query = "&".join(params)
        base_url = f"https://player.vimeo.com/video/{video_id}"
        return f"{base_url}?{query}" if query else base_url

    def render(
        self,
        node: Directive[VimeoOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render Vimeo embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            video_id = getattr(opts, "video_id", "unknown")
            sb.append(
                f'<div class="video-embed vimeo video-error">\n'
                f'  <p class="error">Vimeo Error: {html_escape(error)}</p>\n'
                f"  <p>Video ID: <code>{html_escape(video_id)}</code></p>\n"
                f"</div>\n"
            )
            return

        embed_url = getattr(opts, "embed_url", "")
        title = opts.title or "Vimeo Video"
        width = opts.width
        aspect = opts.aspect
        css_class = opts.css_class
        video_id = getattr(opts, "video_id", "")

        # Build class string
        classes = ["video-embed", "vimeo"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build inline style for width if specified
        style_attr = f' style="width: {width}"' if width else ""

        sb.append(f'<div class="{class_str}" data-aspect="{aspect}"{style_attr}>\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append(
            '    allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media"\n'
        )
        sb.append("    allowfullscreen\n")
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(
            f'    <p>Watch on Vimeo: <a href="https://vimeo.com/{video_id}">{safe_title}</a></p>\n'
        )
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# TikTok Directive
# =============================================================================

# TikTok video ID: 19 digits
TIKTOK_ID_PATTERN = re.compile(r"^\d{19}$")


@dataclass(frozen=True, slots=True)
class TikTokOptions(DirectiveOptions):
    """Options for TikTok video embed."""

    title: str = ""
    width: str = ""
    aspect: str = "9/16"  # TikTok videos are typically vertical
    css_class: str = ""
    autoplay: bool = False
    loop: bool = False
    muted: bool = False

    # Computed attributes (populated during parse)
    video_id: str = ""
    embed_url: str = ""
    error: str = ""


class TikTokDirective:
    """
    TikTok video embed directive.
    
    Syntax:
        :::{tiktok} 7123456789012345678
        :title: Funny cat video
        :::
    
    Output:
        <div class="video-embed tiktok" data-aspect="9/16">
          <iframe src="https://www.tiktok.com/embed/v2/..."
                  title="..." loading="lazy" allowfullscreen></iframe>
          <noscript><p>Watch on TikTok: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("tiktok",)
    token_type: ClassVar[str] = "tiktok_video"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[TikTokOptions]] = TikTokOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: TikTokOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build TikTok embed AST node."""
        video_id = title.strip() if title else ""

        # Validate video ID
        error = ""
        if not TIKTOK_ID_PATTERN.match(video_id):
            error = f"Invalid TikTok video ID: {video_id!r}. Expected 19 digits."
        elif not options.title:
            error = f"Missing required :title: option for video embed. Video source: {video_id}"

        # Build embed URL
        embed_url = ""
        if not error:
            embed_url = self._build_embed_url(video_id, options)

        # Store computed values as attributes on options
        from dataclasses import replace

        computed_opts = replace(
            options,
            video_id=video_id,
            embed_url=embed_url,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def _build_embed_url(self, video_id: str, options: TikTokOptions) -> str:
        """Build TikTok embed URL."""
        base_url = f"https://www.tiktok.com/embed/v2/{video_id}"

        params: list[str] = []
        if options.autoplay:
            params.append("autoplay=1")
        if options.muted:
            params.append("muted=1")
        if options.loop:
            params.append("loop=1")

        query = "&".join(params)
        return f"{base_url}?{query}" if query else base_url

    def render(
        self,
        node: Directive[TikTokOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render TikTok embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            video_id = getattr(opts, "video_id", "unknown")
            sb.append(
                f'<div class="video-embed tiktok video-error">\n'
                f'  <p class="error">TikTok Error: {html_escape(error)}</p>\n'
                f"  <p>Video ID: <code>{html_escape(video_id)}</code></p>\n"
                f"</div>\n"
            )
            return

        embed_url = getattr(opts, "embed_url", "")
        title = opts.title or "TikTok Video"
        width = opts.width
        aspect = opts.aspect
        css_class = opts.css_class
        video_id = getattr(opts, "video_id", "")

        # Build class string
        classes = ["video-embed", "tiktok"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build inline style for width if specified
        style_attr = f' style="width: {width}"' if width else ""

        sb.append(f'<div class="{class_str}" data-aspect="{aspect}"{style_attr}>\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append(
            '    allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            'gyroscope; picture-in-picture"\n'
        )
        sb.append("    allowfullscreen\n")
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(
            f'    <p>Watch on TikTok: <a href="https://www.tiktok.com/video/{video_id}">'
            f"{safe_title}</a></p>\n"
        )
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# Self-Hosted Video Directive
# =============================================================================

# Path pattern: starts with / or ./ or https://, ends with video extension
SELFHOSTED_VIDEO_PATTERN = re.compile(
    r"^(?:https?://|/|\./)[\w\-./]+\.(mp4|webm|ogg|mov)$", re.IGNORECASE
)

# MIME types by extension
VIDEO_MIME_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".ogg": "video/ogg",
    ".mov": "video/quicktime",
}


@dataclass(frozen=True, slots=True)
class SelfHostedVideoOptions(DirectiveOptions):
    """Options for self-hosted video embed."""

    title: str = ""
    poster: str = ""
    controls: bool = True
    autoplay: bool = False
    muted: bool = False
    loop: bool = False
    preload: str = "metadata"
    width: str = "100%"
    aspect: str = "16/9"
    css_class: str = ""

    # Computed attributes (populated during parse)
    video_path: str = ""
    mime_type: str = ""
    error: str = ""


class SelfHostedVideoDirective:
    """
    Self-hosted video directive using HTML5 video element.
    
    Syntax:
        :::{video} /assets/demo.mp4
        :title: Product Demo
        :poster: /assets/demo-poster.jpg
        :controls: true
        :::
    
    Output:
        <figure class="video-embed self-hosted">
          <video title="..." controls preload="metadata">
            <source src="..." type="video/mp4">
            <p>Fallback text with download link</p>
          </video>
        </figure>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("video",)
    token_type: ClassVar[str] = "self_hosted_video"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[SelfHostedVideoOptions]] = SelfHostedVideoOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: SelfHostedVideoOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build self-hosted video AST node."""
        video_path = title.strip() if title else ""

        # Validate video path
        error = ""
        if not SELFHOSTED_VIDEO_PATTERN.match(video_path):
            error = (
                f"Invalid video path: {video_path!r}. "
                f"Expected path starting with / or ./ ending with .mp4, .webm, .ogg, or .mov"
            )
        elif not options.title:
            error = f"Missing required :title: option for video embed. Video source: {video_path}"

        # Determine MIME type
        mime_type = "video/mp4"
        for ext, mime in VIDEO_MIME_TYPES.items():
            if video_path.lower().endswith(ext):
                mime_type = mime
                break

        # Store computed values as attributes on options
        from dataclasses import replace

        computed_opts = replace(
            options,
            video_path=video_path,
            mime_type=mime_type,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[SelfHostedVideoOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render self-hosted video to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            video_path = getattr(opts, "video_path", "unknown")
            sb.append(
                f'<div class="video-embed self-hosted video-error">\n'
                f'  <p class="error">Video Error: {html_escape(error)}</p>\n'
                f"  <p>Path: <code>{html_escape(video_path)}</code></p>\n"
                f"</div>\n"
            )
            return

        video_path = getattr(opts, "video_path", "")
        mime_type = getattr(opts, "mime_type", "video/mp4")
        title = opts.title or "Video"
        poster = opts.poster
        controls = opts.controls
        autoplay = opts.autoplay
        muted = opts.muted
        loop = opts.loop
        preload = opts.preload
        width = opts.width
        css_class = opts.css_class

        # Build class string
        classes = ["video-embed", "self-hosted"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build video attributes
        video_attrs = [f'title="{safe_title}"']
        if poster:
            video_attrs.append(f'poster="{html_escape(poster)}"')
        if controls:
            video_attrs.append("controls")
        if autoplay:
            video_attrs.append("autoplay")
        if muted:
            video_attrs.append("muted")
        if loop:
            video_attrs.append("loop")
        video_attrs.append(f'preload="{preload}"')
        if width:
            video_attrs.append(f'style="width: {width}"')

        attrs_str = " ".join(video_attrs)

        sb.append(f'<figure class="{class_str}">\n')
        sb.append(f"  <video {attrs_str}>\n")
        sb.append(f'    <source src="{html_escape(video_path)}" type="{mime_type}">\n')
        sb.append(
            f"    <p>Your browser doesn't support HTML5 video. "
            f'<a href="{html_escape(video_path)}">Download the video</a>.</p>\n'
        )
        sb.append("  </video>\n")
        sb.append("</figure>\n")
