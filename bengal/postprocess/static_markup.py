"""Build-time static markup enhancements for the default theme (#538)."""

from __future__ import annotations

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
_PRE_CODE_RE = re.compile(
    r"(<pre[^>]*>\s*<code[^>]*>)([\s\S]*?)(</code>\s*</pre>)",
    re.IGNORECASE,
)
_A_HREF_RE = re.compile(
    r"<a(\s[^>]*?href=(['\"])(.*?)\2)([^>]*)>",
    re.IGNORECASE | re.DOTALL,
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


def _language_from_code_tag(open_tag: str) -> str:
    match = _LANG_RE.search(open_tag)
    if not match:
        return ""
    return (match.group(1) or match.group(2) or "").upper()


def _wrap_pre_code(match: re.Match[str]) -> str:
    full = match.group(0)
    if "code-copy-button" in full:
        return full
    open_pre = match.group(1)
    lang = _language_from_code_tag(open_pre)
    lang_label = f'<span class="code-language">{lang}</span>' if lang else "<span></span>"
    header = f'<div class="code-header-inline">{lang_label}{_WRAP_BUTTON}{_COPY_BUTTON}</div>'
    return (
        f'<div class="code-block-wrapper">{open_pre}{match.group(2)}{match.group(3)}{header}</div>'
    )


def inject_code_copy_chrome(html: str) -> str:
    """Wrap standalone pre>code blocks with build-time copy chrome."""
    if not html or "<pre" not in html:
        return html

    def replacer(match: re.Match[str]) -> str:
        window = html[max(0, match.start() - 120) : match.start()]
        if "code-block-wrapper" in window:
            return match.group(0)
        return _wrap_pre_code(match)

    return _PRE_CODE_RE.sub(replacer, html)


def enhance_theme_markup(html: str, *, base_url: str = "") -> str:
    """Apply default-theme static markup enhancements."""
    html = mark_external_links(html, base_url)
    html = inject_code_copy_chrome(html)
    return html
