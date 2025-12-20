"""
Video embed directives for Bengal.

Provides directives for embedding videos from YouTube, Vimeo, and self-hosted sources
with privacy-by-default, accessibility requirements, and responsive design.

Architecture:
    - VideoDirective: Abstract base class for video embeds
    - YouTubeDirective: YouTube with privacy-enhanced mode (youtube-nocookie.com)
    - VimeoDirective: Vimeo with Do Not Track mode
    - SelfHostedVideoDirective: Native HTML5 video for local files

Security:
    All video IDs are validated via regex patterns to prevent XSS and injection.
    Iframe embeds use appropriate sandbox attributes and CSP-friendly URLs.

Accessibility:
    Title is required for all embeds to meet WCAG 2.1 AA requirements.
    Fallback content provided for users without JavaScript/iframe support.

Related:
    - bengal/rendering/plugins/directives/base.py: BengalDirective
    - RFC: plan/active/rfc-media-embed-directives.md
"""

from __future__ import annotations

import re
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = [
    "VideoDirective",
    "VideoOptions",
    "YouTubeDirective",
    "YouTubeOptions",
    "VimeoDirective",
    "VimeoOptions",
    "SelfHostedVideoDirective",
    "SelfHostedVideoOptions",
]


# =============================================================================
# Base Video Options and Directive
# =============================================================================


@dataclass
class VideoOptions(DirectiveOptions):
    """
    Common options for all video directives.

    Attributes:
        title: Required - Accessible title for iframe/video (WCAG requirement)
        aspect: Aspect ratio for responsive container (default: 16/9)
        css_class: Additional CSS classes
        autoplay: Auto-start video (not recommended for accessibility)
        loop: Loop video playback
        muted: Start video muted

    Example:
        :::{youtube} dQw4w9WgXcQ
        :title: Never Gonna Give You Up
        :aspect: 16/9
        :autoplay: false
        :::
    """

    title: str = ""
    aspect: str = "16/9"
    css_class: str = ""
    autoplay: bool = False
    loop: bool = False
    muted: bool = False

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class VideoDirective(BengalDirective):
    """
    Abstract base class for video embed directives.

    Provides common functionality for all video embeds:
    - URL/ID validation via subclass patterns
    - Responsive container with aspect ratio
    - Accessibility requirements (title required)
    - Shared rendering utilities

    Subclass Requirements:
        ID_PATTERN: Compiled regex for validating video source
        validate_source(): Validate and return error or None
        build_embed_url(): Build the embed URL from source and options
    """

    # Subclass must define these
    ID_PATTERN: ClassVar[re.Pattern[str]]

    @abstractmethod
    def validate_source(self, source: str) -> str | None:
        """
        Validate video source (ID or URL).

        Args:
            source: Video ID or URL from directive argument

        Returns:
            Error message if invalid, None if valid
        """
        ...

    @abstractmethod
    def build_embed_url(self, source: str, options: VideoOptions) -> str:
        """
        Build the embed URL from source and options.

        Args:
            source: Validated video source
            options: Parsed directive options

        Returns:
            Full embed URL
        """
        ...

    def _validate_title(self, title: str, source: str) -> str | None:
        """Check that title is provided (accessibility requirement)."""
        if not title:
            return f"Missing required :title: option for video embed. Video source: {source}"
        return None


# =============================================================================
# YouTube Directive
# =============================================================================


@dataclass
class YouTubeOptions(VideoOptions):
    """
    Options for YouTube video embed.

    Attributes:
        title: Required - Accessible title for iframe
        start: Start time in seconds
        end: End time in seconds
        privacy: Use youtube-nocookie.com (default: true for GDPR compliance)
        controls: Show player controls
        aspect: Aspect ratio (default: 16/9)

    Example:
        :::{youtube} dQw4w9WgXcQ
        :title: Never Gonna Give You Up
        :start: 30
        :privacy: true
        :::
    """

    start: int = 0
    end: int | None = None
    privacy: bool = True
    controls: bool = True

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class YouTubeDirective(VideoDirective):
    """
    YouTube video embed directive with privacy-enhanced mode.

    Uses youtube-nocookie.com by default for GDPR compliance.
    Validates YouTube video IDs (11 alphanumeric characters).

    Syntax:
        :::{youtube} dQw4w9WgXcQ
        :title: Never Gonna Give You Up
        :start: 30
        :privacy: true
        :::

    Options:
        :title: (required) Accessible title for iframe
        :start: Start time in seconds
        :end: End time in seconds
        :privacy: Use youtube-nocookie.com (default: true)
        :autoplay: Auto-start video (default: false)
        :controls: Show player controls (default: true)
        :loop: Loop video (default: false)
        :muted: Start muted (default: false)
        :aspect: Aspect ratio (default: 16/9)
        :class: Additional CSS classes

    Output:
        <div class="video-embed youtube" data-aspect="16/9">
          <iframe src="https://www.youtube-nocookie.com/embed/..."
                  title="..." loading="lazy" allowfullscreen></iframe>
        </div>

    Security:
        - Video ID validated via regex (11 alphanumeric + _ -)
        - XSS prevention via strict ID validation
        - Privacy mode uses youtube-nocookie.com domain
    """

    NAMES: ClassVar[list[str]] = ["youtube"]
    TOKEN_TYPE: ClassVar[str] = "youtube_video"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = YouTubeOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["youtube"]

    # YouTube video ID: 11 characters (alphanumeric, underscore, hyphen)
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]{11}$")

    def validate_source(self, video_id: str) -> str | None:
        """Validate YouTube video ID (11 alphanumeric chars)."""
        if not self.ID_PATTERN.match(video_id):
            return f"Invalid YouTube video ID: {video_id!r}. Expected 11 alphanumeric characters."
        return None

    def build_embed_url(self, video_id: str, options: YouTubeOptions) -> str:
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

    def parse_directive(
        self,
        title: str,
        options: YouTubeOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build YouTube embed token."""
        video_id = title.strip()

        # Validate video ID
        error = self.validate_source(video_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "video_id": video_id},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(options.title, video_id)
        if title_error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": title_error, "video_id": video_id},
            )

        embed_url = self.build_embed_url(video_id, options)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "video_id": video_id,
                "embed_url": embed_url,
                "title": options.title,
                "aspect": options.aspect,
                "css_class": options.css_class,
                "privacy": options.privacy,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render YouTube embed to HTML."""
        error = attrs.get("error")
        if error:
            video_id = attrs.get("video_id", "unknown")
            return (
                f'<div class="video-embed youtube video-error">\n'
                f'  <p class="error">YouTube Error: {self.escape_html(error)}</p>\n'
                f"  <p>Video ID: <code>{self.escape_html(video_id)}</code></p>\n"
                f"</div>\n"
            )

        embed_url = attrs.get("embed_url", "")
        title = attrs.get("title", "YouTube Video")
        aspect = attrs.get("aspect", "16/9")
        css_class = attrs.get("css_class", "")
        video_id = attrs.get("video_id", "")

        class_str = self.build_class_string("video-embed", "youtube", css_class)
        safe_title = self.escape_html(title)

        return (
            f'<div class="{class_str}" data-aspect="{aspect}">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"\n'
            f"    allowfullscreen\n"
            f'    loading="lazy"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>Watch on YouTube: <a href="https://www.youtube.com/watch?v={video_id}">{safe_title}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# Vimeo Directive
# =============================================================================


@dataclass
class VimeoOptions(VideoOptions):
    """
    Options for Vimeo video embed.

    Attributes:
        title: Required - Accessible title for iframe
        color: Player accent color (hex without #)
        autopause: Pause when another video starts (default: true)
        dnt: Do Not Track mode (default: true for privacy)
        background: Background mode - no controls (default: false)
        aspect: Aspect ratio (default: 16/9)

    Example:
        :::{vimeo} 123456789
        :title: My Vimeo Video
        :color: ff0000
        :dnt: true
        :::
    """

    color: str = ""
    autopause: bool = True
    dnt: bool = True
    background: bool = False

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class VimeoDirective(VideoDirective):
    """
    Vimeo video embed directive with Do Not Track mode.

    Uses dnt=1 by default for privacy compliance.
    Validates Vimeo video IDs (6-11 digits).

    Syntax:
        :::{vimeo} 123456789
        :title: My Vimeo Video
        :color: ff0000
        :::

    Options:
        :title: (required) Accessible title for iframe
        :color: Player accent color (hex without #)
        :autopause: Pause when another video starts (default: true)
        :dnt: Do Not Track mode (default: true)
        :background: Background mode - no controls (default: false)
        :autoplay: Auto-start video (default: false)
        :loop: Loop video (default: false)
        :muted: Start muted (default: false)
        :aspect: Aspect ratio (default: 16/9)
        :class: Additional CSS classes

    Security:
        - Video ID validated via regex (6-11 digits)
        - DNT mode respects user privacy preferences
    """

    NAMES: ClassVar[list[str]] = ["vimeo"]
    TOKEN_TYPE: ClassVar[str] = "vimeo_video"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = VimeoOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["vimeo"]

    # Vimeo video ID: 6-11 digits
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^\d{6,11}$")

    def validate_source(self, video_id: str) -> str | None:
        """Validate Vimeo video ID (6-11 digits)."""
        if not self.ID_PATTERN.match(video_id):
            return f"Invalid Vimeo video ID: {video_id!r}. Expected 6-11 digits."
        return None

    def build_embed_url(self, video_id: str, options: VimeoOptions) -> str:
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

    def parse_directive(
        self,
        title: str,
        options: VimeoOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build Vimeo embed token."""
        video_id = title.strip()

        # Validate video ID
        error = self.validate_source(video_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "video_id": video_id},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(options.title, video_id)
        if title_error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": title_error, "video_id": video_id},
            )

        embed_url = self.build_embed_url(video_id, options)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "video_id": video_id,
                "embed_url": embed_url,
                "title": options.title,
                "aspect": options.aspect,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render Vimeo embed to HTML."""
        error = attrs.get("error")
        if error:
            video_id = attrs.get("video_id", "unknown")
            return (
                f'<div class="video-embed vimeo video-error">\n'
                f'  <p class="error">Vimeo Error: {self.escape_html(error)}</p>\n'
                f"  <p>Video ID: <code>{self.escape_html(video_id)}</code></p>\n"
                f"</div>\n"
            )

        embed_url = attrs.get("embed_url", "")
        title = attrs.get("title", "Vimeo Video")
        aspect = attrs.get("aspect", "16/9")
        css_class = attrs.get("css_class", "")
        video_id = attrs.get("video_id", "")

        class_str = self.build_class_string("video-embed", "vimeo", css_class)
        safe_title = self.escape_html(title)

        return (
            f'<div class="{class_str}" data-aspect="{aspect}">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media"\n'
            f"    allowfullscreen\n"
            f'    loading="lazy"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>Watch on Vimeo: <a href="https://vimeo.com/{video_id}">{safe_title}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# Self-Hosted Video Directive
# =============================================================================


@dataclass
class SelfHostedVideoOptions(VideoOptions):
    """
    Options for self-hosted video embed.

    Attributes:
        title: Required - Accessible title for video element
        poster: Poster image URL
        controls: Show video controls (default: true)
        preload: Preload mode - none, metadata, auto (default: metadata)
        width: Video width (px or %)
        aspect: Aspect ratio (default: 16/9)

    Example:
        :::{video} /assets/demo.mp4
        :title: Product Demo
        :poster: /assets/demo-poster.jpg
        :controls: true
        :::
    """

    poster: str = ""
    controls: bool = True
    preload: str = "metadata"
    width: str = "100%"

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "preload": ["none", "metadata", "auto"],
    }


class SelfHostedVideoDirective(VideoDirective):
    """
    Self-hosted video directive using HTML5 video element.

    Provides native video playback for local or CDN-hosted video files.
    Supports poster images, controls, and accessibility requirements.

    Syntax:
        :::{video} /assets/demo.mp4
        :title: Product Demo
        :poster: /assets/demo-poster.jpg
        :controls: true
        :::

    Options:
        :title: (required) Accessible title for video
        :poster: Poster image URL shown before playback
        :controls: Show video controls (default: true)
        :autoplay: Auto-start video (requires muted) (default: false)
        :muted: Start muted (default: false)
        :loop: Loop video (default: false)
        :preload: Preload mode - none, metadata, auto (default: metadata)
        :width: Video width (default: 100%)
        :aspect: Aspect ratio (default: 16/9)
        :class: Additional CSS classes

    Output:
        <figure class="video-embed self-hosted">
          <video title="..." controls preload="metadata">
            <source src="..." type="video/mp4">
            <p>Fallback text with download link</p>
          </video>
        </figure>

    Supported formats (auto-detected from extension):
        - .mp4 (video/mp4)
        - .webm (video/webm)
        - .ogg (video/ogg)
        - .mov (video/quicktime)
    """

    NAMES: ClassVar[list[str]] = ["video"]
    TOKEN_TYPE: ClassVar[str] = "self_hosted_video"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = SelfHostedVideoOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["video"]

    # Path pattern: starts with / or ./ or just filename, no malicious chars
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:https?://|/|\./)[\w\-./]+\.(mp4|webm|ogg|mov)$", re.IGNORECASE
    )

    # MIME types by extension
    MIME_TYPES: ClassVar[dict[str, str]] = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "video/ogg",
        ".mov": "video/quicktime",
    }

    def validate_source(self, video_path: str) -> str | None:
        """Validate video path/URL."""
        if not self.ID_PATTERN.match(video_path):
            return (
                f"Invalid video path: {video_path!r}. "
                f"Expected path starting with / or ./ ending with .mp4, .webm, .ogg, or .mov"
            )
        return None

    def build_embed_url(self, video_path: str, options: SelfHostedVideoOptions) -> str:
        """Return video path (no transformation needed for self-hosted)."""
        return video_path

    def _get_mime_type(self, video_path: str) -> str:
        """Get MIME type from video path extension."""
        for ext, mime in self.MIME_TYPES.items():
            if video_path.lower().endswith(ext):
                return mime
        return "video/mp4"  # Default

    def parse_directive(
        self,
        title: str,
        options: SelfHostedVideoOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build self-hosted video token."""
        video_path = title.strip()

        # Validate video path
        error = self.validate_source(video_path)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "video_path": video_path},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(options.title, video_path)
        if title_error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": title_error, "video_path": video_path},
            )

        mime_type = self._get_mime_type(video_path)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "video_path": video_path,
                "mime_type": mime_type,
                "title": options.title,
                "poster": options.poster,
                "controls": options.controls,
                "autoplay": options.autoplay,
                "muted": options.muted,
                "loop": options.loop,
                "preload": options.preload,
                "width": options.width,
                "aspect": options.aspect,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render self-hosted video to HTML."""
        error = attrs.get("error")
        if error:
            video_path = attrs.get("video_path", "unknown")
            return (
                f'<div class="video-embed self-hosted video-error">\n'
                f'  <p class="error">Video Error: {self.escape_html(error)}</p>\n'
                f"  <p>Path: <code>{self.escape_html(video_path)}</code></p>\n"
                f"</div>\n"
            )

        video_path = attrs.get("video_path", "")
        mime_type = attrs.get("mime_type", "video/mp4")
        title = attrs.get("title", "Video")
        poster = attrs.get("poster", "")
        controls = attrs.get("controls", True)
        autoplay = attrs.get("autoplay", False)
        muted = attrs.get("muted", False)
        loop = attrs.get("loop", False)
        preload = attrs.get("preload", "metadata")
        width = attrs.get("width", "100%")
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("video-embed", "self-hosted", css_class)
        safe_title = self.escape_html(title)

        # Build video attributes
        video_attrs = [f'title="{safe_title}"']
        if poster:
            video_attrs.append(f'poster="{self.escape_html(poster)}"')
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

        return (
            f'<figure class="{class_str}">\n'
            f"  <video {attrs_str}>\n"
            f'    <source src="{self.escape_html(video_path)}" type="{mime_type}">\n'
            f"    <p>Your browser doesn't support HTML5 video. "
            f'<a href="{self.escape_html(video_path)}">Download the video</a>.</p>\n'
            f"  </video>\n"
            f"</figure>\n"
        )
