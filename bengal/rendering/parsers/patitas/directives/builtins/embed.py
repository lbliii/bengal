"""External service embed directives for documentation.

Provides:
- gist: GitHub Gist embeds
- codepen: CodePen interactive embeds
- codesandbox: CodeSandbox project embeds
- stackblitz: StackBlitz project embeds
- spotify: Spotify audio embeds (tracks, albums, playlists, podcasts)
- soundcloud: SoundCloud audio embeds

Use cases:
- Code examples from GitHub Gists
- Interactive code playgrounds
- Audio content in documentation

Security:
All IDs/URLs are validated via regex patterns to prevent XSS and injection.
Script-based embeds (Gist) include noscript fallbacks.

Accessibility:
Title is required for iframe-based embeds to meet WCAG 2.1 AA requirements.

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's embed directives exactly for parity.

"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import quote

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = [
    "GistDirective",
    "CodePenDirective",
    "CodeSandboxDirective",
    "StackBlitzDirective",
    "SpotifyDirective",
    "SoundCloudDirective",
]


# =============================================================================
# GitHub Gist Directive
# =============================================================================

# Gist ID pattern: username/32-char hex ID
GIST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+/[a-f0-9]{32}$")


@dataclass(frozen=True, slots=True)
class GistOptions(DirectiveOptions):
    """Options for GitHub Gist embed."""

    file: str = ""
    css_class: str = ""

    # Computed attributes (populated during parse)
    gist_ref: str = ""
    error: str = ""


class GistDirective:
    """
    GitHub Gist embed directive.
    
    Syntax:
        :::{gist} username/abc123def456789012345678901234567890
        :file: example.py
        :::
    
    Output:
        <div class="gist-embed">
          <script src="https://gist.github.com/username/id.js?file=example.py"></script>
          <noscript><p>View gist: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("gist",)
    token_type: ClassVar[str] = "gist_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[GistOptions]] = GistOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: GistOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build Gist embed AST node."""
        gist_ref = title.strip() if title else ""

        # Validate gist reference
        error = ""
        if not GIST_ID_PATTERN.match(gist_ref):
            error = (
                f"Invalid gist reference: {gist_ref!r}. "
                f"Expected format: username/32-character-hex-id"
            )

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            gist_ref=gist_ref,
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
        node: Directive[GistOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render Gist embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            gist_ref = getattr(opts, "gist_ref", "unknown")
            sb.append(
                f'<div class="gist-embed gist-error">\n'
                f'  <p class="error">Gist Error: {html_escape(error)}</p>\n'
                f"  <p>Reference: <code>{html_escape(gist_ref)}</code></p>\n"
                f"</div>\n"
            )
            return

        gist_ref = getattr(opts, "gist_ref", "")
        file = opts.file
        css_class = opts.css_class

        # Build class string
        classes = ["gist-embed"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        # Build script URL
        script_url = f"https://gist.github.com/{gist_ref}.js"
        if file:
            script_url += f"?file={html_escape(file)}"

        gist_url = f"https://gist.github.com/{gist_ref}"

        sb.append(f'<div class="{class_str}">\n')
        sb.append(f'  <script src="{script_url}"></script>\n')
        sb.append("  <noscript>\n")
        sb.append(f'    <p>View gist: <a href="{gist_url}">{html_escape(gist_ref)}</a></p>\n')
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# CodePen Directive
# =============================================================================

# CodePen pattern: username/pen/pen_id or just username/pen_id
CODEPEN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+/(?:pen/)?[a-zA-Z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class CodePenOptions(DirectiveOptions):
    """Options for CodePen embed."""

    title: str = ""
    default_tab: str = "result"
    height: int = 300
    theme: str = "dark"
    editable: bool = False
    preview: bool = True
    css_class: str = ""

    # Computed attributes (populated during parse)
    username: str = ""
    pen_id: str = ""
    error: str = ""


class CodePenDirective:
    """
    CodePen embed directive.
    
    Syntax:
        :::{codepen} chriscoyier/pen/abc123
        :title: CSS Grid Example
        :default-tab: result
        :height: 400
        :::
    
    Output:
        <div class="code-embed codepen" style="height: 400px">
          <iframe src="https://codepen.io/..." title="..." ...></iframe>
          <noscript><p>See the Pen: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("codepen",)
    token_type: ClassVar[str] = "codepen_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[CodePenOptions]] = CodePenOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: CodePenOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build CodePen embed AST node."""
        pen_ref = title.strip() if title else ""

        # Validate pen reference
        error = ""
        if not CODEPEN_ID_PATTERN.match(pen_ref):
            error = (
                f"Invalid CodePen reference: {pen_ref!r}. "
                f"Expected format: username/pen/pen_id or username/pen_id"
            )
        elif not options.title:
            error = f"Missing required :title: option for CodePen embed. Pen: {pen_ref}"

        # Parse pen reference into username and pen_id
        username, pen_id = self._parse_pen_ref(pen_ref)

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            username=username,
            pen_id=pen_id,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def _parse_pen_ref(self, pen_ref: str) -> tuple[str, str]:
        """Parse pen reference into (username, pen_id)."""
        parts = pen_ref.split("/")
        if len(parts) == 3 and parts[1] == "pen":
            return parts[0], parts[2]
        elif len(parts) == 2:
            return parts[0], parts[1]
        return "", ""

    def render(
        self,
        node: Directive[CodePenOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render CodePen embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            username = getattr(opts, "username", "")
            pen_id = getattr(opts, "pen_id", "")
            pen_ref = f"{username}/{pen_id}"
            sb.append(
                f'<div class="code-embed codepen code-error">\n'
                f'  <p class="error">CodePen Error: {html_escape(error)}</p>\n'
                f"  <p>Reference: <code>{html_escape(pen_ref)}</code></p>\n"
                f"</div>\n"
            )
            return

        username = getattr(opts, "username", "")
        pen_id = getattr(opts, "pen_id", "")
        title = opts.title or "CodePen Embed"
        default_tab = opts.default_tab
        height = opts.height
        theme = opts.theme
        editable = opts.editable
        preview = opts.preview
        css_class = opts.css_class

        # Build class string
        classes = ["code-embed", "codepen"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build iframe URL
        params = [f"default-tab={default_tab}", f"theme-id={theme}"]
        if editable:
            params.append("editable=true")
        if preview:
            params.append("preview=true")

        embed_url = f"https://codepen.io/{username}/embed/{pen_id}?{'&'.join(params)}"
        pen_url = f"https://codepen.io/{username}/pen/{pen_id}"

        sb.append(f'<div class="{class_str}" style="height: {height}px">\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append('    style="width: 100%; height: 100%"\n')
        sb.append("    allowfullscreen\n")
        sb.append('    loading="lazy"\n')
        sb.append(
            '    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"\n'
        )
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(
            f'    <p>See the Pen <a href="{pen_url}">{safe_title}</a> '
            f"by {html_escape(username)} on CodePen.</p>\n"
        )
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# CodeSandbox Directive
# =============================================================================

# CodeSandbox ID: 5+ alphanumeric characters or 'new' for template
CODESANDBOX_ID_PATTERN = re.compile(r"^[a-z0-9]{5,}$|^new$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class CodeSandboxOptions(DirectiveOptions):
    """Options for CodeSandbox embed."""

    title: str = ""
    module: str = ""
    view: str = "split"
    height: int = 500
    fontsize: int = 14
    hidenavigation: bool = False
    theme: str = "dark"
    css_class: str = ""

    # Computed attributes (populated during parse)
    sandbox_id: str = ""
    error: str = ""


class CodeSandboxDirective:
    """
    CodeSandbox embed directive.
    
    Syntax:
        :::{codesandbox} new
        :title: React Example
        :module: /src/App.js
        :view: preview
        :::
    
    Output:
        <div class="code-embed codesandbox" style="height: 500px">
          <iframe src="https://codesandbox.io/embed/..." title="..." ...></iframe>
          <noscript><p>View on CodeSandbox: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("codesandbox",)
    token_type: ClassVar[str] = "codesandbox_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[CodeSandboxOptions]] = CodeSandboxOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: CodeSandboxOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build CodeSandbox embed AST node."""
        sandbox_id = title.strip() if title else ""

        # Validate sandbox ID
        error = ""
        if not CODESANDBOX_ID_PATTERN.match(sandbox_id):
            error = (
                f"Invalid CodeSandbox ID: {sandbox_id!r}. "
                f"Expected 5+ alphanumeric characters or 'new'"
            )
        elif not options.title:
            error = f"Missing required :title: option for CodeSandbox embed. ID: {sandbox_id}"

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            sandbox_id=sandbox_id,
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
        node: Directive[CodeSandboxOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render CodeSandbox embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            sandbox_id = getattr(opts, "sandbox_id", "unknown")
            sb.append(
                f'<div class="code-embed codesandbox code-error">\n'
                f'  <p class="error">CodeSandbox Error: {html_escape(error)}</p>\n'
                f"  <p>ID: <code>{html_escape(sandbox_id)}</code></p>\n"
                f"</div>\n"
            )
            return

        sandbox_id = getattr(opts, "sandbox_id", "")
        title = opts.title or "CodeSandbox Embed"
        module = opts.module
        view = opts.view
        height = opts.height
        fontsize = opts.fontsize
        hidenavigation = opts.hidenavigation
        theme = opts.theme
        css_class = opts.css_class

        # Build class string
        classes = ["code-embed", "codesandbox"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build iframe URL
        params = [f"view={view}", f"fontsize={fontsize}", f"theme={theme}"]
        if module:
            params.append(f"module={html_escape(module)}")
        if hidenavigation:
            params.append("hidenavigation=1")

        embed_url = f"https://codesandbox.io/embed/{sandbox_id}?{'&'.join(params)}"
        sandbox_url = f"https://codesandbox.io/s/{sandbox_id}"

        sb.append(f'<div class="{class_str}" style="height: {height}px">\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append(
            '    style="width: 100%; height: 100%; border: 0; border-radius: var(--radius-md, 8px); '
            'overflow: hidden"\n'
        )
        sb.append(
            '    allow="accelerometer; ambient-light-sensor; camera; encrypted-media; geolocation; '
            'gyroscope; hid; microphone; midi; payment; usb; vr; xr-spatial-tracking"\n'
        )
        sb.append(
            '    sandbox="allow-forms allow-modals allow-popups allow-presentation '
            'allow-same-origin allow-scripts"\n'
        )
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(f'    <p>View on CodeSandbox: <a href="{sandbox_url}">{safe_title}</a></p>\n')
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# StackBlitz Directive
# =============================================================================

# StackBlitz ID: alphanumeric, underscore, hyphen
STACKBLITZ_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass(frozen=True, slots=True)
class StackBlitzOptions(DirectiveOptions):
    """Options for StackBlitz embed."""

    title: str = ""
    file: str = ""
    view: str = "both"
    height: int = 500
    hidenavigation: bool = False
    hidedevtools: bool = False
    css_class: str = ""

    # Computed attributes (populated during parse)
    project_id: str = ""
    error: str = ""


class StackBlitzDirective:
    """
    StackBlitz embed directive.
    
    Syntax:
        :::{stackblitz} angular-quickstart
        :title: Angular Demo
        :file: src/app.component.ts
        :view: preview
        :::
    
    Output:
        <div class="code-embed stackblitz" style="height: 500px">
          <iframe src="https://stackblitz.com/edit/..." title="..." ...></iframe>
          <noscript><p>View on StackBlitz: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("stackblitz",)
    token_type: ClassVar[str] = "stackblitz_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[StackBlitzOptions]] = StackBlitzOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: StackBlitzOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build StackBlitz embed AST node."""
        project_id = title.strip() if title else ""

        # Validate project ID
        error = ""
        if not STACKBLITZ_ID_PATTERN.match(project_id):
            error = (
                f"Invalid StackBlitz project ID: {project_id!r}. "
                f"Expected alphanumeric characters, underscores, or hyphens"
            )
        elif not options.title:
            error = f"Missing required :title: option for StackBlitz embed. ID: {project_id}"

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            project_id=project_id,
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
        node: Directive[StackBlitzOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render StackBlitz embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            project_id = getattr(opts, "project_id", "unknown")
            sb.append(
                f'<div class="code-embed stackblitz code-error">\n'
                f'  <p class="error">StackBlitz Error: {html_escape(error)}</p>\n'
                f"  <p>Project: <code>{html_escape(project_id)}</code></p>\n"
                f"</div>\n"
            )
            return

        project_id = getattr(opts, "project_id", "")
        title = opts.title or "StackBlitz Embed"
        file = opts.file
        view = opts.view
        height = opts.height
        hidenavigation = opts.hidenavigation
        hidedevtools = opts.hidedevtools
        css_class = opts.css_class

        # Build class string
        classes = ["code-embed", "stackblitz"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build iframe URL
        params = [f"view={view}"]
        if file:
            params.append(f"file={html_escape(file)}")
        if hidenavigation:
            params.append("hideNavigation=1")
        if hidedevtools:
            params.append("hideDevTools=1")

        embed_url = f"https://stackblitz.com/edit/{project_id}?embed=1&{'&'.join(params)}"
        project_url = f"https://stackblitz.com/edit/{project_id}"

        sb.append(f'<div class="{class_str}" style="height: {height}px">\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append(
            '    style="width: 100%; height: 100%; border: 0; border-radius: var(--radius-md, 8px)"\n'
        )
        sb.append(
            '    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"\n'
        )
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(f'    <p>View on StackBlitz: <a href="{project_url}">{safe_title}</a></p>\n')
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# Spotify Directive
# =============================================================================

# Spotify ID: 22 alphanumeric characters (base62)
SPOTIFY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]{22}$")

# Default heights by content type
SPOTIFY_HEIGHTS: dict[str, int] = {
    "track": 152,
    "album": 352,
    "playlist": 352,
    "episode": 232,
    "show": 352,
    "artist": 352,
}


@dataclass(frozen=True, slots=True)
class SpotifyOptions(DirectiveOptions):
    """Options for Spotify embed."""

    title: str = ""
    type: str = "track"
    height: int = 0  # 0 means auto-detect based on type
    theme: int = 0  # 0 = dark, 1 = light
    css_class: str = ""

    # Computed attributes (populated during parse)
    spotify_id: str = ""
    error: str = ""


class SpotifyDirective:
    """
    Spotify embed directive.
    
    Syntax:
        :::{spotify} 4iV5W9uYEdYUVa79Axb7Rh
        :title: Bohemian Rhapsody by Queen
        :type: track
        :::
    
    Output:
        <div class="audio-embed spotify" style="height: 152px">
          <iframe src="https://open.spotify.com/embed/track/..." ...></iframe>
          <noscript><p>Listen on Spotify: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("spotify",)
    token_type: ClassVar[str] = "spotify_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[SpotifyOptions]] = SpotifyOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: SpotifyOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build Spotify embed AST node."""
        spotify_id = title.strip() if title else ""

        # Validate Spotify ID
        error = ""
        if not SPOTIFY_ID_PATTERN.match(spotify_id):
            error = f"Invalid Spotify ID: {spotify_id!r}. Expected 22 alphanumeric characters."
        elif not options.title:
            error = f"Missing required :title: option for Spotify embed. ID: {spotify_id}"

        # Auto-detect height based on content type if not specified
        height = options.height if options.height > 0 else SPOTIFY_HEIGHTS.get(options.type, 152)

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            height=height,
            spotify_id=spotify_id,
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
        node: Directive[SpotifyOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render Spotify embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            spotify_id = getattr(opts, "spotify_id", "unknown")
            sb.append(
                f'<div class="audio-embed spotify audio-error">\n'
                f'  <p class="error">Spotify Error: {html_escape(error)}</p>\n'
                f"  <p>ID: <code>{html_escape(spotify_id)}</code></p>\n"
                f"</div>\n"
            )
            return

        spotify_id = getattr(opts, "spotify_id", "")
        title = opts.title or "Spotify Embed"
        content_type = opts.type
        height = opts.height
        theme = opts.theme
        css_class = opts.css_class

        # Build class string
        classes = ["audio-embed", "spotify"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build embed URL
        embed_url = f"https://open.spotify.com/embed/{content_type}/{spotify_id}?theme={theme}"
        spotify_url = f"https://open.spotify.com/{content_type}/{spotify_id}"

        sb.append(f'<div class="{class_str}" style="height: {height}px">\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append('    style="width: 100%; height: 100%; border: 0; border-radius: 12px"\n')
        sb.append(
            '    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"\n'
        )
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(f'    <p>Listen on Spotify: <a href="{spotify_url}">{safe_title}</a></p>\n')
        sb.append("  </noscript>\n")
        sb.append("</div>\n")


# =============================================================================
# SoundCloud Directive
# =============================================================================

# SoundCloud URL path: username/track-name (alphanumeric, hyphens, underscores)
SOUNDCLOUD_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?$")

# Default heights by content type
SOUNDCLOUD_HEIGHTS: dict[str, int] = {
    "track": 166,
    "track_visual": 300,
    "playlist": 450,
}


@dataclass(frozen=True, slots=True)
class SoundCloudOptions(DirectiveOptions):
    """Options for SoundCloud embed."""

    title: str = ""
    type: str = "track"
    height: int = 0  # 0 means auto-detect based on type
    color: str = "ff5500"  # SoundCloud orange
    autoplay: bool = False
    hide_related: bool = False
    show_comments: bool = True
    show_user: bool = True
    show_reposts: bool = False
    visual: bool = False
    css_class: str = ""

    # Computed attributes (populated during parse)
    url_path: str = ""
    error: str = ""


class SoundCloudDirective:
    """
    SoundCloud embed directive.
    
    Syntax:
        :::{soundcloud} artistname/track-title
        :title: Track Title by Artist
        :::
    
    Output:
        <div class="audio-embed soundcloud" style="height: 166px">
          <iframe src="https://w.soundcloud.com/player/?url=..." ...></iframe>
          <noscript><p>Listen on SoundCloud: ...</p></noscript>
        </div>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("soundcloud",)
    token_type: ClassVar[str] = "soundcloud_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[SoundCloudOptions]] = SoundCloudOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: SoundCloudOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build SoundCloud embed AST node."""
        url_path = title.strip() if title else ""

        # Clean the path
        cleaned_path = self._clean_path(url_path)

        # Validate SoundCloud URL path
        error = ""
        if not SOUNDCLOUD_PATH_PATTERN.match(cleaned_path):
            error = f"Invalid SoundCloud path: {url_path!r}. Expected format: username/track-name"
        elif not options.title:
            error = f"Missing required :title: option for SoundCloud embed. Path: {cleaned_path}"

        # Auto-detect height based on content type and visual mode
        if options.height > 0:
            height = options.height
        elif options.visual and options.type == "track":
            height = SOUNDCLOUD_HEIGHTS["track_visual"]
        else:
            height = SOUNDCLOUD_HEIGHTS.get(options.type, 166)

        # Store computed values as attributes
        from dataclasses import replace

        computed_opts = replace(
            options,
            height=height,
            color=options.color.lstrip("#"),
            url_path=cleaned_path,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,  # Pass typed options with computed attributes
            children=tuple(children),
        )

    def _clean_path(self, url_path: str) -> str:
        """Clean and normalize a SoundCloud URL path."""
        cleaned = url_path
        if cleaned.startswith("https://soundcloud.com/"):
            cleaned = cleaned[23:]
        elif cleaned.startswith("soundcloud.com/"):
            cleaned = cleaned[15:]
        if "?" in cleaned:
            cleaned = cleaned.split("?")[0]
        return cleaned

    def render(
        self,
        node: Directive[SoundCloudOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render SoundCloud embed to HTML."""
        opts = node.options  # Direct typed access!

        # Get computed attributes
        error = getattr(opts, "error", "")
        if error:
            url_path = getattr(opts, "url_path", "unknown")
            sb.append(
                f'<div class="audio-embed soundcloud audio-error">\n'
                f'  <p class="error">SoundCloud Error: {html_escape(error)}</p>\n'
                f"  <p>Path: <code>{html_escape(url_path)}</code></p>\n"
                f"</div>\n"
            )
            return

        url_path = getattr(opts, "url_path", "")
        title = opts.title or "SoundCloud Embed"
        height = opts.height
        color = opts.color
        autoplay = opts.autoplay
        hide_related = opts.hide_related
        show_comments = opts.show_comments
        show_user = opts.show_user
        show_reposts = opts.show_reposts
        visual = opts.visual
        css_class = opts.css_class

        # Build class string
        classes = ["audio-embed", "soundcloud"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build embed URL with parameters
        soundcloud_url = f"https://soundcloud.com/{url_path}"
        encoded_url = quote(soundcloud_url, safe="")
        params = [
            f"url={encoded_url}",
            f"color=%23{color}",
            f"auto_play={'true' if autoplay else 'false'}",
            f"hide_related={'true' if hide_related else 'false'}",
            f"show_comments={'true' if show_comments else 'false'}",
            f"show_user={'true' if show_user else 'false'}",
            f"show_reposts={'true' if show_reposts else 'false'}",
            f"visual={'true' if visual else 'false'}",
        ]
        embed_url = f"https://w.soundcloud.com/player/?{'&'.join(params)}"

        sb.append(f'<div class="{class_str}" style="height: {height}px">\n')
        sb.append("  <iframe\n")
        sb.append(f'    src="{embed_url}"\n')
        sb.append(f'    title="{safe_title}"\n')
        sb.append('    style="width: 100%; height: 100%; border: 0"\n')
        sb.append('    allow="autoplay"\n')
        sb.append('    loading="lazy"\n')
        sb.append("  ></iframe>\n")
        sb.append("  <noscript>\n")
        sb.append(f'    <p>Listen on SoundCloud: <a href="{soundcloud_url}">{safe_title}</a></p>\n')
        sb.append("  </noscript>\n")
        sb.append("</div>\n")
