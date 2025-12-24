"""
External service embed directives for Bengal.

Provides directives for embedding external services:
- GitHub Gists
- CodePen
- CodeSandbox
- StackBlitz
- Spotify (tracks, albums, playlists, podcasts)
- SoundCloud (tracks, playlists)

Architecture:
    All embed directives extend BengalDirective with type-specific validation
    and rendering for their respective services.

Security:
    All IDs/URLs are validated via regex patterns to prevent XSS and injection.
    Script-based embeds (Gist) include noscript fallbacks.

Accessibility:
    Title is required for iframe-based embeds to meet WCAG 2.1 AA requirements.

Related:
    - bengal/rendering/plugins/directives/base.py: BengalDirective
    - RFC: plan/active/rfc-media-embed-directives.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken

__all__ = [
    "GistDirective",
    "GistOptions",
    "CodePenDirective",
    "CodePenOptions",
    "CodeSandboxDirective",
    "CodeSandboxOptions",
    "StackBlitzDirective",
    "StackBlitzOptions",
    "SpotifyDirective",
    "SpotifyOptions",
]


# =============================================================================
# GitHub Gist Directive
# =============================================================================


@dataclass
class GistOptions(DirectiveOptions):
    """
    Options for GitHub Gist embed.

    Attributes:
        file: Specific file from gist to display
        css_class: Additional CSS classes

    Example:
        :::{gist} username/abc123def456789012345678901234567890
        :file: example.py
        :::
    """

    file: str = ""
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class GistDirective(BengalDirective):
    """
    GitHub Gist embed directive.

    Embeds GitHub Gists using the official script embed method.
    Includes noscript fallback with link to gist.

    Syntax:
        :::{gist} username/gist_id
        :file: example.py
        :::

    Options:
        :file: Specific file from gist to display
        :class: Additional CSS classes

    Output:
        <div class="gist-embed">
          <script src="https://gist.github.com/username/gist_id.js?file=example.py"></script>
          <noscript><p>View gist: <a href="...">username/gist_id</a></p></noscript>
        </div>

    Security:
        - Username validated (alphanumeric, underscore, hyphen)
        - Gist ID validated (32 hex characters)
        - File parameter escaped for URL safety
    """

    NAMES: ClassVar[list[str]] = ["gist"]
    TOKEN_TYPE: ClassVar[str] = "gist_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = GistOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["gist"]

    # Gist ID pattern: username/32-char hex ID
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]+/[a-f0-9]{32}$")

    def validate_source(self, gist_ref: str) -> str | None:
        """Validate gist reference (username/gist_id)."""
        if not self.ID_PATTERN.match(gist_ref):
            return (
                f"Invalid gist reference: {gist_ref!r}. "
                f"Expected format: username/32-character-hex-id"
            )
        return None

    def parse_directive(
        self,
        title: str,
        options: GistOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build gist embed token."""
        gist_ref = title.strip()

        # Validate gist reference
        error = self.validate_source(gist_ref)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "gist_ref": gist_ref},
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "gist_ref": gist_ref,
                "file": options.file,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render gist embed to HTML."""
        error = attrs.get("error")
        if error:
            gist_ref = attrs.get("gist_ref", "unknown")
            return (
                f'<div class="gist-embed gist-error">\n'
                f'  <p class="error">Gist Error: {self.escape_html(error)}</p>\n'
                f"  <p>Reference: <code>{self.escape_html(gist_ref)}</code></p>\n"
                f"</div>\n"
            )

        gist_ref = attrs.get("gist_ref", "")
        file = attrs.get("file", "")
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("gist-embed", css_class)

        # Build script URL
        script_url = f"https://gist.github.com/{gist_ref}.js"
        if file:
            script_url += f"?file={self.escape_html(file)}"

        gist_url = f"https://gist.github.com/{gist_ref}"

        return (
            f'<div class="{class_str}">\n'
            f'  <script src="{script_url}"></script>\n'
            f"  <noscript>\n"
            f'    <p>View gist: <a href="{gist_url}">{self.escape_html(gist_ref)}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# CodePen Directive
# =============================================================================


@dataclass
class CodePenOptions(DirectiveOptions):
    """
    Options for CodePen embed.

    Attributes:
        title: Required - Accessible title for iframe
        default_tab: Tab to show - html, css, js, result (default: result)
        height: Height in pixels (default: 300)
        theme: Color theme - light, dark, or theme ID (default: dark)
        editable: Allow editing (default: false)
        preview: Show preview on load (default: true)
        css_class: Additional CSS classes

    Example:
        :::{codepen} chriscoyier/pen/abc123
        :title: CSS Grid Example
        :default-tab: result
        :height: 400
        :::
    """

    title: str = ""
    default_tab: str = "result"
    height: int = 300
    theme: str = "dark"
    editable: bool = False
    preview: bool = True
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "default-tab": "default_tab",
    }
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "default_tab": ["html", "css", "js", "result"],
        "theme": ["light", "dark"],
    }


class CodePenDirective(BengalDirective):
    """
    CodePen embed directive.

    Embeds CodePen pens using iframe with customizable display options.

    Syntax:
        :::{codepen} username/pen/pen_id
        :title: Interactive Example
        :default-tab: result
        :height: 400
        :::

    Options:
        :title: (required) Accessible title for iframe
        :default-tab: Tab to show - html, css, js, result (default: result)
        :height: Height in pixels (default: 300)
        :theme: Color theme - light, dark (default: dark)
        :editable: Allow editing (default: false)
        :preview: Show preview on load (default: true)
        :class: Additional CSS classes

    Security:
        - Username validated (alphanumeric, underscore, hyphen)
        - Pen ID validated (alphanumeric, underscore, hyphen)
    """

    NAMES: ClassVar[list[str]] = ["codepen"]
    TOKEN_TYPE: ClassVar[str] = "codepen_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CodePenOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["codepen"]

    # CodePen pattern: username/pen/pen_id or just username/pen_id
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]+/(?:pen/)?[a-zA-Z0-9_-]+$")

    def validate_source(self, pen_ref: str) -> str | None:
        """Validate CodePen reference."""
        if not self.ID_PATTERN.match(pen_ref):
            return (
                f"Invalid CodePen reference: {pen_ref!r}. "
                f"Expected format: username/pen/pen_id or username/pen_id"
            )
        return None

    def _parse_pen_ref(self, pen_ref: str) -> tuple[str, str]:
        """Parse pen reference into (username, pen_id)."""
        parts = pen_ref.split("/")
        if len(parts) == 3 and parts[1] == "pen":
            return parts[0], parts[2]
        elif len(parts) == 2:
            return parts[0], parts[1]
        return "", ""

    def parse_directive(
        self,
        title: str,
        options: CodePenOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build CodePen embed token."""
        pen_ref = title.strip()

        # Validate pen reference
        error = self.validate_source(pen_ref)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "pen_ref": pen_ref},
            )

        # Validate title (accessibility requirement)
        if not options.title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for CodePen embed. Pen: {pen_ref}",
                    "pen_ref": pen_ref,
                },
            )

        username, pen_id = self._parse_pen_ref(pen_ref)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "username": username,
                "pen_id": pen_id,
                "title": options.title,
                "default_tab": options.default_tab,
                "height": options.height,
                "theme": options.theme,
                "editable": options.editable,
                "preview": options.preview,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render CodePen embed to HTML."""
        error = attrs.get("error")
        if error:
            pen_ref = attrs.get("pen_ref", "unknown")
            return (
                f'<div class="code-embed codepen code-error">\n'
                f'  <p class="error">CodePen Error: {self.escape_html(error)}</p>\n'
                f"  <p>Reference: <code>{self.escape_html(pen_ref)}</code></p>\n"
                f"</div>\n"
            )

        username = attrs.get("username", "")
        pen_id = attrs.get("pen_id", "")
        title = attrs.get("title", "CodePen Embed")
        default_tab = attrs.get("default_tab", "result")
        height = attrs.get("height", 300)
        theme = attrs.get("theme", "dark")
        editable = attrs.get("editable", False)
        preview = attrs.get("preview", True)
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("code-embed", "codepen", css_class)
        safe_title = self.escape_html(title)

        # Build iframe URL
        params = [f"default-tab={default_tab}", f"theme-id={theme}"]
        if editable:
            params.append("editable=true")
        if preview:
            params.append("preview=true")

        embed_url = f"https://codepen.io/{username}/embed/{pen_id}?{'&'.join(params)}"
        pen_url = f"https://codepen.io/{username}/pen/{pen_id}"

        return (
            f'<div class="{class_str}" style="height: {height}px">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    style="width: 100%; height: 100%"\n'
            f"    allowfullscreen\n"
            f'    loading="lazy"\n'
            f'    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>See the Pen <a href="{pen_url}">{safe_title}</a> by {self.escape_html(username)} on CodePen.</p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# CodeSandbox Directive
# =============================================================================


@dataclass
class CodeSandboxOptions(DirectiveOptions):
    """
    Options for CodeSandbox embed.

    Attributes:
        title: Required - Accessible title for iframe
        module: File to show initially
        view: Display mode - editor, preview, split (default: split)
        height: Height in pixels (default: 500)
        fontsize: Editor font size (default: 14)
        hidenavigation: Hide file navigation (default: false)
        theme: Color theme - light, dark (default: dark)
        css_class: Additional CSS classes

    Example:
        :::{codesandbox} new
        :title: React Example
        :module: /src/App.js
        :view: preview
        :::
    """

    title: str = ""
    module: str = ""
    view: str = "split"
    height: int = 500
    fontsize: int = 14
    hidenavigation: bool = False
    theme: str = "dark"
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "view": ["editor", "preview", "split"],
        "theme": ["light", "dark"],
    }


class CodeSandboxDirective(BengalDirective):
    """
    CodeSandbox embed directive.

    Embeds CodeSandbox projects using iframe with customizable display options.

    Syntax:
        :::{codesandbox} sandbox_id
        :title: React Example
        :module: /src/App.js
        :view: preview
        :::

    Options:
        :title: (required) Accessible title for iframe
        :module: File to show initially
        :view: Display mode - editor, preview, split (default: split)
        :height: Height in pixels (default: 500)
        :fontsize: Editor font size (default: 14)
        :hidenavigation: Hide file navigation (default: false)
        :theme: Color theme - light, dark (default: dark)
        :class: Additional CSS classes

    Security:
        - Sandbox ID validated (alphanumeric, 5+ characters)
    """

    NAMES: ClassVar[list[str]] = ["codesandbox"]
    TOKEN_TYPE: ClassVar[str] = "codesandbox_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = CodeSandboxOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["codesandbox"]

    # CodeSandbox ID: 5+ alphanumeric characters or 'new' for template
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-z0-9]{5,}$|^new$", re.IGNORECASE)

    def validate_source(self, sandbox_id: str) -> str | None:
        """Validate CodeSandbox ID."""
        if not self.ID_PATTERN.match(sandbox_id):
            return (
                f"Invalid CodeSandbox ID: {sandbox_id!r}. "
                f"Expected 5+ alphanumeric characters or 'new'"
            )
        return None

    def parse_directive(
        self,
        title: str,
        options: CodeSandboxOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build CodeSandbox embed token."""
        sandbox_id = title.strip()

        # Validate sandbox ID
        error = self.validate_source(sandbox_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "sandbox_id": sandbox_id},
            )

        # Validate title (accessibility requirement)
        if not options.title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for CodeSandbox embed. ID: {sandbox_id}",
                    "sandbox_id": sandbox_id,
                },
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "sandbox_id": sandbox_id,
                "title": options.title,
                "module": options.module,
                "view": options.view,
                "height": options.height,
                "fontsize": options.fontsize,
                "hidenavigation": options.hidenavigation,
                "theme": options.theme,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render CodeSandbox embed to HTML."""
        error = attrs.get("error")
        if error:
            sandbox_id = attrs.get("sandbox_id", "unknown")
            return (
                f'<div class="code-embed codesandbox code-error">\n'
                f'  <p class="error">CodeSandbox Error: {self.escape_html(error)}</p>\n'
                f"  <p>ID: <code>{self.escape_html(sandbox_id)}</code></p>\n"
                f"</div>\n"
            )

        sandbox_id = attrs.get("sandbox_id", "")
        title = attrs.get("title", "CodeSandbox Embed")
        module = attrs.get("module", "")
        view = attrs.get("view", "split")
        height = attrs.get("height", 500)
        fontsize = attrs.get("fontsize", 14)
        hidenavigation = attrs.get("hidenavigation", False)
        theme = attrs.get("theme", "dark")
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("code-embed", "codesandbox", css_class)
        safe_title = self.escape_html(title)

        # Build iframe URL
        params = [f"view={view}", f"fontsize={fontsize}", f"theme={theme}"]
        if module:
            params.append(f"module={self.escape_html(module)}")
        if hidenavigation:
            params.append("hidenavigation=1")

        embed_url = f"https://codesandbox.io/embed/{sandbox_id}?{'&'.join(params)}"
        sandbox_url = f"https://codesandbox.io/s/{sandbox_id}"

        return (
            f'<div class="{class_str}" style="height: {height}px">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    style="width: 100%; height: 100%; border: 0; border-radius: var(--radius-md, 8px); overflow: hidden"\n'
            f'    allow="accelerometer; ambient-light-sensor; camera; encrypted-media; geolocation; gyroscope; hid; microphone; midi; payment; usb; vr; xr-spatial-tracking"\n'
            f'    sandbox="allow-forms allow-modals allow-popups allow-presentation allow-same-origin allow-scripts"\n'
            f'    loading="lazy"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>View on CodeSandbox: <a href="{sandbox_url}">{safe_title}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# StackBlitz Directive
# =============================================================================


@dataclass
class StackBlitzOptions(DirectiveOptions):
    """
    Options for StackBlitz embed.

    Attributes:
        title: Required - Accessible title for iframe
        file: File to show initially
        view: Display mode - editor, preview, both (default: both)
        height: Height in pixels (default: 500)
        hidenavigation: Hide file navigation (default: false)
        hidedevtools: Hide dev tools panel (default: false)
        css_class: Additional CSS classes

    Example:
        :::{stackblitz} angular-quickstart
        :title: Angular Demo
        :file: src/app.component.ts
        :view: preview
        :::
    """

    title: str = ""
    file: str = ""
    view: str = "both"
    height: int = 500
    hidenavigation: bool = False
    hidedevtools: bool = False
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "view": ["editor", "preview", "both"],
    }


class StackBlitzDirective(BengalDirective):
    """
    StackBlitz embed directive.

    Embeds StackBlitz projects using iframe with customizable display options.

    Syntax:
        :::{stackblitz} project_id
        :title: Angular Demo
        :file: src/app.component.ts
        :view: preview
        :::

    Options:
        :title: (required) Accessible title for iframe
        :file: File to show initially
        :view: Display mode - editor, preview, both (default: both)
        :height: Height in pixels (default: 500)
        :hidenavigation: Hide file navigation (default: false)
        :hidedevtools: Hide dev tools panel (default: false)
        :class: Additional CSS classes

    Security:
        - Project ID validated (alphanumeric, underscore, hyphen)
    """

    NAMES: ClassVar[list[str]] = ["stackblitz"]
    TOKEN_TYPE: ClassVar[str] = "stackblitz_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = StackBlitzOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["stackblitz"]

    # StackBlitz ID: alphanumeric, underscore, hyphen
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_-]+$")

    def validate_source(self, project_id: str) -> str | None:
        """Validate StackBlitz project ID."""
        if not self.ID_PATTERN.match(project_id):
            return (
                f"Invalid StackBlitz project ID: {project_id!r}. "
                f"Expected alphanumeric characters, underscores, or hyphens"
            )
        return None

    def parse_directive(
        self,
        title: str,
        options: StackBlitzOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build StackBlitz embed token."""
        project_id = title.strip()

        # Validate project ID
        error = self.validate_source(project_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "project_id": project_id},
            )

        # Validate title (accessibility requirement)
        if not options.title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for StackBlitz embed. ID: {project_id}",
                    "project_id": project_id,
                },
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "project_id": project_id,
                "title": options.title,
                "file": options.file,
                "view": options.view,
                "height": options.height,
                "hidenavigation": options.hidenavigation,
                "hidedevtools": options.hidedevtools,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render StackBlitz embed to HTML."""
        error = attrs.get("error")
        if error:
            project_id = attrs.get("project_id", "unknown")
            return (
                f'<div class="code-embed stackblitz code-error">\n'
                f'  <p class="error">StackBlitz Error: {self.escape_html(error)}</p>\n'
                f"  <p>Project: <code>{self.escape_html(project_id)}</code></p>\n"
                f"</div>\n"
            )

        project_id = attrs.get("project_id", "")
        title = attrs.get("title", "StackBlitz Embed")
        file = attrs.get("file", "")
        view = attrs.get("view", "both")
        height = attrs.get("height", 500)
        hidenavigation = attrs.get("hidenavigation", False)
        hidedevtools = attrs.get("hidedevtools", False)
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("code-embed", "stackblitz", css_class)
        safe_title = self.escape_html(title)

        # Build iframe URL
        params = [f"view={view}"]
        if file:
            params.append(f"file={self.escape_html(file)}")
        if hidenavigation:
            params.append("hideNavigation=1")
        if hidedevtools:
            params.append("hideDevTools=1")

        embed_url = f"https://stackblitz.com/edit/{project_id}?embed=1&{'&'.join(params)}"
        project_url = f"https://stackblitz.com/edit/{project_id}"

        return (
            f'<div class="{class_str}" style="height: {height}px">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    style="width: 100%; height: 100%; border: 0; border-radius: var(--radius-md, 8px)"\n'
            f'    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"\n'
            f'    loading="lazy"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>View on StackBlitz: <a href="{project_url}">{safe_title}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# Spotify Directive
# =============================================================================


@dataclass
class SpotifyOptions(DirectiveOptions):
    """
    Options for Spotify embed.

    Attributes:
        title: Required - Accessible title for iframe
        type: Content type - track, album, playlist, episode, show (default: track)
        height: Embed height in pixels (default: 152 for track, 352 for others)
        theme: Color theme - 0 for dark, 1 for light (default: 0)
        css_class: Additional CSS classes

    Example:
        :::{spotify} 4iV5W9uYEdYUVa79Axb7Rh
        :title: Bohemian Rhapsody by Queen
        :type: track
        :::
    """

    title: str = ""
    type: str = "track"
    height: int = 0  # 0 means auto-detect based on type
    theme: int = 0  # 0 = dark, 1 = light
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "type": ["track", "album", "playlist", "episode", "show", "artist"],
        "theme": [0, 1],
    }


class SpotifyDirective(BengalDirective):
    """
    Spotify embed directive.

    Embeds Spotify content (tracks, albums, playlists, podcasts) using iframe.
    Validates Spotify IDs (22 alphanumeric characters).

    Syntax:
        :::{spotify} 4iV5W9uYEdYUVa79Axb7Rh
        :title: Bohemian Rhapsody by Queen
        :type: track
        :::

    Options:
        :title: (required) Accessible title for iframe
        :type: Content type - track, album, playlist, episode, show, artist (default: track)
        :height: Embed height in pixels (auto-detected if not set)
        :theme: 0 for dark, 1 for light (default: 0)
        :class: Additional CSS classes

    Heights by type (defaults):
        - track: 152px (compact player)
        - album/playlist/show/artist: 352px (full player with art)
        - episode: 232px (medium player)

    Output:
        <div class="audio-embed spotify">
          <iframe src="https://open.spotify.com/embed/track/..."
                  title="..." loading="lazy" allowfullscreen></iframe>
        </div>

    Security:
        - Spotify ID validated via regex (22 alphanumeric characters)
        - XSS prevention via strict ID validation
    """

    NAMES: ClassVar[list[str]] = ["spotify"]
    TOKEN_TYPE: ClassVar[str] = "spotify_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = SpotifyOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["spotify"]

    # Spotify ID: 22 alphanumeric characters (base62)
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9]{22}$")

    # Default heights by content type
    DEFAULT_HEIGHTS: ClassVar[dict[str, int]] = {
        "track": 152,
        "album": 352,
        "playlist": 352,
        "episode": 232,
        "show": 352,
        "artist": 352,
    }

    def validate_source(self, spotify_id: str) -> str | None:
        """Validate Spotify ID (22 alphanumeric chars)."""
        if not self.ID_PATTERN.match(spotify_id):
            return f"Invalid Spotify ID: {spotify_id!r}. Expected 22 alphanumeric characters."
        return None

    def parse_directive(
        self,
        title: str,
        options: SpotifyOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build Spotify embed token."""
        spotify_id = title.strip()

        # Validate Spotify ID
        error = self.validate_source(spotify_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "spotify_id": spotify_id},
            )

        # Validate title (accessibility requirement)
        if not options.title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for Spotify embed. ID: {spotify_id}",
                    "spotify_id": spotify_id,
                },
            )

        # Auto-detect height based on content type if not specified
        height = (
            options.height if options.height > 0 else self.DEFAULT_HEIGHTS.get(options.type, 152)
        )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "spotify_id": spotify_id,
                "title": options.title,
                "content_type": options.type,
                "height": height,
                "theme": options.theme,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render Spotify embed to HTML."""
        error = attrs.get("error")
        if error:
            spotify_id = attrs.get("spotify_id", "unknown")
            return (
                f'<div class="audio-embed spotify audio-error">\n'
                f'  <p class="error">Spotify Error: {self.escape_html(error)}</p>\n'
                f"  <p>ID: <code>{self.escape_html(spotify_id)}</code></p>\n"
                f"</div>\n"
            )

        spotify_id = attrs.get("spotify_id", "")
        title = attrs.get("title", "Spotify Embed")
        content_type = attrs.get("content_type", "track")
        height = attrs.get("height", 152)
        theme = attrs.get("theme", 0)
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("audio-embed", "spotify", css_class)
        safe_title = self.escape_html(title)

        # Build embed URL
        embed_url = f"https://open.spotify.com/embed/{content_type}/{spotify_id}?theme={theme}"
        spotify_url = f"https://open.spotify.com/{content_type}/{spotify_id}"

        return (
            f'<div class="{class_str}" style="height: {height}px">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    style="width: 100%; height: 100%; border: 0; border-radius: 12px"\n'
            f'    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"\n'
            f'    loading="lazy"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>Listen on Spotify: <a href="{spotify_url}">{safe_title}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )


# =============================================================================
# SoundCloud Directive
# =============================================================================


@dataclass
class SoundCloudOptions(DirectiveOptions):
    """
    Options for SoundCloud embed.

    Attributes:
        title: Required - Accessible title for iframe
        type: Content type - track or playlist (default: track)
        height: Embed height in pixels (default: 166 for track, 450 for playlist)
        color: Accent color hex code without # (default: ff5500 - SoundCloud orange)
        autoplay: Auto-start playback (default: false)
        hide_related: Hide related tracks (default: false)
        show_comments: Show comments (default: true)
        show_user: Show uploader info (default: true)
        show_reposts: Show reposts (default: false)
        visual: Use visual player (larger artwork) (default: false for tracks)
        css_class: Additional CSS classes

    Example:
        :::{soundcloud} artistname/track-title
        :title: Track Title by Artist
        :::

        # Also accepts full URLs:
        :::{soundcloud} https://soundcloud.com/artistname/track-title
        :title: Track Title by Artist
        :::
    """

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

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "type": ["track", "playlist"],
    }


class SoundCloudDirective(BengalDirective):
    """
    SoundCloud embed directive.

    Embeds SoundCloud tracks and playlists using iframe.
    Accepts SoundCloud URLs (username/track-slug format).

    Syntax:
        :::{soundcloud} username/track-name
        :title: Track Title
        :::

    Options:
        :title: (required) Accessible title for iframe
        :type: Content type - track or playlist (default: track)
        :height: Embed height in pixels (auto-detected if not set)
        :color: Accent color hex without # (default: ff5500)
        :autoplay: Auto-start playback (default: false)
        :hide_related: Hide related tracks (default: false)
        :show_comments: Show comments (default: true)
        :show_user: Show uploader info (default: true)
        :show_reposts: Show reposts (default: false)
        :visual: Use visual player with large artwork (default: false)
        :class: Additional CSS classes

    Heights by type (defaults):
        - track: 166px (compact player)
        - track (visual): 300px (visual player)
        - playlist: 450px (list view)

    Output:
        <div class="audio-embed soundcloud">
          <iframe src="https://w.soundcloud.com/player/?url=..."
                  title="..." loading="lazy"></iframe>
        </div>

    Security:
        - URL path validated via regex (username/track-name format)
        - XSS prevention via strict URL validation
    """

    NAMES: ClassVar[list[str]] = ["soundcloud"]
    TOKEN_TYPE: ClassVar[str] = "soundcloud_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = SoundCloudOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["soundcloud"]

    # SoundCloud URL path: username/track-name (alphanumeric, hyphens, underscores)
    # Matches: user-604227447/some-track-name or artistname/track-title
    URL_PATH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?$"
    )

    # Default heights by content type
    DEFAULT_HEIGHTS: ClassVar[dict[str, int]] = {
        "track": 166,
        "track_visual": 300,
        "playlist": 450,
    }

    def validate_source(self, url_path: str) -> str | None:
        """Validate SoundCloud URL path (username/track-name format)."""
        # Strip any leading https://soundcloud.com/ if present
        cleaned = url_path
        if cleaned.startswith("https://soundcloud.com/"):
            cleaned = cleaned[23:]  # Remove the prefix
        elif cleaned.startswith("soundcloud.com/"):
            cleaned = cleaned[15:]

        # Remove query params if present
        if "?" in cleaned:
            cleaned = cleaned.split("?")[0]

        if not self.URL_PATH_PATTERN.match(cleaned):
            return f"Invalid SoundCloud path: {url_path!r}. Expected format: username/track-name"
        return None

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

    def parse_directive(
        self,
        title: str,
        options: SoundCloudOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build SoundCloud embed token."""
        url_path = title.strip()

        # Validate SoundCloud URL path
        error = self.validate_source(url_path)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "url_path": url_path},
            )

        # Clean the path
        cleaned_path = self._clean_path(url_path)

        # Validate title (accessibility requirement)
        if not options.title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for SoundCloud embed. Path: {cleaned_path}",
                    "url_path": cleaned_path,
                },
            )

        # Auto-detect height based on content type and visual mode
        if options.height > 0:
            height = options.height
        elif options.visual and options.type == "track":
            height = self.DEFAULT_HEIGHTS["track_visual"]
        else:
            height = self.DEFAULT_HEIGHTS.get(options.type, 166)

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "url_path": cleaned_path,
                "title": options.title,
                "content_type": options.type,
                "height": height,
                "color": options.color.lstrip("#"),  # Remove # if present
                "autoplay": options.autoplay,
                "hide_related": options.hide_related,
                "show_comments": options.show_comments,
                "show_user": options.show_user,
                "show_reposts": options.show_reposts,
                "visual": options.visual,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render SoundCloud embed to HTML."""
        error = attrs.get("error")
        if error:
            url_path = attrs.get("url_path", "unknown")
            return (
                f'<div class="audio-embed soundcloud audio-error">\n'
                f'  <p class="error">SoundCloud Error: {self.escape_html(error)}</p>\n'
                f"  <p>Path: <code>{self.escape_html(url_path)}</code></p>\n"
                f"</div>\n"
            )

        url_path = attrs.get("url_path", "")
        title = attrs.get("title", "SoundCloud Embed")
        height = attrs.get("height", 166)
        color = attrs.get("color", "ff5500")
        autoplay = attrs.get("autoplay", False)
        hide_related = attrs.get("hide_related", False)
        show_comments = attrs.get("show_comments", True)
        show_user = attrs.get("show_user", True)
        show_reposts = attrs.get("show_reposts", False)
        visual = attrs.get("visual", False)
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("audio-embed", "soundcloud", css_class)
        safe_title = self.escape_html(title)

        # Build embed URL with parameters
        # SoundCloud widget accepts full URLs
        from urllib.parse import quote

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

        return (
            f'<div class="{class_str}" style="height: {height}px">\n'
            f"  <iframe\n"
            f'    src="{embed_url}"\n'
            f'    title="{safe_title}"\n'
            f'    style="width: 100%; height: 100%; border: 0"\n'
            f'    allow="autoplay"\n'
            f'    loading="lazy"\n'
            f"  ></iframe>\n"
            f"  <noscript>\n"
            f'    <p>Listen on SoundCloud: <a href="{soundcloud_url}">{safe_title}</a></p>\n'
            f"  </noscript>\n"
            f"</div>\n"
        )
