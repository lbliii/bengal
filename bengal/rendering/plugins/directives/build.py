"""
Build badge directive for Mistune (MyST-style).

Renders a small badge that points at the build-time artifacts generated during
build finalization:
    - `/bengal/build.svg`
    - `/bengal/build.json`

This directive intentionally does NOT attempt to compute the build duration at
render-time. The final build duration is only known after rendering completes.
Instead, it embeds a stable URL that will resolve once the build artifacts are
written.

Syntax:

```markdown
:::{build}
:::

:::{build}
:json: true
:class: mt-3
:::
```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from bengal.rendering.plugins.directives.base import BengalDirective
from bengal.rendering.plugins.directives.options import DirectiveOptions
from bengal.rendering.plugins.directives.tokens import DirectiveToken
from bengal.rendering.plugins.directives.utils import escape_html

__all__ = ["BuildDirective", "BuildOptions"]


@dataclass
class BuildOptions(DirectiveOptions):
    """
    Options for build directive.

    Attributes:
        json: If True, wrap the badge in a link to build.json.
        css_class: Additional CSS classes on wrapper.
        alt: Image alt text.
        dir_name: Directory name used for artifacts (default: "bengal").
    """

    json: bool = False
    css_class: str = ""
    alt: str = "Built in badge"
    dir_name: str = "bengal"

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "dir": "dir_name",
    }


class BuildDirective(BengalDirective):
    """
    Build badge directive.

    Emits HTML that references the generated build badge (SVG) and optionally
    links to the build stats JSON.
    """

    NAMES: ClassVar[list[str]] = ["build"]
    TOKEN_TYPE: ClassVar[str] = "build"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = BuildOptions

    DIRECTIVE_NAMES: ClassVar[list[str]] = ["build"]

    def parse_directive(
        self,
        title: str,
        options: BuildOptions,  # type: ignore[override]
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        # This directive does not use title/content; it is purely a renderer hook.
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "json": bool(options.json),
                "css_class": options.css_class or "",
                "alt": options.alt or "Built in badge",
                "dir_name": options.dir_name or "bengal",
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        site = getattr(renderer, "_site", None)
        dir_name = str(attrs.get("dir_name") or "bengal").strip("/") or "bengal"
        link_json = bool(attrs.get("json", False))
        css_class = str(attrs.get("css_class") or "").strip()
        alt = str(attrs.get("alt") or "Built in badge")

        svg_url, json_url = _resolve_build_artifact_urls(site, dir_name=dir_name)

        wrapper_classes = ["bengal-build-badge"]
        if css_class:
            wrapper_classes.extend(css_class.split())
        class_attr = escape_html(" ".join(wrapper_classes))

        img_html = (
            f'<img class="bengal-build-badge__img" src="{escape_html(svg_url)}" '
            f'alt="{escape_html(alt)}" loading="lazy">'
        )

        if link_json:
            return (
                f'<a class="{class_attr}" href="{escape_html(json_url)}" '
                f'aria-label="Build stats">{img_html}</a>'
            )

        return f'<span class="{class_attr}">{img_html}</span>'


def _resolve_build_artifact_urls(site: Any, *, dir_name: str) -> tuple[str, str]:
    """
    Resolve URLs for build artifacts, considering baseurl and i18n prefix strategy.
    """
    baseurl = ""
    prefix = ""

    if site is not None:
        config = getattr(site, "config", {}) or {}
        baseurl = str(config.get("baseurl", "") or "").rstrip("/")

        i18n = config.get("i18n", {}) or {}
        if i18n.get("strategy") == "prefix":
            current_lang = getattr(site, "current_language", None) or i18n.get(
                "default_language", "en"
            )
            default_lang = i18n.get("default_language", "en")
            default_in_subdir = bool(i18n.get("default_in_subdir", False))
            if default_in_subdir or str(current_lang) != str(default_lang):
                prefix = f"/{current_lang}"

    # Ensure a leading slash for path part
    path_root = f"{prefix}/{dir_name}".replace("//", "/")
    svg_path = f"{path_root}/build.svg"
    json_path = f"{path_root}/build.json"

    if baseurl:
        return f"{baseurl}{svg_path}", f"{baseurl}{json_path}"
    return svg_path, json_path
