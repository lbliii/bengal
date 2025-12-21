"""
Developer tool embed directives for Bengal.

Provides directives for embedding code playgrounds and developer tools:
- GitHub Gists
- CodePen
- CodeSandbox
- StackBlitz

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
