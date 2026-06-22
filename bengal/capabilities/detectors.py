"""
Content detectors for opt-in runtime capabilities (#571).

Each capability declares how to detect whether a page actually uses it.
Build-time resolution is: site owner enabled AND vendors provisioned AND
content detector matched → emit assets for that page.

See plan/rfc-capability-system.md Phase 1.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from bengal.capabilities.runtime import CAPABILITY_NAMES
from bengal.content.page_source import get_raw_source

if TYPE_CHECKING:
    from bengal.protocols import PageLike

# Rendered HTML markers (post-parse, most reliable when available).
_HTML_PATTERNS: dict[str, re.Pattern[str]] = {
    "mermaid": re.compile(r"""class=["']mermaid["']""", re.IGNORECASE),
    "katex": re.compile(
        r"""class=["'](?:math(?:-block)?)["']""",
        re.IGNORECASE,
    ),
}

# Raw markdown / source markers (discovery-time and pre-render fallback).
_SOURCE_PATTERNS: dict[str, re.Pattern[str]] = {
    "mermaid": re.compile(r"```mermaid|:::\{mermaid\}", re.IGNORECASE),
    "katex": re.compile(
        r"(?:\$\$[\s\S]+?\$\$|(?<!\$)\$(?!\$)[^\n$]+\$(?!\$)|"
        r"\{math\}`|:::\{math\}|\\begin\{)",
        re.IGNORECASE,
    ),
}


def detect_capabilities_in_html(html: str) -> dict[str, bool]:
    """Detect capability needs from rendered HTML."""
    needed = dict.fromkeys(CAPABILITY_NAMES, False)
    if not html:
        return needed

    for name, pattern in _HTML_PATTERNS.items():
        if pattern.search(html):
            needed[name] = True

    if needed["mermaid"]:
        needed["iconify"] = True

    return needed


def detect_capabilities_in_source(source: str) -> dict[str, bool]:
    """Detect capability needs from raw markdown/source."""
    needed = dict.fromkeys(CAPABILITY_NAMES, False)
    if not source:
        return needed

    for name, pattern in _SOURCE_PATTERNS.items():
        if pattern.search(source):
            needed[name] = True

    if needed["mermaid"]:
        needed["iconify"] = True

    return needed


def detect_capabilities_in_metadata(metadata: dict[str, Any] | None) -> dict[str, bool]:
    """Detect capability needs from explicit page metadata flags."""
    needed = dict.fromkeys(CAPABILITY_NAMES, False)
    if not metadata:
        return needed

    if metadata.get("mermaid"):
        needed["mermaid"] = True
        needed["iconify"] = True

    if metadata.get("math") or metadata.get("katex"):
        needed["katex"] = True

    return needed


def detect_page_capabilities_needed(
    *,
    page: PageLike | None = None,
    html_content: str | None = None,
    source_content: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """
    Detect which capabilities a page needs.

    Prefers rendered HTML (accurate), then raw source, then metadata flags.
    """
    needed = dict.fromkeys(CAPABILITY_NAMES, False)

    if metadata is None and page is not None:
        metadata = getattr(page, "metadata", None) or {}

    if html_content:
        html_needed = detect_capabilities_in_html(html_content)
        for name in CAPABILITY_NAMES:
            needed[name] = needed[name] or html_needed[name]

    if source_content is None and page is not None:
        source_content = get_raw_source(page)

    if source_content and not any(needed.values()):
        source_needed = detect_capabilities_in_source(source_content)
        for name in CAPABILITY_NAMES:
            needed[name] = needed[name] or source_needed[name]

    meta_needed = detect_capabilities_in_metadata(metadata)
    for name in CAPABILITY_NAMES:
        needed[name] = needed[name] or meta_needed[name]

    return needed


def resolve_effective_capabilities(
    site_capabilities: dict[str, bool],
    page_needed: dict[str, bool],
) -> dict[str, bool]:
    """
    Intersect site-level enabled/provisioned capabilities with page needs.

    Non-vendor capabilities (prebuilt_search, remote_content) pass through unchanged.
    """
    result = dict(site_capabilities)
    for name in CAPABILITY_NAMES:
        result[name] = bool(site_capabilities.get(name)) and bool(page_needed.get(name))
    return result
