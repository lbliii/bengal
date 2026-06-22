"""
Content detectors for opt-in runtime capabilities (#571, #572).

Each registered capability declares how to detect whether a page actually uses it.
Build-time resolution is: site owner enabled AND vendors provisioned AND
content detector matched → emit assets for that page.

See plan/rfc-capability-system.md Phase 1–2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bengal.content.page_source import get_raw_source

if TYPE_CHECKING:
    from bengal.protocols import PageLike


def _registry():
    from bengal.capabilities.registry import get_capability_registry

    return get_capability_registry()


def _empty_needed() -> dict[str, bool]:
    return dict.fromkeys(_registry().names, False)


def _apply_implies(needed: dict[str, bool]) -> None:
    for spec in _registry():
        if needed.get(spec.name) and spec.implies:
            for implied in spec.implies:
                needed[implied] = True


def detect_capabilities_in_html(html: str) -> dict[str, bool]:
    """Detect capability needs from rendered HTML."""
    needed = _empty_needed()
    if not html:
        return needed

    registry = _registry()
    for spec in registry:
        patterns = registry.html_patterns(spec.name)
        if any(pattern.search(html) for pattern in patterns):
            needed[spec.name] = True

    _apply_implies(needed)
    return needed


def detect_capabilities_in_source(source: str) -> dict[str, bool]:
    """Detect capability needs from raw markdown/source."""
    needed = _empty_needed()
    if not source:
        return needed

    registry = _registry()
    for spec in registry:
        patterns = registry.source_patterns(spec.name)
        if any(pattern.search(source) for pattern in patterns):
            needed[spec.name] = True

    _apply_implies(needed)
    return needed


def detect_capabilities_in_metadata(metadata: dict[str, Any] | None) -> dict[str, bool]:
    """Detect capability needs from explicit page metadata flags."""
    needed = _empty_needed()
    if not metadata:
        return needed

    for spec in _registry():
        if any(metadata.get(key) for key in spec.metadata_keys):
            needed[spec.name] = True

    _apply_implies(needed)
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
    needed = _empty_needed()

    if metadata is None and page is not None:
        metadata = getattr(page, "metadata", None) or {}

    if html_content:
        html_needed = detect_capabilities_in_html(html_content)
        for name in needed:
            needed[name] = needed[name] or html_needed[name]

    if source_content is None and page is not None:
        source_content = get_raw_source(page)

    if source_content and not any(needed.values()):
        source_needed = detect_capabilities_in_source(source_content)
        for name in needed:
            needed[name] = needed[name] or source_needed[name]

    meta_needed = detect_capabilities_in_metadata(metadata)
    for name in needed:
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
    for name in _registry().names:
        result[name] = bool(site_capabilities.get(name)) and bool(page_needed.get(name))
    return result
