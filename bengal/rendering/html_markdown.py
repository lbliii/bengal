"""Helpers for deriving Markdown-like agent mirrors from rendered HTML."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

_IGNORED_TAGS = {"script", "style", "svg", "button", "nav", "aside"}


def rendered_html_to_markdown(html: str) -> str:
    """Convert the primary rendered content area from a full HTML page to Markdown."""
    content_html = extract_primary_content_html(html)
    if not content_html:
        return ""
    return html_fragment_to_markdown(content_html)


def extract_primary_content_html(html: str) -> str:
    """Extract the content-bearing HTML fragment from a rendered page."""
    if not html:
        return ""

    article = _extract_balanced_tag(
        html,
        "article",
        r'<article\b[^>]*class="[^"]*\bprose\b[^"]*"[^>]*>',
    )
    if article:
        return article

    docs_content = _extract_balanced_tag(
        html,
        "div",
        r'<div\b[^>]*class="[^"]*\bdocs-content\b[^"]*"[^>]*>',
    )
    if docs_content:
        return docs_content

    main = _extract_balanced_tag(
        html,
        "main",
        r'<main\b[^>]*(?:id="main-content"[^>]*)?>',
    )
    return main


def html_fragment_to_markdown(html: str) -> str:
    """Convert a content HTML fragment into compact Markdown-like text."""
    if not html:
        return ""

    parser = _MarkdownHTMLParser()
    parser.feed(html)
    parser.close()
    return _normalize_markdown(parser.markdown())


def _extract_balanced_tag(html: str, tag: str, start_pattern: str) -> str:
    start = re.search(start_pattern, html, re.IGNORECASE)
    if not start:
        return ""

    tag_pattern = re.compile(rf"</?{tag}\b[^>]*>", re.IGNORECASE)
    depth = 1
    pos = start.end()
    for match in tag_pattern.finditer(html, pos):
        token = match.group(0)
        if token.startswith("</"):
            depth -= 1
            if depth == 0:
                return html[start.end() : match.start()].strip()
        elif not token.endswith("/>"):
            depth += 1
    return ""


class _MarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._links: list[str] = []
        self._pre_parts: list[str] = []
        self._in_pre = False
        self._skip_depth = 0

    def markdown(self) -> str:
        return "".join(self._parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._skip_depth:
            if tag in _IGNORED_TAGS:
                self._skip_depth += 1
            return
        if tag in _IGNORED_TAGS:
            self._skip_depth = 1
            return
        if tag == "pre":
            self._newline()
            self._in_pre = True
            self._pre_parts = []
            return
        if tag == "code" and not self._in_pre:
            self._parts.append("`")
            return
        if tag in {"p", "div", "section", "article", "header", "footer", "ul", "ol"}:
            self._newline()
            return
        if tag in {"br", "hr"}:
            self._newline()
            return
        if tag == "li":
            self._newline()
            self._parts.append("- ")
            return
        if re.fullmatch(r"h[1-6]", tag):
            self._newline()
            self._parts.append("#" * int(tag[1]) + " ")
            return
        if tag == "a":
            href = dict(attrs).get("href") or ""
            self._links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_depth:
            if tag in _IGNORED_TAGS:
                self._skip_depth -= 1
            return
        if tag == "pre":
            code = "".join(self._pre_parts).strip("\n")
            if code:
                self._parts.append(f"\n```\n{code}\n```\n")
            self._in_pre = False
            self._pre_parts = []
            return
        if tag == "code" and not self._in_pre:
            self._parts.append("`")
            return
        if tag == "a":
            href = self._links.pop() if self._links else ""
            if href:
                self._parts.append(f" ({href})")
            return
        if tag in {"p", "div", "section", "article", "header", "footer", "li", "ul", "ol"}:
            self._newline()
            return
        if re.fullmatch(r"h[1-6]", tag):
            self._newline()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_pre:
            self._pre_parts.append(unescape(data))
        else:
            self._parts.append(unescape(data))

    def _newline(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")


def _normalize_markdown(markdown: str) -> str:
    lines: list[str] = []
    blank_count = 0
    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped == "```":
            in_fence = not in_fence
            lines.append(stripped)
            blank_count = 0
            continue
        if in_fence:
            lines.append(line.rstrip())
            continue
        if not stripped:
            blank_count += 1
            if blank_count <= 1:
                lines.append("")
            continue
        blank_count = 0
        lines.append(re.sub(r"[ \t]+", " ", stripped))
    return "\n".join(lines).strip()
