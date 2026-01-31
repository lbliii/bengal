"""
Cascade metadata resolution for Bengal.

This package provides immutable, view-based cascade resolution that eliminates
the dual source of truth problem in the legacy cascade system.

Key Components:
    CascadeSnapshot: Immutable, pre-merged cascade data per section
    CascadeView: Mapping view that resolves frontmatter + cascade on access

Architecture:
    CascadeSnapshot holds pre-merged cascade for each section (child inherits parent).
    CascadeView is a Mapping that combines page frontmatter with cascade resolution.
    Page.metadata returns a CascadeView instead of a mutable dict.

Benefits:
    - Single source of truth (snapshot only, no copying)
    - Immutable (thread-safe for free-threading builds)
    - Always correct (resolution happens on access, not via mutation)
    - No timing bugs (works regardless of when metadata is accessed)

Usage:
    # Snapshot built during content discovery
    snapshot = CascadeSnapshot.build(content_dir, sections)

    # View created for each page (lazy, on first metadata access)
    view = CascadeView.for_page(frontmatter, section_path, snapshot)

    # Access resolves automatically
    view["type"]  # Returns frontmatter value or cascade value
    view.get("type", "default")  # With default
    "type" in view  # Membership test

    # Provenance tracking
    view.cascade_keys()  # Keys that came from cascade
    view.frontmatter_keys()  # Keys from page frontmatter

Related Modules:
    bengal.core.cascade_snapshot: Legacy snapshot (being migrated)
    bengal.core.page: Uses CascadeView for metadata property
    bengal.core.site.cascade: Builds snapshot during discovery
"""

from __future__ import annotations

from bengal.core.cascade.view import CascadeView

# Re-export CascadeSnapshot from legacy location during migration
from bengal.core.cascade_snapshot import CascadeSnapshot

__all__ = [
    "CascadeSnapshot",
    "CascadeView",
]
