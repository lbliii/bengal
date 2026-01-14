"""Miscellaneous directives for documentation.

Provides:
- example-label: Lightweight semantic label for example sections
- build: Build badge showing build duration/status
- asciinema: Terminal recording embeds from asciinema.org

Thread Safety:
Stateless handlers. Safe for concurrent use across threads.

HTML Output:
Matches Bengal's miscellaneous directives exactly for parity.

"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from html import escape as html_escape
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from patitas.directives.options import DirectiveOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder

__all__ = [
    "ExampleLabelDirective",
    "BuildDirective",
    "AsciinemaDirective",
]


# =============================================================================
# Site Context Protocol (for build directive)
# =============================================================================


class SiteContext(Protocol):
    """Protocol for site context required by build directive."""

    config: dict[str, Any]
    output_dir: str | None
    current_language: str | None


SiteContextGetter = Callable[[], tuple[SiteContext | None, Any | None]]


# =============================================================================
# Example Label Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class ExampleLabelOptions(DirectiveOptions):
    """Options for example-label directive."""

    css_class: str = ""
    prefix: str = "Example"
    no_prefix: bool = False


class ExampleLabelDirective:
    """
    Lightweight semantic label for example sections.
    
    Syntax:
        :::{example-label} Basic Usage
        :::
    
        :::{example-label} API Call
        :prefix: Demo
        :::
    
        :::{example-label} Simple
        :no-prefix:
        :::
    
    Output:
        <p class="example-label" role="heading" aria-level="6">
          <span class="example-label-prefix">Example:</span> Basic Usage
        </p>
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("example-label",)
    token_type: ClassVar[str] = "example_label"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[ExampleLabelOptions]] = ExampleLabelOptions

    def parse(
        self,
        name: str,
        title: str | None,
        options: ExampleLabelOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build example-label AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),  # Example labels never have children
        )

    def render(
        self,
        node: Directive[ExampleLabelOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render example label to HTML."""
        opts = node.options
        title = node.title or ""

        css_class = opts.css_class
        prefix = opts.prefix
        no_prefix = opts.no_prefix

        # Build class list
        classes = ["example-label"]
        if css_class:
            classes.append(css_class)
        class_str = " ".join(classes)

        # Build title with optional prefix
        if no_prefix or not title:
            # No prefix: just show the title (or prefix as title if no title)
            display_text = title if title else prefix
            title_html = html_escape(display_text)
        else:
            # With prefix: "Example: Title"
            title_html = (
                f'<span class="example-label-prefix">{html_escape(prefix)}:</span> '
                f"{html_escape(title)}"
            )

        sb.append(f'<p class="{class_str}" role="heading" aria-level="6">{title_html}</p>\n')


# =============================================================================
# Build Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class BuildOptions(DirectiveOptions):
    """Options for build directive."""

    json: bool = False
    inline: bool = False
    align: str = ""
    css_class: str = ""
    alt: str = "Built in badge"
    dir_name: str = "bengal"


class BuildDirective:
    """
    Build badge directive for displaying build status/duration.
    
    Embeds HTML that references generated build badge (SVG) and optionally
    links to build stats JSON. The actual badge is generated at build finalization.
    
    Syntax:
        :::{build}
        :::
    
        :::{build}
        :json: true
        :class: mt-3
        :::
    
    Options:
        :json: Link to build.json (default: false)
        :inline: Render inline (default: false)
        :align: Block alignment - left/center/right
        :class: Additional CSS classes
        :alt: Image alt text (default: "Built in badge")
        :dir: Directory name for artifacts (default: "bengal")
    
    Output:
        <span class="bengal-build-badge">
          <img class="bengal-build-badge__img" src="/bengal/build.svg" alt="...">
        </span>
    
    Requires:
        Site context for URL resolution.
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("build",)
    token_type: ClassVar[str] = "build"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[BuildOptions]] = BuildOptions

    # Site context getter - set by renderer
    get_site_context: SiteContextGetter | None = None

    def parse(
        self,
        name: str,
        title: str | None,
        options: BuildOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build build-badge AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=options,  # Pass typed options directly
            children=(),
        )

    def render(
        self,
        node: Directive[BuildOptions],
        rendered_children: str,
        sb: StringBuilder,
        *,
        get_site_context: SiteContextGetter | None = None,
    ) -> None:
        """Render build badge to HTML."""
        opts = node.options

        dir_name = opts.dir_name.strip("/") or "bengal"
        link_json = opts.json
        inline = opts.inline
        align = opts.align.strip().lower()
        css_class = opts.css_class.strip()
        alt = opts.alt or "Built in badge"

        # Get site context for URL resolution
        context_getter = get_site_context or self.get_site_context
        if context_getter:
            site, page = context_getter()
        else:
            site, page = None, None

        svg_url, json_url = self._resolve_build_artifact_urls(site, page, dir_name)

        # Build wrapper classes
        wrapper_classes = ["bengal-build-badge"]
        if inline:
            wrapper_classes.append("bengal-build-badge--inline")
        elif align in ("left", "center", "right"):
            wrapper_classes.append(f"bengal-build-badge--{align}")
        if css_class:
            wrapper_classes.extend(css_class.split())
        class_attr = html_escape(" ".join(wrapper_classes))

        # Build styles
        wrapper_style, img_style = self._resolve_layout_styles(inline, align)
        wrapper_style_attr = f' style="{html_escape(wrapper_style)}"' if wrapper_style else ""
        img_style_attr = f' style="{html_escape(img_style)}"' if img_style else ""

        img_html = (
            f'<img class="bengal-build-badge__img" src="{html_escape(svg_url)}" '
            f'alt="{html_escape(alt)}"{img_style_attr}>'
        )

        if link_json:
            sb.append(
                f'<a class="{class_attr}" href="{html_escape(json_url)}" '
                f'aria-label="Build stats"{wrapper_style_attr}>{img_html}</a>'
            )
        else:
            sb.append(f'<span class="{class_attr}"{wrapper_style_attr}>{img_html}</span>')

    def _resolve_layout_styles(self, inline: bool, align: str) -> tuple[str, str]:
        """Return (wrapper_style, img_style) for layout."""
        if not inline and align not in ("left", "center", "right"):
            return "", ""

        if inline:
            return (
                "display:inline-flex;align-items:center;vertical-align:middle;",
                "display:inline-block;margin:0;vertical-align:middle;",
            )

        return (
            f"display:block;text-align:{align};",
            "display:inline-block;margin:0;",
        )

    def _resolve_build_artifact_urls(
        self, site: SiteContext | None, page: Any, dir_name: str
    ) -> tuple[str, str]:
        """Resolve URLs for build artifacts."""
        baseurl = ""
        prefix = ""

        if site is not None:
            config = site.config or {}
            baseurl = str(config.get("baseurl", "") or "").rstrip("/")

            i18n = config.get("i18n", {}) or {}
            if i18n.get("strategy") == "prefix":
                current_lang = site.current_language or i18n.get("default_language", "en")
                default_lang = i18n.get("default_language", "en")
                default_in_subdir = bool(i18n.get("default_in_subdir", False))
                if default_in_subdir or str(current_lang) != str(default_lang):
                    prefix = f"/{current_lang}"

        # Absolute paths (typical for HTTP deployments)
        path_root = f"{prefix}/{dir_name}".replace("//", "/")
        svg_path = f"{path_root}/build.svg"
        json_path = f"{path_root}/build.json"

        if baseurl:
            return f"{baseurl}{svg_path}", f"{baseurl}{json_path}"
        return svg_path, json_path


# =============================================================================
# Asciinema Directive
# =============================================================================


@dataclass(frozen=True, slots=True)
class AsciinemaOptions(DirectiveOptions):
    """Options for Asciinema terminal recording embed."""

    title: str = ""
    cols: int = 80
    rows: int = 24
    speed: float = 1.0
    autoplay: bool = False
    loop: bool = False
    theme: str = "asciinema"
    poster: str = "npt:0:0"
    idle_time_limit: float | None = None
    start_at: str = ""
    css_class: str = ""

    # Computed attributes (populated during parse)
    recording_id: str = ""
    is_local_file: bool = False  # True if input is a local .cast file path
    error: str = ""


class AsciinemaDirective:
    """
    Asciinema terminal recording embed directive.
    
    Supports both remote (asciinema.org) and local (.cast file) recordings.
    
    Remote recording syntax:
        :::{asciinema} 590029
        :title: Installation Demo
        :cols: 80
        :rows: 24
        :speed: 1.5
        :autoplay: true
        :::
    
    Local file syntax:
        :::{asciinema} recordings/demo.cast
        :title: Local Demo
        :cols: 80
        :speed: 1.5
        :::
    
    Input:
        - Numeric ID (e.g., "590029") for asciinema.org recordings
        - File path ending in .cast (e.g., "recordings/demo.cast") for local files
          Local paths are resolved relative to site root and should be in static/ directory
    
    Options:
        :title: (required) Accessible title for recording
        :cols: Terminal columns (default: 80)
        :rows: Terminal rows (default: 24)
        :speed: Playback speed multiplier (default: 1.0)
        :autoplay: Auto-start playback (default: false)
        :loop: Loop playback (default: false)
        :theme: Color theme name (default: asciinema)
        :poster: Preview frame - npt:MM:SS (default: npt:0:0)
        :idle-time-limit: Max idle time between frames
        :start-at: Start playback at specific time
        :class: Additional CSS classes
    
    Output:
        Remote: <figure> with script tag loading from asciinema.org
        Local: <figure> with asciinema player initialized with local .cast file
    
    Security:
        Recording ID validated (numeric for remote, .cast extension for local).
    
    Accessibility:
        ARIA role="img" with aria-label. Noscript fallback.
    
    Thread Safety:
        Stateless handler. Safe for concurrent use.
        
    """

    names: ClassVar[tuple[str, ...]] = ("asciinema",)
    token_type: ClassVar[str] = "asciinema_embed"
    contract: ClassVar[DirectiveContract | None] = None
    options_class: ClassVar[type[AsciinemaOptions]] = AsciinemaOptions

    # Asciinema recording ID: numeric only (for remote recordings)
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^\d+$")
    # Local file pattern: ends with .cast, may be relative or absolute path
    LOCAL_FILE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r".*\.cast$", re.IGNORECASE)

    def parse(
        self,
        name: str,
        title: str | None,
        options: AsciinemaOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive:
        """Build Asciinema embed AST node.

        Accepts either:
        - Numeric ID (e.g., "590029") for asciinema.org recordings
        - File path (e.g., "recordings/demo.cast") for local recordings
        """
        recording_id = title.strip() if title else ""

        # Determine if input is a local file or remote ID
        is_local_file = bool(recording_id and self.LOCAL_FILE_PATTERN.match(recording_id))
        is_remote_id = bool(recording_id and self.ID_PATTERN.match(recording_id))

        # Validate input
        error = ""
        if not recording_id:
            error = "Missing recording ID or file path for Asciinema embed"
        elif not is_local_file and not is_remote_id:
            error = (
                f"Invalid Asciinema input: {recording_id!r}. "
                f"Expected numeric ID (e.g., '590029') or file path ending in .cast (e.g., 'recordings/demo.cast')."
            )
        elif not options.title:
            error = (
                f"Missing required :title: option for Asciinema embed. Recording: {recording_id}"
            )

        # Store computed values
        computed_opts = replace(
            options,
            recording_id=recording_id,
            is_local_file=is_local_file,
            error=error,
        )

        return Directive(
            location=location,
            name=name,
            title=title,
            options=computed_opts,
            children=(),
        )

    def render(
        self,
        node: Directive[AsciinemaOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render Asciinema embed to HTML.

        Supports both remote (asciinema.org) and local (.cast file) recordings.
        """
        opts = node.options

        error = getattr(opts, "error", "")
        recording_id = getattr(opts, "recording_id", "")
        is_local_file = getattr(opts, "is_local_file", False)

        if error:
            sb.append(
                f'<div class="terminal-embed asciinema terminal-error">\n'
                f'  <p class="error">Asciinema Error: {html_escape(error)}</p>\n'
                f"  <p>Recording: <code>{html_escape(recording_id or 'unknown')}</code></p>\n"
                f"</div>\n"
            )
            return

        title = opts.title or "Terminal Recording"
        cols = opts.cols
        rows = opts.rows
        speed = opts.speed
        autoplay = opts.autoplay
        loop = opts.loop
        theme = opts.theme
        poster = opts.poster
        idle_time_limit = opts.idle_time_limit
        start_at = opts.start_at
        css_class = opts.css_class

        # Build class list
        classes = ["terminal-embed", "asciinema"]
        if css_class:
            classes.extend(css_class.split())
        class_str = " ".join(classes)

        safe_title = html_escape(title)

        # Build data attributes
        data_attrs = [
            f'data-cols="{cols}"',
            f'data-rows="{rows}"',
            f'data-theme="{html_escape(theme)}"',
        ]

        if speed != 1.0:
            data_attrs.append(f'data-speed="{speed}"')
        if autoplay:
            data_attrs.append('data-autoplay="true"')
        if loop:
            data_attrs.append('data-loop="true"')
        if poster:
            data_attrs.append(f'data-poster="{html_escape(poster)}"')
        if idle_time_limit is not None:
            data_attrs.append(f'data-idle-time-limit="{idle_time_limit}"')
        if start_at:
            data_attrs.append(f'data-start-at="{html_escape(start_at)}"')

        data_attrs_str = " ".join(data_attrs)

        # Generate different HTML for local vs remote recordings
        if is_local_file:
            # Local file: normalize path (ensure it starts with / if relative)
            file_path = recording_id
            if not file_path.startswith(("/", "http://", "https://")):
                # Relative path - assume it's in static/ directory
                file_path = f"/{file_path.lstrip('/')}"

            # Generate unique ID for this recording
            recording_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            element_id = f"asciicast-local-{recording_hash}"

            # For local files, use asciinema player library from CDN
            # Load asciinema player script and initialize with local file
            # Using jsdelivr CDN for asciinema-player which supports local files
            player_config = {
                "cols": cols,
                "rows": rows,
                "theme": theme,
                "speed": speed,
                "autoplay": autoplay,
                "loop": loop,
                "poster": poster,
            }
            if idle_time_limit is not None:
                player_config["idleTimeLimit"] = idle_time_limit
            if start_at:
                player_config["startAt"] = start_at

            # Build config JSON string
            config_items = []
            for key, value in player_config.items():
                if isinstance(value, bool):
                    config_items.append(f'"{key}": {str(value).lower()}')
                elif isinstance(value, (int, float)):
                    config_items.append(f'"{key}": {value}')
                elif value is None:
                    continue
                else:
                    config_items.append(f'"{key}": {repr(str(value))}')
            config_json = "{" + ", ".join(config_items) + "}"

            sb.append(
                f'<figure class="{class_str}" role="img" aria-label="{safe_title}">\n'
                f'  <div id="{element_id}"></div>\n'
                f'  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3/dist/bundle/asciinema-player.css">\n'
                f'  <script src="https://cdn.jsdelivr.net/npm/asciinema-player@3/dist/bundle/asciinema-player.min.js"></script>\n'
                f"  <script>\n"
                f"    (function() {{\n"
                f"      function initPlayer() {{\n"
                f"        if (window.AsciinemaPlayer) {{\n"
                f"          AsciinemaPlayer.create(\n"
                f'            "{html_escape(file_path)}",\n'
                f'            document.getElementById("{element_id}"),\n'
                f"            {config_json}\n"
                f"          );\n"
                f"        }}\n"
                f"      }}\n"
                f'      if (document.readyState === "loading") {{\n'
                f'        document.addEventListener("DOMContentLoaded", initPlayer);\n'
                f"      }} else {{\n"
                f"        initPlayer();\n"
                f"      }}\n"
                f"    }})();\n"
                f"  </script>\n"
                f"  <noscript>\n"
                f'    <a href="{html_escape(file_path)}">View recording: {safe_title}</a>\n'
                f"  </noscript>\n"
                f"</figure>\n"
            )
        else:
            # Remote recording: use asciinema.org script
            script_url = f"https://asciinema.org/a/{recording_id}.js"
            recording_url = f"https://asciinema.org/a/{recording_id}"

            sb.append(
                f'<figure class="{class_str}" role="img" aria-label="{safe_title}">\n'
                f"  <script\n"
                f'    id="asciicast-{recording_id}"\n'
                f'    src="{script_url}"\n'
                f"    async\n"
                f"    {data_attrs_str}\n"
                f"  ></script>\n"
                f"  <noscript>\n"
                f'    <a href="{recording_url}">View recording: {safe_title}</a>\n'
                f"  </noscript>\n"
                f"</figure>\n"
            )
