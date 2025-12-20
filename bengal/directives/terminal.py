"""
Terminal recording embed directives for Bengal.

Provides directives for embedding terminal recordings:
- Asciinema: Terminal session recordings with playback controls

Architecture:
    AsciinemaDirective extends BengalDirective with asciinema.org
    integration and fallback for users without JavaScript.

Security:
    Recording IDs are validated via regex to prevent injection.
    Noscript fallbacks provide accessible link to recording.

Accessibility:
    Title is required for WCAG compliance. ARIA role="img" used
    for semantic meaning. Recommend providing transcript for
    complex recordings.

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
    "AsciinemaDirective",
    "AsciinemaOptions",
]


# =============================================================================
# Asciinema Directive
# =============================================================================


@dataclass
class AsciinemaOptions(DirectiveOptions):
    """
    Options for Asciinema terminal recording embed.

    Attributes:
        title: Required - Accessible title for recording (ARIA label)
        cols: Terminal columns (default: 80)
        rows: Terminal rows (default: 24)
        speed: Playback speed multiplier (default: 1.0)
        autoplay: Auto-start playback (default: false)
        loop: Loop playback (default: false)
        theme: Color theme name (default: asciinema)
        poster: Preview frame - npt:MM:SS or data:text/plain,... (default: npt:0:0)
        idle_time_limit: Max idle time between frames in seconds
        start_at: Start playback at specific time (seconds or MM:SS)
        css_class: Additional CSS classes

    Example:
        :::{asciinema} 590029
        :title: Installation Demo
        :cols: 80
        :rows: 24
        :speed: 1.5
        :autoplay: true
        :::
    """

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

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "idle-time-limit": "idle_time_limit",
        "start-at": "start_at",
    }


class AsciinemaDirective(BengalDirective):
    """
    Asciinema terminal recording embed directive.

    Embeds asciinema.org terminal recordings with customizable playback options.
    Uses official script-based embed with noscript fallback.

    Syntax:
        :::{asciinema} recording_id
        :title: Installation Demo
        :cols: 80
        :rows: 24
        :speed: 1.5
        :autoplay: true
        :::

    Options:
        :title: (required) Accessible title for recording
        :cols: Terminal columns (default: 80)
        :rows: Terminal rows (default: 24)
        :speed: Playback speed multiplier (default: 1.0)
        :autoplay: Auto-start playback (default: false)
        :loop: Loop playback (default: false)
        :theme: Color theme name (default: asciinema)
        :poster: Preview frame - npt:MM:SS (default: npt:0:0)
        :idle-time-limit: Max idle time between frames in seconds
        :start-at: Start playback at specific time
        :class: Additional CSS classes

    Output:
        <figure class="asciinema-embed" role="img" aria-label="...">
          <script id="asciicast-..." src="https://asciinema.org/a/....js"
                  async data-cols="80" data-rows="24" ...></script>
          <noscript>
            <a href="https://asciinema.org/a/...">View recording: ...</a>
          </noscript>
        </figure>

    Security:
        - Recording ID validated (numeric only)
        - All data attributes properly escaped

    Accessibility:
        - ARIA role="img" with aria-label
        - Noscript fallback with link
        - Recommend providing transcript for complex recordings
    """

    NAMES: ClassVar[list[str]] = ["asciinema"]
    TOKEN_TYPE: ClassVar[str] = "asciinema_embed"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = AsciinemaOptions
    DIRECTIVE_NAMES: ClassVar[list[str]] = ["asciinema"]

    # Asciinema recording ID: numeric only
    ID_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^\d+$")

    def validate_source(self, recording_id: str) -> str | None:
        """Validate Asciinema recording ID (numeric only)."""
        if not self.ID_PATTERN.match(recording_id):
            return f"Invalid Asciinema recording ID: {recording_id!r}. Expected numeric ID."
        return None

    def parse_directive(
        self,
        title: str,
        options: AsciinemaOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        """Build Asciinema embed token."""
        recording_id = title.strip()

        # Validate recording ID
        error = self.validate_source(recording_id)
        if error:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={"error": error, "recording_id": recording_id},
            )

        # Validate title (accessibility requirement)
        if not options.title:
            return DirectiveToken(
                type=self.TOKEN_TYPE,
                attrs={
                    "error": f"Missing required :title: option for Asciinema embed. Recording: {recording_id}",
                    "recording_id": recording_id,
                },
            )

        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "recording_id": recording_id,
                "title": options.title,
                "cols": options.cols,
                "rows": options.rows,
                "speed": options.speed,
                "autoplay": options.autoplay,
                "loop": options.loop,
                "theme": options.theme,
                "poster": options.poster,
                "idle_time_limit": options.idle_time_limit,
                "start_at": options.start_at,
                "css_class": options.css_class,
            },
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render Asciinema embed to HTML."""
        error = attrs.get("error")
        if error:
            recording_id = attrs.get("recording_id", "unknown")
            return (
                f'<div class="terminal-embed asciinema terminal-error">\n'
                f'  <p class="error">Asciinema Error: {self.escape_html(error)}</p>\n'
                f"  <p>Recording ID: <code>{self.escape_html(recording_id)}</code></p>\n"
                f"</div>\n"
            )

        recording_id = attrs.get("recording_id", "")
        title = attrs.get("title", "Terminal Recording")
        cols = attrs.get("cols", 80)
        rows = attrs.get("rows", 24)
        speed = attrs.get("speed", 1.0)
        autoplay = attrs.get("autoplay", False)
        loop = attrs.get("loop", False)
        theme = attrs.get("theme", "asciinema")
        poster = attrs.get("poster", "npt:0:0")
        idle_time_limit = attrs.get("idle_time_limit")
        start_at = attrs.get("start_at", "")
        css_class = attrs.get("css_class", "")

        class_str = self.build_class_string("terminal-embed", "asciinema", css_class)
        safe_title = self.escape_html(title)

        # Build data attributes for script tag
        data_attrs = [
            f'data-cols="{cols}"',
            f'data-rows="{rows}"',
            f'data-theme="{self.escape_html(theme)}"',
        ]

        if speed != 1.0:
            data_attrs.append(f'data-speed="{speed}"')
        if autoplay:
            data_attrs.append('data-autoplay="true"')
        if loop:
            data_attrs.append('data-loop="true"')
        if poster:
            data_attrs.append(f'data-poster="{self.escape_html(poster)}"')
        if idle_time_limit is not None:
            data_attrs.append(f'data-idle-time-limit="{idle_time_limit}"')
        if start_at:
            data_attrs.append(f'data-start-at="{self.escape_html(start_at)}"')

        data_attrs_str = " ".join(data_attrs)

        script_url = f"https://asciinema.org/a/{recording_id}.js"
        recording_url = f"https://asciinema.org/a/{recording_id}"

        return (
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
