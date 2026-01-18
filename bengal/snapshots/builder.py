"""
Snapshot builder - creates immutable snapshots from mutable site objects.

Called once after Phase 5 (content discovery) to create frozen snapshots
for all rendering operations. O(n) traversal where n = pages + sections.

"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.menu import MenuItem
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site

from bengal.snapshots.types import (
    MenuItemSnapshot,
    NO_SECTION,
    PageSnapshot,
    ScoutHint,
    SectionSnapshot,
    SiteSnapshot,
)


def create_site_snapshot(site: Site) -> SiteSnapshot:
    """
    Create immutable snapshot from mutable site.
    
    Called ONCE at end of Phase 5 (after content discovery).
    O(n) where n = total pages + sections.
    
    Args:
        site: Mutable Site after content discovery
        
    Returns:
        Frozen SiteSnapshot for all render operations
    """
    start = time.perf_counter()

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
        all_section_ids = {id(s) for s in site.sections}
        child_section_ids = {id(sub) for s in site.sections for sub in s.subsections}
        root_sections = [s for s in site.sections if id(s) not in child_section_ids]
    
    # Snapshot all root sections and their trees
    root_snapshots: list[SectionSnapshot] = []
    for root_section in root_sections:
        root_snapshot = _snapshot_section_recursive(
            root_section,
            page_cache,
            section_cache,
            depth=1,
        )
        root_snapshots.append(root_snapshot)
    
    # Also snapshot any remaining sections not yet snapshotted (handles disconnected sections)
    for section in site.sections:
        if id(section) not in section_cache:
            _snapshot_section_recursive(
                section,
                page_cache,
                section_cache,
                depth=1,
            )
    
    # Phase 2.5: Set root references on all sections (post-processing)
    # Find root sections (sections with parent=None)
    root_section_snapshots = [
        s for s in section_cache.values() if s.parent is None
    ]
    
    # Helper to find root section snapshot by walking up parent chain
    def find_root_snapshot(snapshot: SectionSnapshot) -> SectionSnapshot:
        """Find root section by walking up parent chain."""
        if snapshot.parent is None:
            return snapshot
        current = snapshot
        while current.parent is not None:
            current = current.parent
        return current
    
    # Update sections with root references (only if root is None)
    # Note: This is a simplified approach - root can be computed on-demand if needed
    for orig_section_id, section_snapshot in list(section_cache.items()):
        if section_snapshot.root is None:
            root_ref = find_root_snapshot(section_snapshot)
            if root_ref != section_snapshot.root:
                updated = SectionSnapshot(
                    name=section_snapshot.name,
                    title=section_snapshot.title,
                    nav_title=section_snapshot.nav_title,
                    href=section_snapshot.href,
                    path=section_snapshot.path,
                    pages=section_snapshot.pages,
                    sorted_pages=section_snapshot.sorted_pages,
                    regular_pages=section_snapshot.regular_pages,
                    subsections=section_snapshot.subsections,
                    sorted_subsections=section_snapshot.sorted_subsections,
                    parent=section_snapshot.parent,
                    root=root_ref,
                    index_page=section_snapshot.index_page,
                    metadata=section_snapshot.metadata,
                    icon=section_snapshot.icon,
                    weight=section_snapshot.weight,
                    depth=section_snapshot.depth,
                    hierarchy=section_snapshot.hierarchy,
                    is_virtual=section_snapshot.is_virtual,
                    template_name=section_snapshot.template_name,
                    total_pages=section_snapshot.total_pages,
                )
                section_cache[orig_section_id] = updated
    
    # Use first root as primary root (for compatibility)
    root = root_snapshots[0] if root_snapshots else None
    
    # If still no root, create a minimal virtual root
    if root is None:
        from bengal.core.section import Section
        virtual_root = Section(name="root", path=site.root_path / "content")
        root = _snapshot_section_recursive(
            virtual_root,
            page_cache,
            section_cache,
            depth=1,
        )
        # Update root reference on virtual root
        if root.root is None:
            root = SectionSnapshot(
                name=root.name,
                title=root.title,
                nav_title=root.nav_title,
                href=root.href,
                path=root.path,
                pages=root.pages,
                sorted_pages=root.sorted_pages,
                regular_pages=root.regular_pages,
                subsections=root.subsections,
                sorted_subsections=root.sorted_subsections,
                parent=root.parent,
                root=root,  # Root points to itself
                index_page=root.index_page,
                metadata=root.metadata,
                icon=root.icon,
                weight=root.weight,
                depth=root.depth,
                hierarchy=root.hierarchy,
                is_virtual=root.is_virtual,
                template_name=root.template_name,
                total_pages=root.total_pages,
            )

    # Phase 3: Resolve section references on pages
    for page in site.pages:
        page_snapshot = page_cache[id(page)]
        section = getattr(page, "_section", None)
        section_snapshot: SectionSnapshot | None = None
        if section and id(section) in section_cache:
            section_snapshot = section_cache[id(section)]
        else:
            # Use NO_SECTION sentinel for pages without sections
            section_snapshot = NO_SECTION
        
        # Create new snapshot with section ref (frozen, so must recreate)
        page_snapshot = PageSnapshot(
            title=page_snapshot.title,
            href=page_snapshot.href,
            source_path=page_snapshot.source_path,
            output_path=page_snapshot.output_path,
            template_name=page_snapshot.template_name,
            content=page_snapshot.content,
            parsed_html=page_snapshot.parsed_html,
            toc=page_snapshot.toc,
            toc_items=page_snapshot.toc_items,
            excerpt=page_snapshot.excerpt,
            metadata=page_snapshot.metadata,
            tags=page_snapshot.tags,
            categories=page_snapshot.categories,
            reading_time=page_snapshot.reading_time,
            word_count=page_snapshot.word_count,
            content_hash=page_snapshot.content_hash,
            section=section_snapshot,
            next_page=page_snapshot.next_page,
            prev_page=page_snapshot.prev_page,
            attention_score=page_snapshot.attention_score,
            estimated_render_ms=page_snapshot.estimated_render_ms,
        )
        page_cache[id(page)] = page_snapshot

    # Phase 4: Resolve navigation (next/prev)
    _resolve_navigation(page_cache, site)

    # Phase 5: Compute scheduling structures
    all_pages = tuple(page_cache.values())
    topological_order = _compute_topological_waves(root, all_pages)
    template_groups = _compute_template_groups(all_pages)
    attention_order = _compute_attention_order(all_pages)
    scout_hints = _compute_scout_hints(topological_order, template_groups, site)

    # Phase 6: Snapshot menus and taxonomies
    menus = _snapshot_menus(site, page_cache, section_cache)
    taxonomies = _snapshot_taxonomies(site, page_cache)

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Get config dict (handle both Config objects and plain dicts)
    config_dict = site.config.raw if hasattr(site.config, "raw") else site.config
    config_dict = dict(config_dict) if config_dict else {}

    return SiteSnapshot(
        pages=tuple(page_cache.values()),
        regular_pages=tuple(
            p for p in page_cache.values() if not p.metadata.get("_generated")
        ),
        sections=tuple(section_cache.values()),
        root_section=root or NO_SECTION,
        config=MappingProxyType(config_dict),
        params=MappingProxyType(config_dict.get("params", {})),
        data=MappingProxyType(dict(site.data) if hasattr(site, "data") and site.data else {}),
        menus=menus,
        taxonomies=taxonomies,
        topological_order=topological_order,
        template_groups=template_groups,
        attention_order=attention_order,
        scout_hints=scout_hints,
        snapshot_time=time.time(),
        page_count=len(page_cache),
        section_count=len(section_cache),
    )


def _snapshot_page_initial(page: Page, site: Site) -> PageSnapshot:
    """Create initial page snapshot (section resolved later)."""
    metadata = dict(page.metadata) if page.metadata else {}

    # Get href (_path property)
    href = getattr(page, "_path", None) or getattr(page, "href", "") or ""

    # Get output_path
    output_path = getattr(page, "output_path", None)
    if output_path is None:
        # Compute from source_path if not set
        source_path = page.source_path
        if source_path:
            # Convert .md to .html, preserve directory structure
            output_path = site.output_dir / source_path.relative_to(
                site.root_path / "content"
            ).with_suffix(".html")
        else:
            output_path = site.output_dir / "index.html"

    # Determine template name
    template_name = _determine_template(page, site)

    # Get raw markdown content (for reference/debugging/incremental comparison)
    raw_content = getattr(page, "_source", "") or getattr(page, "content", "") or ""
    
    # Get parsed HTML (pre-parsed during parsing phase - RFC: rfc-bengal-snapshot-engine)
    # This is what rendering should use, eliminating re-parsing during render
    parsed_html = getattr(page, "parsed_ast", "") or ""

    # Get TOC
    toc = getattr(page, "toc", "") or ""

    # Get TOC items
    toc_items = tuple(getattr(page, "toc_items", []) or [])

    # Get excerpt
    excerpt = getattr(page, "excerpt", "") or ""

    # Get reading_time and word_count
    reading_time = getattr(page, "reading_time", 0) or 0
    word_count = getattr(page, "word_count", 0) or 0

    # Compute content hash
    content_hash = _compute_content_hash(page)

    # Compute attention score
    attention_score = _compute_attention_score(page)

    # Estimate render time
    estimated_render_ms = _estimate_render_time(page)

    return PageSnapshot(
        title=page.title or "",
        href=href,
        source_path=page.source_path,
        output_path=output_path,
        template_name=template_name,
        content=raw_content,  # Raw markdown for reference/debugging
        parsed_html=parsed_html,  # Pre-parsed HTML (rendering uses this)
        toc=toc,
        toc_items=toc_items,
        excerpt=excerpt,
        metadata=MappingProxyType(metadata),
        tags=tuple(metadata.get("tags", []) or []),
        categories=tuple(metadata.get("categories", []) or []),
        reading_time=reading_time,
        word_count=word_count,
        content_hash=content_hash,
        attention_score=attention_score,
        estimated_render_ms=estimated_render_ms,
    )


def _snapshot_section_recursive(
    section: Section,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
    depth: int,
    parent: SectionSnapshot | None = None,
) -> SectionSnapshot:
    """Recursively snapshot section tree."""
    # Check cache first (handles re-visits)
    if id(section) in section_cache:
        return section_cache[id(section)]

    metadata = dict(section.metadata) if section.metadata else {}

    # Snapshot pages in this section
    pages = tuple(
        page_cache[id(p)] for p in section.pages if id(p) in page_cache
    )

    # Compute sorted variants
    sorted_pages = tuple(
        sorted(
            pages,
            key=lambda p: (
                p.metadata.get("weight", float("inf")),
                p.title.lower(),
            ),
        )
    )

    regular_pages = tuple(
        p
        for p in sorted_pages
        if p.source_path.stem not in ("index", "_index")
    )

    # Get href (_path property)
    href = getattr(section, "_path", None) or getattr(section, "href", "") or ""

    # Get title and nav_title
    title = section.title or section.name
    nav_title = getattr(section, "nav_title", None) or title

    # Get icon
    icon = metadata.get("icon")

    # Get weight
    weight = metadata.get("weight", float("inf"))
    if weight is not None:
        try:
            weight = float(weight)
        except (ValueError, TypeError):
            weight = float("inf")
    else:
        weight = float("inf")

    # Compute hierarchy
    hierarchy = tuple(
        [*parent.hierarchy, section.name] if parent else [section.name]
    )

    # Get is_virtual
    is_virtual = getattr(section, "is_virtual", False) or section.path is None

    # Most common template
    template_name = _most_common_template(pages)

    # Create snapshot (subsections filled in below)
    snapshot = SectionSnapshot(
        name=section.name,
        title=title,
        nav_title=nav_title,
        href=href,
        path=section.path,
        pages=pages,
        sorted_pages=sorted_pages,
        regular_pages=regular_pages,
        subsections=(),  # Filled below
        sorted_subsections=(),  # Filled below
        parent=parent,
        metadata=MappingProxyType(metadata),
        icon=icon,
        weight=weight,
        depth=depth,
        hierarchy=hierarchy,
        is_virtual=is_virtual,
        template_name=template_name,
        total_pages=len(pages),
    )

    # Cache before recursing (handles cycles)
    section_cache[id(section)] = snapshot

    # Recurse into subsections
    subsections = tuple(
        _snapshot_section_recursive(sub, page_cache, section_cache, depth + 1, snapshot)
        for sub in section.subsections
    )

    sorted_subsections = tuple(
        sorted(subsections, key=lambda s: (s.weight, s.title.lower()))
    )

    # Find index page
    index_page = _find_index_page(pages)

    # Update total_pages to include subsections
    total = len(pages) + sum(s.total_pages for s in subsections)

    # Recreate with subsections (frozen, can't mutate)
    snapshot = SectionSnapshot(
        name=snapshot.name,
        title=snapshot.title,
        nav_title=snapshot.nav_title,
        href=snapshot.href,
        path=snapshot.path,
        pages=snapshot.pages,
        sorted_pages=snapshot.sorted_pages,
        regular_pages=snapshot.regular_pages,
        subsections=subsections,
        sorted_subsections=sorted_subsections,
        parent=snapshot.parent,
        root=None,  # Set after full tree built
        index_page=index_page,
        metadata=snapshot.metadata,
        icon=snapshot.icon,
        weight=snapshot.weight,
        depth=snapshot.depth,
        hierarchy=snapshot.hierarchy,
        is_virtual=snapshot.is_virtual,
        template_name=snapshot.template_name,
        total_pages=total,
    )

    section_cache[id(section)] = snapshot
    return snapshot


def _resolve_navigation(
    page_cache: dict[int, PageSnapshot], site: Site
) -> None:
    """Resolve next/prev navigation links."""
    # Create mapping from source_path to page snapshot for lookup
    pages_by_path: dict[Path, PageSnapshot] = {
        page.source_path: page for page in page_cache.values()
    }
    
    # Sort pages by source_path for consistent ordering
    sorted_paths = sorted(pages_by_path.keys())
    
    # Update pages with next/prev refs
    for idx, path in enumerate(sorted_paths):
        page = pages_by_path[path]
        next_page = pages_by_path.get(sorted_paths[idx + 1]) if idx + 1 < len(sorted_paths) else None
        prev_page = pages_by_path.get(sorted_paths[idx - 1]) if idx > 0 else None

        # Only update if navigation changed
        if page.next_page != next_page or page.prev_page != prev_page:
            # Find original page in cache by source_path
            for orig_id, orig_page in list(page_cache.items()):
                if orig_page.source_path == path:
                    # Create new snapshot with navigation (frozen, so must recreate)
                    updated = PageSnapshot(
                        title=page.title,
                        href=page.href,
                        source_path=page.source_path,
                        output_path=page.output_path,
                        template_name=page.template_name,
                        content=page.content,
                        parsed_html=page.parsed_html,
                        toc=page.toc,
                        toc_items=page.toc_items,
                        excerpt=page.excerpt,
                        metadata=page.metadata,
                        tags=page.tags,
                        categories=page.categories,
                        reading_time=page.reading_time,
                        word_count=page.word_count,
                        content_hash=page.content_hash,
                        section=page.section,
                        next_page=next_page,
                        prev_page=prev_page,
                        attention_score=page.attention_score,
                        estimated_render_ms=page.estimated_render_ms,
                    )
                    page_cache[orig_id] = updated
                    break


def _compute_topological_waves(
    root: SectionSnapshot,
    all_pages: tuple[PageSnapshot, ...],
) -> tuple[tuple[PageSnapshot, ...], ...]:
    """
    Compute rendering waves following section topology.
    
    Each wave contains pages from the same section that share a template.
    Processing waves in order maximizes cache locality.
    
    Pages not assigned to any section are added as a final wave to ensure
    all pages get rendered.
    
    Args:
        root: Root section snapshot for tree traversal
        all_pages: All page snapshots (to detect orphan pages)
        
    Returns:
        Tuple of waves, where each wave is a tuple of PageSnapshots
    """
    waves: list[tuple[PageSnapshot, ...]] = []
    pages_in_sections: set[Path] = set()
    queue = [root]

    while queue:
        section = queue.pop(0)

        # All sorted_pages in section become one wave
        if section.sorted_pages:
            waves.append(section.sorted_pages)
            # Track which pages are in sections
            for page in section.sorted_pages:
                pages_in_sections.add(page.source_path)

        # Queue subsections (BFS order)
        queue.extend(section.sorted_subsections)

    # Find orphan pages (pages not in any section)
    orphan_pages = tuple(
        p for p in all_pages if p.source_path not in pages_in_sections
    )
    
    # Add orphan pages as final wave (ensures all pages get rendered)
    if orphan_pages:
        waves.append(orphan_pages)

    return tuple(waves)


def _compute_template_groups(
    pages: tuple[PageSnapshot, ...],
) -> MappingProxyType[str, tuple[PageSnapshot, ...]]:
    """Group pages by template for cache optimization."""
    groups: dict[str, list[PageSnapshot]] = {}

    for page in pages:
        template = page.template_name
        if template not in groups:
            groups[template] = []
        groups[template].append(page)

    return MappingProxyType({k: tuple(v) for k, v in groups.items()})


def _compute_attention_order(
    pages: tuple[PageSnapshot, ...],
) -> tuple[PageSnapshot, ...]:
    """
    Sort pages by attention score (importance).
    
    High attention pages rendered first for faster time-to-preview.
    """
    return tuple(sorted(pages, key=lambda p: -p.attention_score))


def _compute_scout_hints(
    waves: tuple[tuple[PageSnapshot, ...], ...],
    template_groups: MappingProxyType[str, tuple[PageSnapshot, ...]],
    site: Site,
) -> tuple[ScoutHint, ...]:
    """Pre-compute cache warming hints for scout thread."""
    hints: list[ScoutHint] = []
    seen_templates: set[str] = set()

    for wave in waves:
        if not wave:
            continue

        template = wave[0].template_name
        if template not in seen_templates:
            seen_templates.add(template)

            # Get partials for this template via template engine analysis
            partials = _get_template_partials(template, site)

            hints.append(
                ScoutHint(
                    template_path=Path(template),
                    partial_paths=tuple(partials),
                    pages_using=len(template_groups.get(template, ())),
                    priority=len(
                        template_groups.get(template, ())
                    ),  # More pages = higher priority
                )
            )

    # Sort by priority (warm most-used templates first)
    return tuple(sorted(hints, key=lambda h: -h.priority))


def _snapshot_menus(
    site: Site,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
) -> MappingProxyType[str, tuple[MenuItemSnapshot, ...]]:
    """Snapshot menus from site."""
    menus: dict[str, tuple[MenuItemSnapshot, ...]] = {}

    for menu_name, menu_items in site.menu.items():
        menus[menu_name] = tuple(
            _snapshot_menu_item(item, page_cache, section_cache)
            for item in menu_items
        )

    return MappingProxyType(menus)


def _snapshot_menu_item(
    item: MenuItem,
    page_cache: dict[int, PageSnapshot],
    section_cache: dict[int, SectionSnapshot],
) -> MenuItemSnapshot:
    """Snapshot a single menu item."""
    page_snapshot = None
    if item.page and id(item.page) in page_cache:
        page_snapshot = page_cache[id(item.page)]

    section_snapshot = None
    if item.section and id(item.section) in section_cache:
        section_snapshot = section_cache[id(item.section)]

    children = tuple(
        _snapshot_menu_item(child, page_cache, section_cache)
        for child in item.children
    )

    return MenuItemSnapshot(
        name=item.name,
        title=item.title,
        href=item.href,
        weight=item.weight,
        children=children,
        page=page_snapshot,
        section=section_snapshot,
        is_active=item.is_active,
    )


def _snapshot_taxonomies(
    site: Site,
    page_cache: dict[int, PageSnapshot],
) -> MappingProxyType[str, MappingProxyType[str, tuple[PageSnapshot, ...]]]:
    """Snapshot taxonomies from site."""
    taxonomies: dict[str, dict[str, tuple[PageSnapshot, ...]]] = {}

    for taxonomy_name, taxonomy_dict in site.taxonomies.items():
        taxonomy_snapshot: dict[str, tuple[PageSnapshot, ...]] = {}
        for term, pages_list in taxonomy_dict.items():
            taxonomy_snapshot[term] = tuple(
                page_cache[id(p)] for p in pages_list if id(p) in page_cache
            )
        taxonomies[taxonomy_name] = taxonomy_snapshot

    return MappingProxyType(
        {
            k: MappingProxyType(v) for k, v in taxonomies.items()
        }
    )


# Helper functions

def _determine_template(page: Page, site: Site) -> str:
    """Determine template name for page."""
    # Check page metadata
    template = page.metadata.get("template") or page.metadata.get("layout")
    if template:
        return str(template)

    # Check page type
    page_type = getattr(page, "type", None) or page.metadata.get("type")
    if page_type:
        return str(page_type)

    # Default template
    return "page.html"


def _compute_content_hash(page: Page) -> str:
    """Compute content hash for incremental builds."""
    content = getattr(page, "content", "") or ""
    return hashlib.sha256(content.encode()).hexdigest()


def _compute_attention_score(page: Page) -> float:
    """Compute attention score for priority scheduling."""
    score = 0.0

    # Boost for index pages
    if page.source_path.stem in ("index", "_index"):
        score += 10.0

    # Boost for recent pages
    date = page.metadata.get("date")
    if date:
        try:
            from datetime import datetime, timezone

            if isinstance(date, datetime):
                days_ago = (datetime.now(timezone.utc) - date).days
                score += max(0, 10.0 - days_ago / 10.0)
        except Exception:
            pass

    # Boost for featured pages
    if page.metadata.get("featured"):
        score += 5.0

    return score


def _estimate_render_time(page: Page) -> float:
    """Estimate render time in milliseconds."""
    # Simple heuristic: base time + word count factor
    base_ms = 10.0
    word_count = getattr(page, "word_count", 0) or 0
    return base_ms + (word_count / 100.0)


def _most_common_template(pages: tuple[PageSnapshot, ...]) -> str:
    """Find most common template in pages."""
    if not pages:
        return ""

    template_counts: dict[str, int] = {}
    for page in pages:
        template = page.template_name
        template_counts[template] = template_counts.get(template, 0) + 1

    return max(template_counts.items(), key=lambda x: x[1])[0] if template_counts else ""


def _find_index_page(pages: tuple[PageSnapshot, ...]) -> PageSnapshot | None:
    """Find index page in pages."""
    for page in pages:
        if page.source_path.stem in ("index", "_index"):
            return page
    return None


def _get_template_partials(template_name: str, site: Site) -> list[Path]:
    """
    Get partials used by template via template engine analysis.
    
    Uses the site's template engine to analyze template dependencies.
    This enables scout thread to warm partials ahead of workers.
    
    Args:
        template_name: Name of template to analyze
        site: Site instance (needed for template engine access)
        
    Returns:
        List of Path objects for partial templates used by this template
    """
    from bengal.rendering.engines import create_engine
    
    try:
        # Create engine to analyze template
        engine = create_engine(site, profile=False)
        
        # Get template path
        if hasattr(engine, "get_template_path"):
            template_path = engine.get_template_path(template_name)
            if not template_path:
                return []
        else:
            # Fallback: search template dirs manually
            template_path = None
            for template_dir in getattr(engine, "template_dirs", []):
                candidate = Path(template_dir) / template_name
                if candidate.exists():
                    template_path = candidate
                    break
            if not template_path:
                return []
        
        # Use engine's template analysis if available
        partials: set[str] = set()
        
        if hasattr(engine, "_track_referenced_templates"):
            # Jinja2/Kida engines have this method
            # Create a temporary cache to collect referenced templates
            referenced_cache: dict[str, set[str]] = {}
            
            # Try to extract referenced templates
            if hasattr(engine, "_env"):
                env = engine._env
                
                # Jinja2 approach
                if hasattr(env, "parse"):
                    try:
                        from jinja2 import meta
                        source, _filename, _uptodate = env.loader.get_source(env, template_name)
                        ast = env.parse(source)
                        for ref in meta.find_referenced_templates(ast) or []:
                            if isinstance(ref, str):
                                partials.add(ref)
                    except Exception:
                        pass
                
                # Kida approach (if available)
                if hasattr(env, "get_template"):
                    try:
                        template = env.get_template(template_name)
                        if hasattr(template, "_optimized_ast"):
                            ast = template._optimized_ast
                            if hasattr(engine, "_extract_referenced_templates"):
                                referenced = engine._extract_referenced_templates(ast)
                                partials.update(referenced)
                    except Exception:
                        pass
        
        # Convert template names to Paths
        partial_paths: list[Path] = []
        for partial_name in partials:
            if hasattr(engine, "get_template_path"):
                partial_path = engine.get_template_path(partial_name)
                if partial_path:
                    partial_paths.append(partial_path)
            else:
                # Fallback: search template dirs
                for template_dir in getattr(engine, "template_dirs", []):
                    candidate = Path(template_dir) / partial_name
                    if candidate.exists():
                        partial_paths.append(candidate)
                        break
        
        return partial_paths
        
    except Exception:
        # Template analysis is optional - don't fail snapshot creation
        return []
