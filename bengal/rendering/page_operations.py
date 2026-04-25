"""Rendering-side helpers for operations exposed on pages.

The concrete ``Page`` type lives in ``bengal.core`` and should remain a passive
domain object. Operations that understand rendered HTML, shortcode syntax, or
link extraction belong here; ``Page`` keeps only small compatibility shims for
template and third-party code that already calls methods such as
``page.extract_links()``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

# Compiled patterns for link extraction (used per-page in extract_links)
_FENCE_4PLUS = re.compile(r"`{4,}[^\n]*\n.*?`{4,}", re.DOTALL)
_FENCE_3 = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]+`")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_HTML_HREF = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\']')
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_BROKEN_REF = re.compile(r'<span\s+class="broken-ref"[^>]*data-ref="([^"]+)"')


class PageOperationTarget(Protocol):
    """Structural page surface needed by rendering operations."""

    html_content: str | None
    links: list[str]
    source_path: Path

    @property
    def _source(self) -> str:
        """Raw markdown source content."""
        ...


def extract_links(page: PageOperationTarget, plugin_links: list[str] | None = None) -> list[str]:
    """
    Extract all links from page content.

    When plugin_links is provided (from CrossReferencePlugin during parse), it
    is used as the single source of truth for wikilinks. Otherwise extraction
    falls back to ``html_content`` or regex over source markdown.

    Content inside fenced code blocks and inline code spans is ignored to avoid
    false positives from documentation examples.
    """
    content_without_code = _strip_code_for_link_extraction(page._source)

    markdown_links = _MARKDOWN_LINK.findall(content_without_code)
    html_links = _HTML_HREF.findall(content_without_code)

    if plugin_links is not None:
        wikilink_urls = plugin_links
        page.links = [url for _, url in markdown_links] + html_links + wikilink_urls
    elif page.html_content:
        page.links = extract_all_links_from_html(page.html_content)
    else:
        wikilink_urls = extract_wikilinks_from_source(content_without_code)
        page.links = [url for _, url in markdown_links] + html_links + wikilink_urls

    _merge_directive_links(page, plugin_links=plugin_links)
    return page.links


def has_shortcode(page: PageOperationTarget, name: str) -> bool:
    """Return True if page source content uses the named shortcode."""
    from bengal.rendering.shortcodes import has_shortcode as _has_shortcode

    return _has_shortcode(page, name)


def extract_all_links_from_html(html_content: str | None) -> list[str]:
    """Extract href and broken-reference links from rendered HTML."""
    if not html_content:
        return []
    urls: list[str] = []
    urls.extend(_HTML_HREF.findall(html_content))
    urls.extend(match.group(1) for match in _BROKEN_REF.finditer(html_content))
    return urls


def extract_wikilinks_from_source(content: str) -> list[str]:
    """Extract wikilinks from source via regex as a last-resort fallback."""
    wikilink_urls: list[str] = []
    for path in _WIKILINK.findall(content):
        path = path.strip()
        if path.startswith("ext:"):
            continue
        # Fix edge cases: [[!id]] -> #id, [[#heading]] -> #heading, [[path\|label]] -> path
        if path.startswith("!"):
            url = f"#{path[1:]}"
        elif path.startswith("#"):
            url = path
        else:
            path = path.replace("\\|", "|").split("|")[0].strip()
            url = f"/{path}" if not path.startswith("/") else path
        wikilink_urls.append(url)
    return wikilink_urls


def _strip_code_for_link_extraction(content: str) -> str:
    """Remove Markdown code spans and fences before regex link extraction."""
    content_without_code = _FENCE_4PLUS.sub("", content)
    content_without_code = _FENCE_3.sub("", content_without_code)
    return _INLINE_CODE.sub("", content_without_code)


def _merge_directive_links(page: PageOperationTarget, *, plugin_links: list[str] | None) -> None:
    """Merge directive-collected links without duplicating existing entries."""
    collected = getattr(page, "_directive_links", None)
    if collected:
        existing = set(page.links)
        for link in collected:
            if link not in existing:
                page.links.append(link)
                existing.add(link)
    elif page.html_content and plugin_links is not None:
        directive_links = _HTML_HREF.findall(page.html_content)
        if directive_links:
            existing = set(page.links)
            for link in directive_links:
                if link not in existing:
                    page.links.append(link)
                    existing.add(link)
