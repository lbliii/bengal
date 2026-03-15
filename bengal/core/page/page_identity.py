"""
PageIdentity — Immutable, cache-line-friendly page identity for hot-path operations.

Computed once per page after content phases finalize. Every field is O(1) to access.
Thread-safe by construction (frozen + slots).

Use PageIdentity in build-phase algorithms (related posts, taxonomy indexing,
URL collision detection) and render-phase scoring loops. Avoid accessing
Page.metadata, Page.kind, or Page.slug in tight loops — use identity instead.

Architecture:
    Page.identity returns the frozen PageIdentity struct.
    Build orchestration calls page.finalize_identity() after all section
    assignments, output paths, and tag normalization are complete (end of
    content phases, before parsing/rendering).

Cost: O(1) for every field (all pre-computed, no property chains).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageIdentity:
    """Immutable page identity — all O(1) lookups, no property chains.

    Fields are a minimal subset of Page state needed by build-phase
    algorithms and render-phase scoring. Everything is pre-resolved
    to avoid hidden cost (pathlib.relative_to, cascade resolution, etc.).
    """

    page_id: int
    source_path: str
    section_path_str: str
    slug: str
    kind: str
    is_generated: bool
    is_index: bool
    tag_slugs: frozenset[str]
    href: str
