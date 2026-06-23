"""Build-time static markup enhancements for the default theme (#538, #542)."""

from __future__ import annotations

import html as html_mod
import re
from urllib.parse import urlparse

from bengal.utils.primitives.code import default_frame_for_language

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
    r'(<div(?=[^>]*\bdata-collapsible="(open|closed)")(?=[^>]*\bclass="[^"]*\b(?:code-block-wrapper|rosettes|highlight)\b[^"]*")[^>]*>)'
    r"([\s\S]*?)"
    r"(</div>)",
    re.IGNORECASE,
)
_TITLE_BEFORE_RE = re.compile(
    r'<div class="code-block-title">([^<]*)</div>\s*$',
    re.IGNORECASE,
)
_DEDUPE_EDITOR_TITLE_RE = re.compile(
    r'(<div class="code-block-titled">\s*)<div class="code-block-title">[^<]*</div>\s*'
    r'(<div class="code-block-wrapper[^"]*\bcode-block-frame--editor\b[^"]*")',
    re.IGNORECASE,
)
_ENHANCED_CODE_MARKER = "data-bengal-code-chrome"
_HIGHLIGHT_ROOT_CLASSES = frozenset({"rosettes", "highlight"})


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


def _parse_div_attrs(open_div: str) -> dict[str, str]:
    attrs_str = open_div[4:-1] if open_div.startswith("<div") else open_div
    return {match.group(1): match.group(2) for match in _ATTR_RE.finditer(attrs_str)}


def _highlight_root_classes(class_value: str) -> list[str]:
    return [
        token
        for token in class_value.split()
        if token in _HIGHLIGHT_ROOT_CLASSES or token.startswith("highlight-")
    ]


def _is_inside_enhanced_code_block(html: str, pos: int) -> bool:
    """Return True when ``pos`` is inside an already-enhanced code block."""
    div_depth = 0
    enhanced_depth = 0
    for match in re.finditer(r"<div[^>]*>|</div>", html[:pos], re.IGNORECASE):
        tag = match.group(0)
        if tag.startswith("</div"):
            div_depth = max(0, div_depth - 1)
            if enhanced_depth > div_depth:
                enhanced_depth = div_depth
            continue
        div_depth += 1
        if _ENHANCED_CODE_MARKER in tag:
            enhanced_depth = div_depth
    return enhanced_depth > 0


def _merge_wrapper_opening(
    wrapper_html: str,
    *,
    extra_classes: list[str],
    data_attrs: dict[str, str],
) -> str:
    def repl(match: re.Match[str]) -> str:
        attrs = match.group(1)
        classes = (_attr_value(attrs, "class") or "code-block-wrapper").split()
        for class_name in extra_classes:
            if class_name not in classes:
                classes.append(class_name)
        if "code-block-wrapper" not in classes:
            classes.insert(0, "code-block-wrapper")

        merged_attrs = re.sub(
            r'\bclass="[^"]*"',
            f'class="{" ".join(classes)}"',
            attrs,
            count=1,
        )
        if 'class="' not in merged_attrs:
            merged_attrs = f' class="{" ".join(classes)}"{merged_attrs}'

        for key, value in data_attrs.items():
            if key.startswith("data-") and not _attr_value(merged_attrs, key):
                merged_attrs += f' {key}="{html_mod.escape(value, quote=True)}"'

        if _ENHANCED_CODE_MARKER not in merged_attrs:
            merged_attrs += f' {_ENHANCED_CODE_MARKER}="true"'
        return f"<div{merged_attrs}>"

    return re.sub(r"^<div([^>]*)>", repl, wrapper_html, count=1)


def _absorb_highlight_root(open_div: str, wrapper_html: str) -> str:
    """Fold rosettes/highlight root attrs into the single chrome wrapper."""
    outer = _parse_div_attrs(open_div)
    extra_classes = _highlight_root_classes(outer.get("class", ""))
    data_attrs = {key: value for key, value in outer.items() if key.startswith("data-")}
    return _merge_wrapper_opening(wrapper_html, extra_classes=extra_classes, data_attrs=data_attrs)


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


def _build_toolbar(lang: str, *, overlay: bool = False, show_lang: bool = True) -> str:
    lang_label = f'<span class="code-language">{lang}</span>' if lang and show_lang else ""
    overlay_classes = " code-block-toolbar--overlay code-header-inline" if overlay else ""
    return (
        f'<div class="code-block-toolbar{overlay_classes}">'
        f"{lang_label}{_WRAP_BUTTON}{_COPY_BUTTON}"
        "</div>"
    )


def _frame_dots() -> str:
    return (
        '<div class="code-block-frame-dots" aria-hidden="true">'
        '<span class="code-block-frame-dot"></span>'
        '<span class="code-block-frame-dot"></span>'
        '<span class="code-block-frame-dot"></span>'
        "</div>"
    )


def _editor_tab_label(filename: str, lang: str) -> str:
    if filename:
        return filename
    if lang:
        return lang.lower()
    return "untitled"


def _build_editor_tab(filename: str, lang: str) -> str:
    label = html_mod.escape(_editor_tab_label(filename, lang))
    return (
        '<div class="code-block-tabs" role="presentation">'
        f'<div class="code-block-tab code-block-tab--active">'
        f'<span class="code-block-tab__icon" aria-hidden="true"></span>'
        f'<span class="code-block-tab__label">{label}</span>'
        "</div>"
        "</div>"
    )


def _extract_title_from_context(html: str, pos: int) -> str:
    window = html[max(0, pos - 500) : pos]
    if "code-block-titled" not in window:
        return ""
    match = _TITLE_BEFORE_RE.search(window)
    if not match:
        return ""
    return html_mod.unescape(match.group(1).strip())


def _resolve_editor_filename(div_attrs: str, html: str, pos: int) -> str:
    return _attr_value(div_attrs, "data-title") or _extract_title_from_context(html, pos)


def _build_frame_chrome(frame: str, lang: str, *, filename: str = "") -> str:
    if frame == "terminal":
        toolbar = _build_toolbar(lang, overlay=False)
        return (
            f'<div class="code-block-chrome code-block-chrome--{frame}">'
            f"{_frame_dots()}{toolbar}</div>"
        )

    tab = _build_editor_tab(filename, lang)
    toolbar = _build_toolbar(lang, overlay=False, show_lang=not filename)
    return (
        f'<div class="code-block-chrome code-block-chrome--editor">'
        f"{_frame_dots()}{tab}{toolbar}</div>"
    )


def _resolve_frame(
    div_attrs: str,
    *,
    in_titled_block: bool = False,
    lang: str = "",
) -> str:
    explicit = _attr_value(div_attrs, "data-frame")
    if explicit:
        return explicit
    if in_titled_block:
        return "editor"
    data_lang = _attr_value(div_attrs, "data-language") or lang
    return default_frame_for_language(data_lang) or ""


def _wrapper_classes(
    div_attrs: str,
    *,
    in_titled_block: bool = False,
    lang: str = "",
) -> str:
    classes = ["code-block-wrapper"]
    frame = _resolve_frame(div_attrs, in_titled_block=in_titled_block, lang=lang)
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
    source_html: str = "",
    source_pos: int = 0,
) -> str:
    lang = _attr_value(div_attrs, "data-language").upper() or _language_from_code_tag(open_pre)
    annotations = _parse_annotations(_attr_value(div_attrs, "data-annotate"))
    code_html = _apply_line_annotations(code_html, annotations)

    if _attr_value(div_attrs, "data-linenos") == "true":
        body = _wrap_with_linenos(open_pre, code_html, close_pre)
    else:
        body = f"{open_pre}{code_html}{close_pre}"

    wrapper_class = _wrapper_classes(
        div_attrs,
        in_titled_block=in_titled_block,
        lang=lang.lower(),
    )
    frame = _resolve_frame(div_attrs, in_titled_block=in_titled_block, lang=lang.lower())

    if frame:
        filename = (
            _resolve_editor_filename(div_attrs, source_html, source_pos)
            if frame == "editor"
            else ""
        )
        chrome = _build_frame_chrome(frame, lang, filename=filename)
        return (
            f'<div class="{wrapper_class}" {_ENHANCED_CODE_MARKER}="true">'
            f'{chrome}<div class="code-block-body">{body}</div></div>'
        )

    toolbar = _build_toolbar(lang, overlay=True)
    return f'<div class="{wrapper_class}" {_ENHANCED_CODE_MARKER}="true">{body}{toolbar}</div>'


def _enhance_highlighted_block(match: re.Match[str]) -> str:
    open_div, inner, _close_div = match.group(1), match.group(2), match.group(3)
    if _ENHANCED_CODE_MARKER in open_div or "code-block-wrapper" in open_div:
        return match.group(0)
    if "code-block-wrapper" in inner or "code-copy-button" in inner:
        return match.group(0)

    pre_match = _PRE_CODE_RE.search(inner)
    if not pre_match:
        return match.group(0)

    div_attrs = open_div[4:-1]
    wrapped = _wrap_pre_code(
        pre_match.group(1),
        pre_match.group(2),
        pre_match.group(3),
        div_attrs=div_attrs,
        in_titled_block="code-block-titled" in match.string[: match.start()],
        source_html=match.string,
        source_pos=match.start(),
    )
    return _absorb_highlight_root(open_div, wrapped)


def _wrap_plain_pre_code(match: re.Match[str]) -> str:
    full = match.group(0)
    if "code-copy-button" in full:
        return full
    if _is_inside_enhanced_code_block(match.string, match.start()):
        return full

    window = match.string[max(0, match.start() - 400) : match.start()]
    in_titled = "code-block-titled" in window
    return _wrap_pre_code(
        match.group(1),
        match.group(2),
        match.group(3),
        in_titled_block=in_titled,
        source_html=match.string,
        source_pos=match.start(),
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
    html = _DEDUPE_EDITOR_TITLE_RE.sub(r"\1\2", html)
    html = _wrap_collapsible_blocks(html)
    return html


def enhance_theme_markup(html: str, *, base_url: str = "") -> str:
    """Apply default-theme static markup enhancements."""
    html = mark_external_links(html, base_url)
    html = inject_code_copy_chrome(html)
    return html
