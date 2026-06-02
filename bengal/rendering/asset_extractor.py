"""Asset extraction utilities for tracking page-to-asset dependencies.

Extracts references to assets (images, stylesheets, scripts, fonts) from
rendered HTML to populate the AssetDependencyMap cache. This enables
incremental builds to discover only the assets needed for changed pages.

Asset types tracked:
- Images: <img src>, <picture> <source srcset>
- Stylesheets: <link href> with rel=stylesheet
- Scripts: <script src>
- Fonts: <link href> with rel=preload type=font
- Data URLs, IFrames, and other embedded resources

Implementation note
-------------------
``extract_assets_from_html`` is a hand-rolled single-pass scanner rather than a
``html.parser.HTMLParser`` subclass. On real builds this fallback runs on EVERY
page (block/fragment caching means the render-time ``AssetTracker`` is usually
empty), and the stdlib parser's per-tag method dispatch and incremental buffer
made it the single largest render cost (~24% of a cold build). The scanner
produces a byte-identical asset set to the old parser — it deliberately
replicates the parser's quirks (HTML-entity unescaping in attribute values,
comment and ``<script>``/``<style>`` CDATA skipping, whitespace-tolerant close
tags, last-wins duplicate attributes, and the empty-srcset-candidate abort) so
the per-page incremental dependency map is unchanged. ``AssetExtractorParser``
is retained below as the reference oracle that the parity test compares against.

The scanner is stateless and free-threading-safe: only module-level immutable
regexes are shared; every call uses a fresh local set.
"""

from __future__ import annotations

import html as _html
import re
from contextlib import suppress
from html.parser import HTMLParser

# @import url(...) inside <style> bodies. Reused verbatim from the old parser.
_IMPORT_RE = re.compile(r"@import\s+url\(['\"]?([^'\")\s]+)['\"]?\)")
# Tag name immediately after "<" (ASCII letter then name chars).
_TAGNAME_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9:_-]*")
# One attribute: name, optional = value (double-quoted, single-quoted, or bare).
_ATTR_RE = re.compile(r"""([^\s/>"'=]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+))?""")
# CDATA element close tags — html.parser tolerates surrounding whitespace.
_SCRIPT_CLOSE_RE = re.compile(r"</\s*script\s*>", re.IGNORECASE)
_STYLE_CLOSE_RE = re.compile(r"</\s*style\s*>", re.IGNORECASE)

# Asset-bearing tags this extractor inspects (mirrors AssetExtractorParser).
_INTERESTING_TAGS = frozenset({"img", "script", "link", "source", "iframe", "style"})


def _find_tag_end(s: str, i: int) -> int:
    """Index of the '>' that closes a start tag, skipping quoted attribute values.

    A '>' inside a quoted value does not end the tag (matches html.parser).
    Returns -1 if the tag is never closed.
    """
    n = len(s)
    while i < n:
        c = s[i]
        if c in "\"'":
            close = s.find(c, i + 1)
            if close < 0:
                return -1
            i = close + 1
        elif c == ">":
            return i
        else:
            i += 1
    return -1


def _parse_attrs(blob: str) -> dict[str, str | None]:
    """Parse a tag's attribute text into {lower_name: value}.

    Duplicate attributes keep the LAST value (dict semantics, matching the old
    ``dict(attrs)``). Quoted values are unquoted; HTML entities in values are
    unescaped, exactly as html.parser hands them to handle_starttag.
    """
    attrs: dict[str, str | None] = {}
    for m in _ATTR_RE.finditer(blob):
        name = m.group(1).lower()
        raw = m.group(2)
        if raw is None:
            attrs[name] = None
            continue
        if raw[:1] in "\"'":
            raw = raw[1:-1]
        attrs[name] = _html.unescape(raw)
    return attrs


def _extract_from_tag(tag: str, attrs: dict[str, str | None], assets: set[str]) -> None:
    """Apply the per-tag extraction rules (identical to AssetExtractorParser).

    Intra-tag order and the unguarded ``split()[0]`` are preserved so behavior —
    including the abort on an empty srcset candidate — matches the parser.
    """
    if tag == "img":
        if src := attrs.get("src"):
            assets.add(src)
        if srcset := attrs.get("srcset"):
            for item in srcset.split(","):
                url = item.strip().split()[0]
                if url:
                    assets.add(url)
    elif tag == "script":
        if src := attrs.get("src"):
            assets.add(src)
    elif tag == "link":
        if href := attrs.get("href"):
            rel_value = attrs.get("rel", "")
            if rel_value is not None:
                rel = rel_value.lower()
                if "stylesheet" in rel or "preload" in rel or "prefetch" in rel:
                    assets.add(href)
    elif tag == "source":
        if srcset := attrs.get("srcset"):
            for item in srcset.split(","):
                url = item.strip().split()[0]
                if url:
                    assets.add(url)
        if src := attrs.get("src"):
            assets.add(src)
    elif tag == "iframe":
        if src := attrs.get("src"):
            assets.add(src)


def _scan(s: str, assets: set[str]) -> None:
    """Single forward pass collecting asset references into ``assets``."""
    i, n = 0, len(s)
    while i < n:
        lt = s.find("<", i)
        if lt < 0:
            return
        # Comments (incl. conditional comments) — skip to "-->", nothing inside.
        if s.startswith("<!--", lt):
            # Abrupt-closing empty comments <!--> and <!---> (HTML5 comment-start /
            # comment-start-dash states) close immediately; html.parser then resumes
            # parsing the following markup, so the scanner must too.
            if s.startswith("<!-->", lt):
                i = lt + 5
                continue
            if s.startswith("<!--->", lt):
                i = lt + 6
                continue
            end = s.find("-->", lt + 4)
            i = n if end < 0 else end + 3
            continue
        # CDATA section.
        if s.startswith("<![CDATA[", lt):
            end = s.find("]]>", lt + 9)
            i = n if end < 0 else end + 3
            continue
        # Declarations (<!doctype) and processing instructions (<?).
        if s.startswith("<!", lt) or s.startswith("<?", lt):
            end = s.find(">", lt + 2)
            i = n if end < 0 else end + 1
            continue
        # End tags.
        if s.startswith("</", lt):
            end = s.find(">", lt + 2)
            i = n if end < 0 else end + 1
            continue
        # Start tag: read the name.
        name_match = _TAGNAME_RE.match(s, lt + 1)
        if not name_match:
            i = lt + 1
            continue
        tag = name_match.group(0).lower()
        tag_end = _find_tag_end(s, name_match.end())
        if tag_end < 0:
            return
        # <script>/<style> bodies are CDATA: tags inside are NOT parsed. <script>
        # still contributes its own src; <style> still contributes @import url(...)
        # from its body (matching the parser's handle_starttag/handle_data).
        if tag == "script":
            if src := _parse_attrs(s[name_match.end() : tag_end]).get("src"):
                assets.add(src)
            close = _SCRIPT_CLOSE_RE.search(s, tag_end + 1)
            i = close.end() if close else n
            continue
        if tag == "style":
            close = _STYLE_CLOSE_RE.search(s, tag_end + 1)
            body_end = close.start() if close else n
            for im in _IMPORT_RE.finditer(s[tag_end + 1 : body_end]):
                assets.add(im.group(1))
            i = close.end() if close else n
            continue
        if tag in _INTERESTING_TAGS:
            _extract_from_tag(tag, _parse_attrs(s[name_match.end() : tag_end]), assets)
        i = tag_end + 1


def extract_assets_from_html(html_content: str) -> set[str]:
    """Extract all asset references from rendered HTML.

    Args:
        html_content: Rendered HTML content

    Returns:
        Set of asset URLs/paths referenced in the HTML

    Example:
            >>> html = '<img src="/images/logo.png" /><script src="/js/app.js"></script>'
            >>> assets = extract_assets_from_html(html)
            >>> assert "/images/logo.png" in assets
            >>> assert "/js/app.js" in assets

    """
    if not html_content:
        return set()

    assets: set[str] = set()
    # Match the old parser's tolerant feed(): malformed HTML (incl. the empty
    # srcset-candidate abort) degrades to whatever was collected before the error.
    with suppress(Exception):
        _scan(html_content, assets)
    return {url.strip() for url in assets if url and url.strip()}


class AssetExtractorParser(HTMLParser):
    """Reference HTML parser for asset extraction (parity oracle for tests).

    Retained as the behavioral specification that ``extract_assets_from_html``'s
    fast scanner is validated against; not used on the production hot path.
    """

    def __init__(self) -> None:
        """Initialize the asset extractor parser."""
        super().__init__()
        self.assets: set[str] = set()
        self.in_style_tag = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Extract asset references from opening tags."""
        tag = tag.lower()
        attrs_dict = dict(attrs) if attrs else {}

        if tag == "img":
            if src := attrs_dict.get("src"):
                self.assets.add(src)
            if srcset := attrs_dict.get("srcset"):
                for item in srcset.split(","):
                    url = item.strip().split()[0]
                    if url:
                        self.assets.add(url)
        elif tag == "script":
            if src := attrs_dict.get("src"):
                self.assets.add(src)
        elif tag == "link":
            if href := attrs_dict.get("href"):
                rel_value = attrs_dict.get("rel", "")
                if rel_value is not None:
                    rel = rel_value.lower()
                    if "stylesheet" in rel or "preload" in rel or "prefetch" in rel:
                        self.assets.add(href)
        elif tag == "source":
            if srcset := attrs_dict.get("srcset"):
                for item in srcset.split(","):
                    url = item.strip().split()[0]
                    if url:
                        self.assets.add(url)
            if src := attrs_dict.get("src"):
                self.assets.add(src)
        elif tag == "iframe":
            if src := attrs_dict.get("src"):
                self.assets.add(src)
        elif tag == "style":
            self.in_style_tag = True

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags."""
        if tag.lower() == "style":
            self.in_style_tag = False

    def handle_data(self, data: str) -> None:
        """Extract @import URLs from style tag content."""
        if self.in_style_tag:
            for match in _IMPORT_RE.finditer(data):
                url = match.group(1)
                if url:
                    self.assets.add(url)

    def feed(self, data: str) -> AssetExtractorParser:  # type: ignore[override]
        """Parse HTML and return self for chaining."""
        with suppress(Exception):
            super().feed(data)
        return self

    def get_assets(self) -> set[str]:
        """Get all extracted asset URLs (stripped, non-empty)."""
        return {url.strip() for url in self.assets if url and url.strip()}
