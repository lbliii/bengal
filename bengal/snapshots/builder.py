"""
Snapshot builder - creates immutable snapshots from mutable site objects.

Called once after Phase 5 (content discovery) to create frozen snapshots
for all rendering operations. O(n) traversal where n = pages + sections.

RFC: Snapshot-Enabled v2 Opportunities
- create_site_snapshot(): Full O(n) snapshot creation
- update_snapshot(): Incremental O(changed) updates with structural sharing
- pages_affected_by_template_change(): O(1) template->page lookup

"""

from __future__ import annotations

import time
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.site import Site
    from bengal.protocols import SiteLike

from bengal.config.snapshot import ConfigSnapshot
from bengal.snapshots.content import (
    _resolve_navigation,
    _snapshot_page_initial,
    _snapshot_section_recursive,
)
from bengal.snapshots.scheduling import (
    _compute_attention_order,
    _compute_scout_hints,
    _compute_template_groups,
    _compute_topological_waves,
    _snapshot_menus,
    _snapshot_taxonomies,
)
from bengal.snapshots.templates import (
    _snapshot_templates,
)
from bengal.snapshots.types import (
    NO_SECTION,
    PageSnapshot,
    SectionSnapshot,
    SiteSnapshot,
    TemplateSnapshot,
)
from bengal.snapshots.utils import (
    update_frozen,
)


def create_site_snapshot(site: SiteLike) -> SiteSnapshot:
    """
    Create immutable snapshot from mutable site.

    Called ONCE at end of Phase 5 (after content discovery).
    O(n) where n = total pages + sections.

    Args:
        site: Mutable Site after content discovery

    Returns:
        Frozen SiteSnapshot for all render operations
    """
    # Caches for circular reference resolution
    page_cache: dict[int, PageSnapshot] = {}
    section_cache: dict[int, SectionSnapshot] = {}

    # Phase 1: Snapshot all pages (without section refs)
    for page in site.pages:
        page_cache[id(page)] = _snapshot_page_initial(page, site)

    # Phase 2: Snapshot all sections (with page refs)
    # Snapshot all sections recursively, starting from root sections
    root_sections = [s for s in site.sections if s.parent is None]

    # If no root sections, find top-level sections (not children of others)
    if not root_sections:
        child_section_ids = {id(sub) for s in site.sections for sub in s.subsections}
        root_sections = [s for s in site.sections if id(s) not in child_section_ids]

    # Snapshot all root sections and their trees
    root_snapshots: list[SectionSnapshot] = []
    for root_section in root_sections:
        root_snap = _snapshot_section_recursive(
            root_section,
            page_cache,
            section_cache,
            depth=1,
        )
        root_snapshots.append(root_snap)

    # Also snapshot any remaining disconnected sections
    for section in site.sections:
        if id(section) not in section_cache:
            _snapshot_section_recursive(section, page_cache, section_cache, depth=1)

    # Phase 2.5: Set root references on all sections (post-processing)
    def find_root_snapshot(snapshot: SectionSnapshot) -> SectionSnapshot:
        """Find root section by walking up parent chain."""
        current = snapshot
        while current.parent is not None:
            current = current.parent
        return current

    for orig_section_id, section_snapshot in list(section_cache.items()):
        if section_snapshot.root is None:
            root_ref = find_root_snapshot(section_snapshot)
            if root_ref != section_snapshot.root:
                section_cache[orig_section_id] = update_frozen(section_snapshot, root=root_ref)

    # Determine root section
    root = root_snapshots[0] if root_snapshots else None

    if root is None:
        # Fallback: create virtual root
        from bengal.core.section import Section

        virtual_root = Section(name="root", path=site.root_path / "content")
        root = _snapshot_section_recursive(virtual_root, page_cache, section_cache, depth=1)
        if root.root is None:
            root = update_frozen(root, root=root)
            section_cache[id(virtual_root)] = root

    # Ensure all sections have root set
    for orig_section_id, section_snapshot in list(section_cache.items()):
        if section_snapshot.root is None:
            root_ref = (
                find_root_snapshot(section_snapshot)
                if section_snapshot.parent is not None
                else root
            )
            section_cache[orig_section_id] = update_frozen(section_snapshot, root=root_ref)

    # Phase 3: Resolve section references on pages
    for mutable_page in site.pages:
        page_snapshot = page_cache.get(id(mutable_page))
        if not page_snapshot:
            continue

        section = getattr(mutable_page, "_section", None)
        section_snapshot = (section_cache.get(id(section)) if section else NO_SECTION) or NO_SECTION

        if page_snapshot.section != section_snapshot:
            page_cache[id(mutable_page)] = update_frozen(page_snapshot, section=section_snapshot)

    # Phase 4: Resolve prev/next navigation
    _resolve_navigation(page_cache, site)

    # Phase 5: Compute scheduling data
    all_pages = tuple(page_cache.values())
    all_sections = tuple(section_cache.values())

    # Compute pre-sorted caches
    regular_pages = tuple(p for p in all_pages if not p.metadata.get("_generated"))

    topological_order = _compute_topological_waves(root, all_pages)
    template_groups = _compute_template_groups(all_pages)
    attention_order = _compute_attention_order(all_pages)
    scout_hints = _compute_scout_hints(topological_order, template_groups, site)

    # Snapshot menus and taxonomies
    menus = _snapshot_menus(site, page_cache, section_cache)
    taxonomies = _snapshot_taxonomies(site, page_cache)

    # Snapshot templates
    templates, template_dep_graph, template_dependents = _snapshot_templates(site, page_cache)

    # Create config snapshot
    config_dict = site.config.raw if hasattr(site.config, "raw") else site.config
    config_dict = dict(config_dict) if isinstance(config_dict, dict) else {}
    config_snapshot = ConfigSnapshot.from_dict(config_dict)

    # Build navigation trees
    nav_trees = _build_nav_trees(site)

    # Pre-compute top-level content and tag pages
    top_level_pages, top_level_sections = _compute_top_level_content(regular_pages, all_sections)
    tag_pages = _compute_tag_pages(taxonomies)

    return SiteSnapshot(
        pages=all_pages,
        regular_pages=regular_pages,
        sections=all_sections,
        root_section=root or NO_SECTION,
        config=MappingProxyType(config_dict),
        params=MappingProxyType(config_dict.get("params", {})),
        data=MappingProxyType(dict(site.data) if site.data else {}),
        menus=menus,
        taxonomies=taxonomies,
        topological_order=topological_order,
        template_groups=template_groups,
        attention_order=attention_order,
        scout_hints=scout_hints,
        snapshot_time=time.time(),
        page_count=len(page_cache),
        section_count=len(section_cache),
        templates=templates,
        template_dependency_graph=template_dep_graph,
        template_dependents=template_dependents,
        config_snapshot=config_snapshot,
        nav_trees=nav_trees,
        top_level_pages=top_level_pages,
        top_level_sections=top_level_sections,
        tag_pages=tag_pages,
    )


def update_snapshot(
    old: SiteSnapshot,
    site: Site,
    changed_paths: set[Path],
) -> SiteSnapshot:
    """
    Incrementally update snapshot for changed files.

    O(changed) instead of O(all) by using structural sharing.
    Unchanged portions reference the same frozen objects.

    RFC: Snapshot-Enabled v2 Opportunities (Opportunity 2)

    Args:
        old: Previous build's snapshot
        site: Mutable Site with updated content for changed files
        changed_paths: Files that changed since last build

    Returns:
        New snapshot with structural sharing for unchanged data

    Performance:
        | Scenario | Full Snapshot | Incremental |
        |----------|---------------|-------------|
        | 1000 pages, 1 change | ~50ms | <5ms |
        | 1000 pages, 10 changes | ~50ms | ~10ms |
    """
    if not changed_paths:
        # No changes - return same snapshot
        return old

    # Build mapping from source_path to old page snapshot
    old_pages_by_path: dict[Path, PageSnapshot] = {p.source_path: p for p in old.pages}

    # Build mapping from source_path to mutable page
    site_pages_by_path: dict[Path, Page] = {p.source_path: p for p in site.pages}

    # Identify affected pages (directly changed)
    affected_paths: set[Path] = set()
    for changed_path in changed_paths:
        if changed_path in old_pages_by_path or changed_path in site_pages_by_path:
            affected_paths.add(changed_path)

    # Also check for template changes affecting pages
    for changed_path in changed_paths:
        if changed_path.suffix in (".html", ".jinja", ".j2"):
            # Find pages using this template
            template_name = changed_path.name
            for page_path, page_snap in old_pages_by_path.items():
                if page_snap.template_name == template_name:
                    affected_paths.add(page_path)
                # Also check transitive dependencies
                if template_name in old.template_dependency_graph:
                    for dep_template in old.template_dependency_graph[template_name]:
                        if page_snap.template_name == dep_template:
                            affected_paths.add(page_path)

    # Create new page snapshots for affected pages only
    new_page_cache: dict[int, PageSnapshot] = {}

    for path, old_page in old_pages_by_path.items():
        if path in affected_paths:
            # Re-snapshot this page
            if path in site_pages_by_path:
                mutable_page = site_pages_by_path[path]
                new_page_cache[id(mutable_page)] = _snapshot_page_initial(mutable_page, site)
            # else: page was deleted, skip it
        else:
            # Reuse old snapshot (structural sharing)
            new_page_cache[id(old_page)] = old_page

    # Add any new pages not in old snapshot
    for path, mutable_page in site_pages_by_path.items():
        if path not in old_pages_by_path:
            new_page_cache[id(mutable_page)] = _snapshot_page_initial(mutable_page, site)

    # Identify affected sections (parents of changed pages)
    affected_section_paths: set[Path | None] = set()
    for path in affected_paths:
        if path in site_pages_by_path:
            page = site_pages_by_path[path]
            section = getattr(page, "_section", None)
            if section:
                affected_section_paths.add(section.path)

    # Rebuild sections if any pages changed
    # For simplicity in v1, rebuild all sections if anything changed
    # TODO: Optimize to only rebuild affected sections
    section_cache: dict[int, SectionSnapshot] = {}

    root_sections = [s for s in site.sections if s.parent is None]
    if not root_sections:
        child_section_ids = {id(sub) for s in site.sections for sub in s.subsections}
        root_sections = [s for s in site.sections if id(s) not in child_section_ids]

    for root_section in root_sections:
        _snapshot_section_recursive(
            root_section,
            new_page_cache,
            section_cache,
            depth=1,
        )

    # Set root references on all sections (post-processing)
    def find_root_snapshot(snapshot: SectionSnapshot) -> SectionSnapshot:
        current = snapshot
        while current.parent is not None:
            current = current.parent
        return current

    for orig_id, section_snapshot in list(section_cache.items()):
        if section_snapshot.root is None:
            root_ref = find_root_snapshot(section_snapshot)
            if root_ref != section_snapshot.root:
                section_cache[orig_id] = update_frozen(section_snapshot, root=root_ref)

    # Find root for the snapshot
    root_snapshots_inc = [s for s in section_cache.values() if s.parent is None]
    root = root_snapshots_inc[0] if root_snapshots_inc else None

    if root is None:
        from bengal.core.section import Section

        virtual_root = Section(name="root", path=site.root_path / "content")
        root = _snapshot_section_recursive(virtual_root, new_page_cache, section_cache, depth=1)
        if root.root is None:
            root = update_frozen(root, root=root)
            section_cache[id(virtual_root)] = root

    # Ensure all sections have root set
    for orig_id, section_snapshot in list(section_cache.items()):
        if section_snapshot.root is None:
            root_ref = (
                find_root_snapshot(section_snapshot)
                if section_snapshot.parent is not None
                else root
            )
            section_cache[orig_id] = update_frozen(section_snapshot, root=root_ref)

    # Resolve section references on pages
    for mutable_page in site.pages:
        if id(mutable_page) in new_page_cache:
            page_snapshot = new_page_cache[id(mutable_page)]
            section = getattr(mutable_page, "_section", None)
            section_snapshot = (
                section_cache.get(id(section)) if section else NO_SECTION
            ) or NO_SECTION

            if page_snapshot.section != section_snapshot:
                # Update with new section ref
                new_page_cache[id(mutable_page)] = update_frozen(
                    page_snapshot, section=section_snapshot
                )

    # Reuse unchanged data structures from old snapshot
    all_pages = tuple(new_page_cache.values())

    # Recompute scheduling if pages changed
    topological_order = _compute_topological_waves(root, all_pages)
    template_groups = _compute_template_groups(all_pages)
    attention_order = _compute_attention_order(all_pages)

    # Reuse scout hints if templates didn't change
    template_changed = any(p.suffix in (".html", ".jinja", ".j2") for p in changed_paths)
    scout_hints = (
        _compute_scout_hints(topological_order, template_groups, site)
        if template_changed
        else old.scout_hints
    )

    # Reuse template snapshots if no template files changed
    if template_changed:
        templates, template_dep_graph, template_dependents = _snapshot_templates(
            site, new_page_cache
        )
    else:
        # Update template_dependents with new page refs
        templates = old.templates
        template_dep_graph = old.template_dependency_graph
        # Rebuild dependents with new page refs
        template_dependents = _rebuild_template_dependents(templates, template_groups)

    # Reuse menus and taxonomies if structure didn't change
    # For now, rebuild them (cheap operation)
    menus = _snapshot_menus(site, new_page_cache, section_cache)
    taxonomies = _snapshot_taxonomies(site, new_page_cache)

    # Reuse config if unchanged
    config_dict = site.config.raw if hasattr(site.config, "raw") else site.config
    # Type narrowing: ensure config_dict is a dict
    config_dict = dict(config_dict) if isinstance(config_dict, dict) else {}
    config_snapshot = old.config_snapshot or ConfigSnapshot.from_dict(config_dict)

    # Rebuild nav trees (structure may have changed)
    nav_trees = _build_nav_trees(site)

    # Rebuild renderer caches
    regular_pages_inc = tuple(p for p in all_pages if not p.metadata.get("_generated"))
    all_sections_inc = tuple(section_cache.values())
    top_level_pages, top_level_sections = _compute_top_level_content(
        regular_pages_inc, all_sections_inc
    )
    tag_pages = _compute_tag_pages(taxonomies)

    return SiteSnapshot(
        pages=all_pages,
        regular_pages=regular_pages_inc,
        sections=all_sections_inc,
        root_section=root or NO_SECTION,
        config=old.config,  # Reuse (structural sharing)
        params=old.params,  # Reuse (structural sharing)
        data=old.data,  # Reuse (structural sharing)
        menus=menus,
        taxonomies=taxonomies,
        topological_order=topological_order,
        template_groups=template_groups,
        attention_order=attention_order,
        scout_hints=scout_hints,
        snapshot_time=time.time(),
        page_count=len(new_page_cache),
        section_count=len(section_cache),
        templates=templates,
        template_dependency_graph=template_dep_graph,
        template_dependents=template_dependents,
        config_snapshot=config_snapshot,
        nav_trees=nav_trees,
        top_level_pages=top_level_pages,
        top_level_sections=top_level_sections,
        tag_pages=tag_pages,
    )


def _rebuild_template_dependents(
    templates: MappingProxyType[str, TemplateSnapshot],
    template_groups: MappingProxyType[str, tuple[PageSnapshot, ...]],
) -> MappingProxyType[str, tuple[PageSnapshot, ...]]:
    """Rebuild template_dependents with new page references."""
    dependents: dict[str, list[PageSnapshot]] = {}

    for template_name in templates:
        pages = list(template_groups.get(template_name, ()))
        if pages:
            dependents[template_name] = pages

    return MappingProxyType({k: tuple(v) for k, v in dependents.items()})


def _compute_top_level_content(
    regular_pages: tuple[PageSnapshot, ...],
    sections: tuple[SectionSnapshot, ...],
) -> tuple[tuple[PageSnapshot, ...], tuple[SectionSnapshot, ...]]:
    """
    Pre-compute top-level pages and sections (not nested in any parent).

    Eliminates Renderer._cache_lock by computing at snapshot time instead of
    lazily during rendering under a lock.

    Args:
        regular_pages: All non-generated page snapshots
        sections: All section snapshots

    Returns:
        Tuple of (top_level_pages, top_level_sections)
    """
    # Build set of all page source_paths that are in any section
    pages_in_sections: set[Path] = set()
    for section in sections:
        for page in section.pages:
            pages_in_sections.add(page.source_path)

    # Build set of sections that are subsections of another
    nested_section_paths: set[Path | None] = set()
    for parent in sections:
        for sub in parent.subsections:
            nested_section_paths.add(sub.path)

    top_pages = tuple(p for p in regular_pages if p.source_path not in pages_in_sections)
    top_sections = tuple(s for s in sections if s.path not in nested_section_paths)

    return top_pages, top_sections


def _compute_tag_pages(
    taxonomies: MappingProxyType[str, MappingProxyType[str, tuple[PageSnapshot, ...]]],
) -> MappingProxyType[str, tuple[PageSnapshot, ...]]:
    """
    Pre-compute filtered tag->pages mapping from taxonomy data.

    Eliminates Renderer._cache_lock by computing at snapshot time.
    Excludes generated pages, API pages, and CLI pages (same logic as
    Renderer._build_all_tag_pages_cache).

    Args:
        taxonomies: Snapshot taxonomy data

    Returns:
        Frozen mapping of tag_slug -> filtered page snapshots
    """
    tags_data = taxonomies.get("tags", {})
    cache: dict[str, tuple[PageSnapshot, ...]] = {}

    for tag_slug, tag_pages_tuple in tags_data.items():
        filtered: list[PageSnapshot] = []
        for page in tag_pages_tuple:
            source_str = str(page.source_path)
            # Same filtering as Renderer._build_all_tag_pages_cache:
            # exclude generated, API, and CLI pages
            if (
                not page.metadata.get("_generated")
                and "content/api" not in source_str
                and "content/cli" not in source_str
            ):
                filtered.append(page)
        cache[tag_slug] = tuple(filtered)

    return MappingProxyType(cache)


def _build_nav_trees(site: SiteLike) -> MappingProxyType[str, Any]:
    """
    Pre-compute navigation trees for all versions at snapshot time.

    This eliminates the need for NavTreeCache locks during parallel rendering.
    Trees are built from the fully-populated site (sections + pages), which is
    the same input NavTree.build() uses when called lazily.

    Args:
        site: Mutable Site after content discovery (sections must be populated)

    Returns:
        Frozen mapping of version_key -> NavTree for lock-free lookups
    """
    from bengal.core.nav_tree import NavTree

    trees: dict[str, Any] = {}

    # Build default (unversioned) tree
    trees["__default__"] = NavTree.build(site)

    # Build per-version trees if versioning is enabled
    if getattr(site, "versioning_enabled", False):
        versions = getattr(site, "versions", [])
        for version_dict in versions:
            version_id = version_dict["id"] if isinstance(version_dict, dict) else str(version_dict)
            trees[version_id] = NavTree.build(site, version_id)

    return MappingProxyType(trees)
