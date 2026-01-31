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
from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import StyledOptions
from bengal.directives.tokens import DirectiveToken
from bengal.directives.utils import (
    clean_soundcloud_path,
    render_error_block,
    render_noscript_fallback,
)

if TYPE_CHECKING:
    from bengal.directives.types import DirectiveRenderer, MistuneBlockState

__all__ = [
    "CodePenDirective",
    "CodePenOptions",
    "CodeSandboxDirective",
    "CodeSandboxOptions",
    "EmbedDirectiveBase",
    "EmbedOptionsBase",
    "GistDirective",
    "GistOptions",
    "SoundCloudDirective",
    "SoundCloudOptions",
    "SpotifyDirective",
    "SpotifyOptions",
    "StackBlitzDirective",
    "StackBlitzOptions",
]


# =============================================================================
# Embed Directive Base Classes
# =============================================================================


@dataclass
class EmbedOptionsBase(StyledOptions):
    """
    Base options for all embed directives.

    Provides common options shared across embed types:
    - title: Required for accessibility (WCAG 2.1 AA)
    - height: Embed height in pixels (0 = auto-detect)

    Subclasses add service-specific options.
    """

    title: str = ""
    height: int = 0  # 0 means auto-detect based on content type


class EmbedDirectiveBase(BengalDirective):
    """
    Abstract base class for external service embed directives.

    Provides shared functionality:
    - ID/URL validation via regex patterns
    - Standardized error rendering
    - Noscript fallback generation
    - Title accessibility validation

    Subclasses must define:
    - NAMES, TOKEN_TYPE, OPTIONS_CLASS (inherited from BengalDirective)
    - SERVICE_NAME: Human-readable service name for error messages
    - ID_PATTERN: Regex pattern for validating embed source
    - validate_source(): Service-specific validation logic
    """

    # Subclasses must define these
    SERVICE_NAME: ClassVar[str] = ""
    ID_PATTERN: ClassVar[re.Pattern[str]]

    @abstractmethod
    def validate_source(self, source: str) -> str | None:
        """
        Validate the embed source (ID or URL).

        Args:
            source: Source identifier from directive title

        Returns:
            Error message string if invalid, None if valid
        """
        ...

    def _render_error(self, error: str, reference: str) -> str:
        """Render standardized error block for this embed type."""
        base_class = f"{self.TOKEN_TYPE.replace('_', '-')}"
        return render_error_block(
            error=error,
            reference=reference,
            base_class=f"{base_class} embed-error",
            service=self.SERVICE_NAME,
        )

    def _render_noscript(self, url: str, title: str) -> str:
        """Render noscript fallback for this embed type."""
        return render_noscript_fallback(url, title, self.SERVICE_NAME)

    def _validate_title(self, source: str, title: str) -> DirectiveToken | None:
        """
        Validate that title is provided (accessibility requirement).

        Returns error token if title is missing, None if valid.
        """
        if not title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for {self.SERVICE_NAME} embed",
                    "reference": source,
                },
            )
        return None


# =============================================================================
# GitHub Gist Directive
# =============================================================================


@dataclass
class GistOptions(StyledOptions):
    """
    Options for GitHub Gist embed.

    Attributes:
        file: Specific file from gist to display
        css_class: Additional CSS classes (inherited from StyledOptions)

    Example:
        :::{gist} username/abc123def456789012345678901234567890
        :file: example.py
        :::

    """

    file: str = ""


class GistDirective(EmbedDirectiveBase):
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
    OPTIONS_CLASS: ClassVar[type[GistOptions]] = GistOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["gist"]
    SERVICE_NAME: ClassVar[str] = "Gist"

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
        options: GistOptions,
        content: str,
        children: list[dict[str, object]],
        state: MistuneBlockState,
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

    def render(self, renderer: DirectiveRenderer, text: str, **attrs: object) -> str:
        """Render gist embed to HTML."""
        error = attrs.get("error")
        if error:
            return self._render_error(str(error), str(attrs.get("gist_ref", "unknown")))

        gist_ref = str(attrs.get("gist_ref", ""))
        file = str(attrs.get("file", ""))
        css_class = str(attrs.get("css_class", ""))

        class_str = self.build_class_string("gist-embed", css_class)

        # Build script URL
        script_url = f"https://gist.github.com/{gist_ref}.js"
        if file:
            script_url += f"?file={self.escape_html(file)}"

        gist_url = f"https://gist.github.com/{gist_ref}"

        return (
            f'<div class="{class_str}">\n'
            f'  <script src="{script_url}"></script>\n'
            f"  {self._render_noscript(gist_url, gist_ref)}\n"
            f"</div>\n"
        )


# =============================================================================
# CodePen Directive
# =============================================================================


@dataclass
class CodePenOptions(EmbedOptionsBase):
    """
    Options for CodePen embed.

    Attributes:
        title: Required - Accessible title for iframe (inherited)
        height: Height in pixels (default: 300, inherited)
        default_tab: Tab to show - html, css, js, result (default: result)
        theme: Color theme - light, dark (default: dark)
        editable: Allow editing (default: false)
        preview: Show preview on load (default: true)
        css_class: Additional CSS classes (inherited)

    Example:
        :::{codepen} chriscoyier/pen/abc123
        :title: CSS Grid Example
        :default-tab: result
        :height: 400
        :::

    """

    height: int = 300  # Override default
    default_tab: str = "result"
    theme: str = "dark"
    editable: bool = False
    preview: bool = True

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "default-tab": "default_tab",
    }
    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "default_tab": ["html", "css", "js", "result"],
        "theme": ["light", "dark"],
    }


class CodePenDirective(EmbedDirectiveBase):
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
    OPTIONS_CLASS: ClassVar[type[CodePenOptions]] = CodePenOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["codepen"]
    SERVICE_NAME: ClassVar[str] = "CodePen"

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
        options: CodePenOptions,
        content: str,
        children: list[dict[str, object]],
        state: MistuneBlockState,
    ) -> DirectiveToken:
        """Build CodePen embed token."""
        pen_ref = title.strip()

        # Validate pen reference
        error = self.validate_source(pen_ref)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "reference": pen_ref},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(pen_ref, options.title)
        if title_error:
            return title_error

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

    def render(self, renderer: DirectiveRenderer, text: str, **attrs: object) -> str:
        """Render CodePen embed to HTML."""
        error = attrs.get("error")
        if error:
            return self._render_error(str(error), str(attrs.get("reference", "unknown")))

        username = str(attrs.get("username", ""))
        pen_id = str(attrs.get("pen_id", ""))
        title = str(attrs.get("title", "CodePen Embed"))
        default_tab = str(attrs.get("default_tab", "result"))
        height = attrs.get("height", 300)
        theme = str(attrs.get("theme", "dark"))
        editable = attrs.get("editable", False)
        preview = attrs.get("preview", True)
        css_class = str(attrs.get("css_class", ""))

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
            f"  {self._render_noscript(pen_url, safe_title)}\n"
            f"</div>\n"
        )


# =============================================================================
# CodeSandbox Directive
# =============================================================================


@dataclass
class CodeSandboxOptions(EmbedOptionsBase):
    """
    Options for CodeSandbox embed.

    Attributes:
        title: Required - Accessible title for iframe (inherited)
        height: Height in pixels (default: 500, inherited)
        module: File to show initially
        view: Display mode - editor, preview, split (default: split)
        fontsize: Editor font size (default: 14)
        hidenavigation: Hide file navigation (default: false)
        theme: Color theme - light, dark (default: dark)
        css_class: Additional CSS classes (inherited)

    Example:
        :::{codesandbox} new
        :title: React Example
        :module: /src/App.js
        :view: preview
        :::

    """

    height: int = 500  # Override default
    module: str = ""
    view: str = "split"
    fontsize: int = 14
    hidenavigation: bool = False
    theme: str = "dark"

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "view": ["editor", "preview", "split"],
        "theme": ["light", "dark"],
    }


class CodeSandboxDirective(EmbedDirectiveBase):
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
    OPTIONS_CLASS: ClassVar[type[CodeSandboxOptions]] = CodeSandboxOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["codesandbox"]
    SERVICE_NAME: ClassVar[str] = "CodeSandbox"

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
        options: CodeSandboxOptions,
        content: str,
        children: list[dict[str, object]],
        state: MistuneBlockState,
    ) -> DirectiveToken:
        """Build CodeSandbox embed token."""
        sandbox_id = title.strip()

        # Validate sandbox ID
        error = self.validate_source(sandbox_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "reference": sandbox_id},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(sandbox_id, options.title)
        if title_error:
            return title_error

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

    def render(self, renderer: DirectiveRenderer, text: str, **attrs: object) -> str:
        """Render CodeSandbox embed to HTML."""
        error = attrs.get("error")
        if error:
            return self._render_error(str(error), str(attrs.get("reference", "unknown")))

        sandbox_id = str(attrs.get("sandbox_id", ""))
        title = str(attrs.get("title", "CodeSandbox Embed"))
        module = str(attrs.get("module", ""))
        view = str(attrs.get("view", "split"))
        height = attrs.get("height", 500)
        fontsize = attrs.get("fontsize", 14)
        hidenavigation = attrs.get("hidenavigation", False)
        theme = str(attrs.get("theme", "dark"))
        css_class = str(attrs.get("css_class", ""))

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
            f"  {self._render_noscript(sandbox_url, safe_title)}\n"
            f"</div>\n"
        )


# =============================================================================
# StackBlitz Directive
# =============================================================================


@dataclass
class StackBlitzOptions(EmbedOptionsBase):
    """
    Options for StackBlitz embed.

    Attributes:
        title: Required - Accessible title for iframe (inherited)
        height: Height in pixels (default: 500, inherited)
        file: File to show initially
        view: Display mode - editor, preview, both (default: both)
        hidenavigation: Hide file navigation (default: false)
        hidedevtools: Hide dev tools panel (default: false)
        css_class: Additional CSS classes (inherited)

    Example:
        :::{stackblitz} angular-quickstart
        :title: Angular Demo
        :file: src/app.component.ts
        :view: preview
        :::

    """

    height: int = 500  # Override default
    file: str = ""
    view: str = "both"
    hidenavigation: bool = False
    hidedevtools: bool = False

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "view": ["editor", "preview", "both"],
    }


class StackBlitzDirective(EmbedDirectiveBase):
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
    OPTIONS_CLASS: ClassVar[type[StackBlitzOptions]] = StackBlitzOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["stackblitz"]
    SERVICE_NAME: ClassVar[str] = "StackBlitz"

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
        options: StackBlitzOptions,
        content: str,
        children: list[dict[str, object]],
        state: MistuneBlockState,
    ) -> DirectiveToken:
        """Build StackBlitz embed token."""
        project_id = title.strip()

        # Validate project ID
        error = self.validate_source(project_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "reference": project_id},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(project_id, options.title)
        if title_error:
            return title_error

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

    def render(self, renderer: DirectiveRenderer, text: str, **attrs: object) -> str:
        """Render StackBlitz embed to HTML."""
        error = attrs.get("error")
        if error:
            return self._render_error(str(error), str(attrs.get("reference", "unknown")))

        project_id = str(attrs.get("project_id", ""))
        title = str(attrs.get("title", "StackBlitz Embed"))
        file = str(attrs.get("file", ""))
        view = str(attrs.get("view", "both"))
        height = attrs.get("height", 500)
        hidenavigation = attrs.get("hidenavigation", False)
        hidedevtools = attrs.get("hidedevtools", False)
        css_class = str(attrs.get("css_class", ""))

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
            f"  {self._render_noscript(project_url, safe_title)}\n"
            f"</div>\n"
        )


# =============================================================================
# Spotify Directive
# =============================================================================


@dataclass
class SpotifyOptions(EmbedOptionsBase):
    """
    Options for Spotify embed.

    Attributes:
        title: Required - Accessible title for iframe (inherited)
        height: Embed height in pixels (0 = auto-detect, inherited)
        type: Content type - track, album, playlist, episode, show (default: track)
        theme: Color theme - 0 for dark, 1 for light (default: 0)
        css_class: Additional CSS classes (inherited)

    Example:
        :::{spotify} 4iV5W9uYEdYUVa79Axb7Rh
        :title: Bohemian Rhapsody by Queen
        :type: track
        :::

    """

    type: str = "track"
    theme: int = 0  # 0 = dark, 1 = light

    _allowed_values: ClassVar[dict[str, list[str | int]]] = {
        "type": ["track", "album", "playlist", "episode", "show", "artist"],
        "theme": [0, 1],
    }


class SpotifyDirective(EmbedDirectiveBase):
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
    OPTIONS_CLASS: ClassVar[type[SpotifyOptions]] = SpotifyOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["spotify"]
    SERVICE_NAME: ClassVar[str] = "Spotify"

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
        options: SpotifyOptions,
        content: str,
        children: list[dict[str, object]],
        state: MistuneBlockState,
    ) -> DirectiveToken:
        """Build Spotify embed token."""
        spotify_id = title.strip()

        # Validate Spotify ID
        error = self.validate_source(spotify_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "reference": spotify_id},
            )

        # Validate title (accessibility requirement)
        title_error = self._validate_title(spotify_id, options.title)
        if title_error:
            return title_error

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

    def render(self, renderer: DirectiveRenderer, text: str, **attrs: object) -> str:
        """Render Spotify embed to HTML."""
        error = attrs.get("error")
        if error:
            return self._render_error(str(error), str(attrs.get("reference", "unknown")))

        spotify_id = str(attrs.get("spotify_id", ""))
        title = str(attrs.get("title", "Spotify Embed"))
        content_type = str(attrs.get("content_type", "track"))
        height = attrs.get("height", 152)
        theme = attrs.get("theme", 0)
        css_class = str(attrs.get("css_class", ""))

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
            f"  {self._render_noscript(spotify_url, safe_title)}\n"
            f"</div>\n"
        )


# =============================================================================
# SoundCloud Directive
# =============================================================================


@dataclass
class SoundCloudOptions(EmbedOptionsBase):
    """
    Options for SoundCloud embed.

    Attributes:
        title: Required - Accessible title for iframe (inherited)
        height: Embed height in pixels (0 = auto-detect, inherited)
        type: Content type - track or playlist (default: track)
        color: Accent color hex code without # (default: ff5500 - SoundCloud orange)
        autoplay: Auto-start playback (default: false)
        hide_related: Hide related tracks (default: false)
        show_comments: Show comments (default: true)
        show_user: Show uploader info (default: true)
        show_reposts: Show reposts (default: false)
        visual: Use visual player (larger artwork) (default: false for tracks)
        css_class: Additional CSS classes (inherited)

    Example:
        :::{soundcloud} artistname/track-title
        :title: Track Title by Artist
        :::

        # Also accepts full URLs:
        :::{soundcloud} https://soundcloud.com/artistname/track-title
        :title: Track Title by Artist
        :::

    """

    type: str = "track"
    color: str = "ff5500"  # SoundCloud orange
    autoplay: bool = False
    hide_related: bool = False
    show_comments: bool = True
    show_user: bool = True
    show_reposts: bool = False
    visual: bool = False

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "type": ["track", "playlist"],
    }


class SoundCloudDirective(EmbedDirectiveBase):
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
    OPTIONS_CLASS: ClassVar[type[SoundCloudOptions]] = SoundCloudOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["soundcloud"]
    SERVICE_NAME: ClassVar[str] = "SoundCloud"

    # SoundCloud URL path: username/track-name (alphanumeric, hyphens, underscores)
    # Matches: user-604227447/some-track-name or artistname/track-title
    URL_PATH_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?$"
    )
    # Alias for EmbedDirectiveBase compatibility
    ID_PATTERN: ClassVar[re.Pattern[str]] = URL_PATH_PATTERN

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

    # Use canonical implementation from bengal.directives.utils
    _clean_path = staticmethod(clean_soundcloud_path)

    def parse_directive(
        self,
        title: str,
        options: SoundCloudOptions,
        content: str,
        children: list[dict[str, object]],
        state: MistuneBlockState,
    ) -> DirectiveToken:
        """Build SoundCloud embed token."""
        url_path = title.strip()

        # Validate SoundCloud URL path
        error = self.validate_source(url_path)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "reference": url_path},
            )

        # Clean the path
        cleaned_path = self._clean_path(url_path)

        # Validate title (accessibility requirement)
        title_error = self._validate_title(cleaned_path, options.title)
        if title_error:
            return title_error

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

    def render(self, renderer: DirectiveRenderer, text: str, **attrs: object) -> str:
        """Render SoundCloud embed to HTML."""
        error = attrs.get("error")
        if error:
            return self._render_error(str(error), str(attrs.get("reference", "unknown")))

        url_path = str(attrs.get("url_path", ""))
        title = str(attrs.get("title", "SoundCloud Embed"))
        height = attrs.get("height", 166)
        color = str(attrs.get("color", "ff5500"))
        autoplay = attrs.get("autoplay", False)
        hide_related = attrs.get("hide_related", False)
        show_comments = attrs.get("show_comments", True)
        show_user = attrs.get("show_user", True)
        show_reposts = attrs.get("show_reposts", False)
        visual = attrs.get("visual", False)
        css_class = str(attrs.get("css_class", ""))

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
            f"  {self._render_noscript(soundcloud_url, safe_title)}\n"
            f"</div>\n"
        )
