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
from pathlib import Path
from typing import Any, ClassVar

from bengal.directives.base import BengalDirective
from bengal.directives.options import DirectiveOptions
from bengal.directives.tokens import DirectiveToken
from bengal.directives.utils import escape_html

__all__ = ["BuildDirective", "BuildOptions"]


@dataclass
class BuildOptions(DirectiveOptions):
    """
    Options for build directive.

    Attributes:
        json: If True, wrap the badge in a link to build.json.
        inline: If True, render as inline content (useful inside sentences).
        align: Optional alignment for block rendering: left | center | right.
        css_class: Additional CSS classes on wrapper.
        alt: Image alt text.
        dir_name: Directory name used for artifacts (default: "bengal").
    """

    json: bool = False
    inline: bool = False
    align: str = ""
    css_class: str = ""
    alt: str = "Built in badge"
    dir_name: str = "bengal"

    _field_aliases: ClassVar[dict[str, str]] = {
        "class": "css_class",
        "dir": "dir_name",
    }

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "align": ["", "left", "center", "right"],
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
                "inline": bool(options.inline),
                "align": options.align or "",
                "css_class": options.css_class or "",
                "alt": options.alt or "Built in badge",
                "dir_name": options.dir_name or "bengal",
            },
            children=[],
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        site = getattr(renderer, "_site", None)
        page = getattr(renderer, "_current_page", None)
        dir_name = str(attrs.get("dir_name") or "bengal").strip("/") or "bengal"
        link_json = bool(attrs.get("json", False))
        inline = bool(attrs.get("inline", False))
        align = str(attrs.get("align") or "").strip().lower()
        css_class = str(attrs.get("css_class") or "").strip()
        alt = str(attrs.get("alt") or "Built in badge")

        svg_url, json_url = _resolve_build_artifact_urls(site, page=page, dir_name=dir_name)

        wrapper_classes = ["bengal-build-badge"]
        if inline:
            wrapper_classes.append("bengal-build-badge--inline")
        elif align in ("left", "center", "right"):
            wrapper_classes.append(f"bengal-build-badge--{align}")
        if css_class:
            wrapper_classes.extend(css_class.split())
        class_attr = escape_html(" ".join(wrapper_classes))

        wrapper_style, img_style = _resolve_layout_styles(inline=inline, align=align)
        wrapper_style_attr = f' style="{escape_html(wrapper_style)}"' if wrapper_style else ""
        img_style_attr = f' style="{escape_html(img_style)}"' if img_style else ""

        img_html = (
            f'<img class="bengal-build-badge__img" src="{escape_html(svg_url)}" '
            f'alt="{escape_html(alt)}"{img_style_attr}>'
        )

        if link_json:
            return (
                f'<a class="{class_attr}" href="{escape_html(json_url)}" '
                f'aria-label="Build stats"{wrapper_style_attr}>{img_html}</a>'
            )

        return f'<span class="{class_attr}"{wrapper_style_attr}>{img_html}</span>'


def _resolve_layout_styles(*, inline: bool, align: str) -> tuple[str, str]:
    """
    Return (wrapper_style, img_style) to control placement.

    Why inline styles:
        The default theme applies global `img { display: block; margin: auto; }`
        rules inside prose. Inline styles let authors place the badge inline or
        align it without needing custom CSS.
    """
    # Default: preserve existing theme behavior (do not force styles).
    if not inline and align not in ("left", "center", "right"):
        return "", ""

    # For inline usage, override common prose image rules.
    if inline:
        return (
            "display:inline-flex;align-items:center;vertical-align:middle;",
            "display:inline-block;margin:0;vertical-align:middle;",
        )

    # Block alignment requested.
    return (
        f"display:block;text-align:{align};",
        "display:inline-block;margin:0;",
    )


def _resolve_build_artifact_urls(site: Any, *, page: Any, dir_name: str) -> tuple[str, str]:
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

    # Prefer relative URLs when we can compute them from the current page.
    #
    # This makes the badge work when users open built HTML via file:// (no server),
    # and it also works when served over HTTP (relative URLs resolve to the same files).
    if site is not None and page is not None:
        try:
            output_dir = getattr(site, "output_dir", None)
            page_output = getattr(page, "output_path", None)
            if output_dir and page_output:
                out_root = _resolve_output_root_for_page(site, page)
                svg_fs = Path(out_root) / dir_name / "build.svg"
                json_fs = Path(out_root) / dir_name / "build.json"
                from_dir = Path(page_output).parent
                svg_rel = svg_fs.relative_to(from_dir) if svg_fs.is_relative_to(from_dir) else None
                json_rel = (
                    json_fs.relative_to(from_dir) if json_fs.is_relative_to(from_dir) else None
                )
                if svg_rel is None or json_rel is None:
                    svg_rel_str = Path(
                        Path(svg_fs).as_posix()
                    )  # fallback, but should not happen in normal layouts
                    json_rel_str = Path(Path(json_fs).as_posix())
                else:
                    svg_rel_str = svg_rel.as_posix()
                    json_rel_str = json_rel.as_posix()
                # Ensure relative paths have ./ when needed
                if not svg_rel_str.startswith((".", "/")):
                    svg_rel_str = f"./{svg_rel_str}"
                if not json_rel_str.startswith((".", "/")):
                    json_rel_str = f"./{json_rel_str}"
                return svg_rel_str, json_rel_str
        except Exception:
            # Best-effort; fall back to absolute paths below.
            pass

    # Absolute paths fallback (good for dev server / typical HTTP deployments).
    path_root = f"{prefix}/{dir_name}".replace("//", "/")
    svg_path = f"{path_root}/build.svg"
    json_path = f"{path_root}/build.json"

    if baseurl:
        return f"{baseurl}{svg_path}", f"{baseurl}{json_path}"
    return svg_path, json_path


def _resolve_output_root_for_page(site: Any, page: Any) -> Path:
    """
    Determine which output root should be used for the current page.

    For i18n prefix strategy, pages may render into `output_dir/<lang>/...`.
    In that case, build artifacts may also exist under `output_dir/<lang>/bengal/...`.
    """
    output_dir = Path(site.output_dir)
    page_output = Path(page.output_path)

    config = getattr(site, "config", {}) or {}
    i18n = config.get("i18n", {}) or {}
    if i18n.get("strategy") != "prefix":
        return output_dir

    try:
        rel = page_output.relative_to(output_dir)
    except Exception:
        return output_dir

    if not rel.parts:
        return output_dir

    maybe_lang = rel.parts[0]
    default_lang = str(i18n.get("default_language", "en"))
    default_in_subdir = bool(i18n.get("default_in_subdir", False))

    # Only treat first segment as lang if it matches configured languages/default.
    lang_codes: set[str] = {default_lang}
    for entry in i18n.get("languages", []) or []:
        if isinstance(entry, str):
            lang_codes.add(entry)
        elif isinstance(entry, dict):
            code = entry.get("code") or entry.get("lang") or entry.get("language")
            if isinstance(code, str) and code:
                lang_codes.add(code)

    if maybe_lang in lang_codes:
        # Default language may or may not be in subdir based on config.
        if maybe_lang == default_lang and not default_in_subdir:
            return output_dir
        return output_dir / maybe_lang

    return output_dir
