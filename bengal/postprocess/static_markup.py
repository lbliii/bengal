"""Build-time static markup enhancements for the default theme (#538, #542)."""

from __future__ import annotations

import html as html_mod
import re
from urllib.parse import urlparse

_COPY_BUTTON = (
    '<button type="button" class="code-copy-button copy-success-burst" aria-label="Copy code to clipboard">'
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'
    "<span>Copy</span></button>"
)

_WRAP_BUTTON = (
    '<button type="button" class="code-wrap-toggle" aria-label="Enable word wrap" aria-pressed="false">'
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2"><path d="M4 6h16M4 12h10M4 18h16"/></svg>'
    "<span>Wrap</span></button>"
)

_LANG_RE = re.compile(r"language-(\w+)|hljs-(\w+)")
_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_PRE_CODE_RE = re.compile(
    r"(<pre[^>]*>\s*<code[^>]*>)([\s\S]*?)(</code>\s*</pre>)",
    re.IGNORECASE,
)
_A_HREF_RE = re.compile(
    r"<a(\s[^>]*?href=(['\"])(.*?)\2)([^>]*)>",
    re.IGNORECASE | re.DOTALL,
)
_HIGHLIGHTED_BLOCK_RE = re.compile(
    r'(<div(?=[^>]*\bclass="[^"]*\b(?:rosettes|highlight)\b[^"]*")[^>]*>)'
    r"([\s\S]*?)"
    r"(</div>)",
    re.IGNORECASE,
)
_COLLAPSIBLE_BLOCK_RE = re.compile(
    r'(<div(?=[^>]*\bdata-collapsible="(open|closed)")(?=[^>]*\bclass="[^"]*\b(?:rosettes|highlight)\b[^"]*")[^>]*>)'
    r"([\s\S]*?)"
    r"(</div>)",
    re.IGNORECASE,
)


def _normalize_origin(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        host = "localhost"
    scheme = parsed.scheme or "https"
    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def _is_external_href(href: str, site_origin: str) -> bool:
    href = (href or "").strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return False
    if href.startswith(("/", "./", "../")):
        return False
    parsed = urlparse(href)
    if not parsed.scheme:
        return False
    return _normalize_origin(href) != site_origin


def _merge_attrs(opening: str, additions: dict[str, str]) -> str:
    merged = opening
    for key, value in additions.items():
        if re.search(rf"\b{re.escape(key)}=", merged, re.IGNORECASE):
            continue
        merged += f' {key}="{value}"'
    return merged


def mark_external_links(html: str, base_url: str = "") -> str:
    """Add data-external + rel/target to off-site anchors."""
    if not html or "<a" not in html:
        return html

    site_origin = _normalize_origin(base_url or "https://localhost")

    def repl(match: re.Match[str]) -> str:
        href_attrs, _quote, href, tail = (
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )
        full = match.group(0)
        if "data-external" in full or not _is_external_href(href, site_origin):
            return full
        attrs = _merge_attrs(
            href_attrs + tail,
            {
                "data-external": "true",
                "rel": "noopener noreferrer",
                "target": "_blank",
            },
        )
        return f"<a{attrs}>"

    return _A_HREF_RE.sub(repl, html)


def _attr_value(attrs: str, name: str) -> str:
    for attr_match in _ATTR_RE.finditer(attrs):
        if attr_match.group(1) == name:
            return attr_match.group(2)
    return ""


def _language_from_code_tag(open_tag: str) -> str:
    match = _LANG_RE.search(open_tag)
    if not match:
        return ""
    return (match.group(1) or match.group(2) or "").upper()


def _parse_annotations(spec: str) -> dict[int, str]:
    annotations: dict[int, str] = {}
    if not spec:
        return annotations
    for part in spec.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        line_s, _, text = part.partition(":")
        try:
            annotations[int(line_s.strip())] = text.strip()
        except ValueError:
            continue
    return annotations


def _build_toolbar(lang: str) -> str:
    lang_label = f'<span class="code-language">{lang}</span>' if lang else "<span></span>"
    return f'<div class="code-header-inline">{lang_label}{_WRAP_BUTTON}{_COPY_BUTTON}</div>'


def _wrapper_classes(div_attrs: str, *, in_titled_block: bool = False) -> str:
    classes = ["code-block-wrapper"]
    frame = _attr_value(div_attrs, "data-frame")
    if not frame and in_titled_block:
        frame = "editor"
    if frame in {"terminal", "editor"}:
        classes.append(f"code-block-frame--{frame}")
    if _attr_value(div_attrs, "data-diff") == "true":
        classes.append("code-block--diff")
    return " ".join(classes)


def _split_code_lines(code_html: str) -> list[str]:
    lines = code_html.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _apply_line_annotations(code_html: str, annotations: dict[int, str]) -> str:
    if not annotations:
        return code_html

    lines = _split_code_lines(code_html)
    rendered: list[str] = []
    for index, line in enumerate(lines, start=1):
        note = annotations.get(index)
        if note:
            safe_note = html_mod.escape(note)
            rendered.append(
                f'<span class="code-line"><span class="code-line__content">{line}</span>'
                f'<span class="code-line-annotation">{safe_note}</span></span>'
            )
        else:
            rendered.append(line)
    trailing_newline = "\n" if code_html.endswith("\n") else ""
    return "\n".join(rendered) + trailing_newline


def _wrap_with_linenos(open_pre: str, code_html: str, close_pre: str) -> str:
    lines = _split_code_lines(code_html)
    if not lines:
        return f"{open_pre}{code_html}{close_pre}"

    numbers = "\n".join(str(index) for index in range(1, len(lines) + 1))
    return (
        '<div class="code-block-with-linenos">'
        f'<pre class="code-linenos" aria-hidden="true">{numbers}\n</pre>'
        f'<div class="code-block-scroll">{open_pre}{code_html}{close_pre}</div>'
        "</div>"
    )


def _wrap_pre_code(
    open_pre: str,
    code_html: str,
    close_pre: str,
    *,
    div_attrs: str = "",
    in_titled_block: bool = False,
) -> str:
    lang = _attr_value(div_attrs, "data-language").upper() or _language_from_code_tag(open_pre)
    annotations = _parse_annotations(_attr_value(div_attrs, "data-annotate"))
    code_html = _apply_line_annotations(code_html, annotations)

    if _attr_value(div_attrs, "data-linenos") == "true":
        body = _wrap_with_linenos(open_pre, code_html, close_pre)
    else:
        body = f"{open_pre}{code_html}{close_pre}"

    wrapper_class = _wrapper_classes(div_attrs, in_titled_block=in_titled_block)
    header = _build_toolbar(lang)
    frame = _attr_value(div_attrs, "data-frame") or ("editor" if in_titled_block else "")
    frame_header = ""
    if frame == "terminal":
        frame_header = (
            '<div class="code-block-frame-header code-block-frame-header--terminal" aria-hidden="true">'
            '<span class="code-block-frame-dot"></span>'
            '<span class="code-block-frame-dot"></span>'
            '<span class="code-block-frame-dot"></span>'
            "</div>"
        )
    elif frame == "editor":
        frame_header = '<div class="code-block-frame-header code-block-frame-header--editor" aria-hidden="true"></div>'

    return f'<div class="{wrapper_class}">{frame_header}{body}{header}</div>'


def _enhance_highlighted_block(match: re.Match[str]) -> str:
    open_div, inner, close_div = match.group(1), match.group(2), match.group(3)
    if "code-block-wrapper" in inner or "code-copy-button" in inner:
        return match.group(0)

    pre_match = _PRE_CODE_RE.search(inner)
    if not pre_match:
        return match.group(0)

    div_attrs = open_div[4:-1]  # strip <div ...>
    wrapped = _wrap_pre_code(
        pre_match.group(1),
        pre_match.group(2),
        pre_match.group(3),
        div_attrs=div_attrs,
        in_titled_block="code-block-titled" in match.string[: match.start()],
    )
    return f"{open_div}{wrapped}{close_div}"


def _wrap_plain_pre_code(match: re.Match[str]) -> str:
    full = match.group(0)
    if "code-copy-button" in full:
        return full
    window = match.string[max(0, match.start() - 160) : match.start()]
    if (
        "code-block-wrapper" in window
        or 'class="rosettes"' in window
        or 'class="highlight' in window
    ):
        return full
    in_titled = "code-block-titled" in window
    return _wrap_pre_code(
        match.group(1),
        match.group(2),
        match.group(3),
        in_titled_block=in_titled,
    )


def _wrap_collapsible_blocks(html: str) -> str:
    def repl(match: re.Match[str]) -> str:
        open_div, state, inner, close_div = (
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )
        lang = _attr_value(open_div, "data-language") or "Code"
        summary = html_mod.escape(lang.upper() if lang else "Code")
        open_attr = "" if state == "closed" else " open"
        return (
            f'<details class="code-block-collapsible"{open_attr}>'
            f'<summary class="code-block-collapsible__summary">{summary}</summary>'
            f"{open_div}{inner}{close_div}"
            "</details>"
        )

    return _COLLAPSIBLE_BLOCK_RE.sub(repl, html)


def inject_code_copy_chrome(html: str) -> str:
    """Wrap code blocks with premium build-time chrome (#542)."""
    if not html or "<pre" not in html:
        return html

    html = _HIGHLIGHTED_BLOCK_RE.sub(_enhance_highlighted_block, html)
    html = _PRE_CODE_RE.sub(_wrap_plain_pre_code, html)
    html = _wrap_collapsible_blocks(html)
    return html


def enhance_theme_markup(html: str, *, base_url: str = "") -> str:
    """Apply default-theme static markup enhancements."""
    html = mark_external_links(html, base_url)
    html = inject_code_copy_chrome(html)
    return html
