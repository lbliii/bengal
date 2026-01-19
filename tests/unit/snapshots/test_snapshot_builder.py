"""
Tests for snapshot builder (create_site_snapshot).

Verifies that snapshots are created correctly from Site objects with all
required fields populated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.snapshots import create_site_snapshot
from bengal.snapshots.types import NO_SECTION, PageSnapshot, SectionSnapshot, SiteSnapshot


@pytest.mark.bengal(testroot="test-basic")
def test_create_snapshot_basic(site, build_site):
    """Test snapshot creation for basic site."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    assert isinstance(snapshot, SiteSnapshot)
    assert snapshot.page_count > 0
    assert len(snapshot.pages) == snapshot.page_count
    assert snapshot.root_section is not None


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_includes_all_pages(site, build_site):
    """Test that snapshot includes all pages from site."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    # All site pages should be in snapshot
    site_page_paths = {p.source_path for p in site.pages}
    snapshot_page_paths = {p.source_path for p in snapshot.pages}
    
    assert site_page_paths == snapshot_page_paths


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_pages_have_required_fields(site, build_site):
    """Test that PageSnapshot has all required fields."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    for page_snap in snapshot.pages:
        assert isinstance(page_snap, PageSnapshot)
        assert page_snap.title is not None
        assert page_snap.source_path is not None
        assert page_snap.output_path is not None
        assert page_snap.template_name is not None
        assert page_snap.content is not None  # Raw markdown
        assert page_snap.section is not None or page_snap.section is NO_SECTION


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_sections_have_required_fields(site, build_site):
    """Test that SectionSnapshot has all required fields."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    for section_snap in snapshot.sections:
        assert isinstance(section_snap, SectionSnapshot)
        assert section_snap.name is not None
        assert section_snap.pages is not None
        assert isinstance(section_snap.pages, tuple)  # Immutable
        assert isinstance(section_snap.subsections, tuple)  # Immutable


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_navigation_resolved(site, build_site):
    """Test that next_page and prev_page are resolved."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    # Check that pages have navigation links
    pages_with_nav = [p for p in snapshot.pages if p.next_page or p.prev_page]
    
    # In a multi-page site, at least some pages should have navigation
    if len(snapshot.pages) > 1:
        assert len(pages_with_nav) > 0


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_topological_order(site, build_site):
    """Test that topological_order is computed."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    assert snapshot.topological_order is not None
    assert isinstance(snapshot.topological_order, tuple)
    assert len(snapshot.topological_order) > 0
    
    # Each wave should be a tuple of PageSnapshots
    for wave in snapshot.topological_order:
        assert isinstance(wave, tuple)
        assert len(wave) > 0
        for page_snap in wave:
            assert isinstance(page_snap, PageSnapshot)


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_template_groups(site, build_site):
    """Test that template_groups is computed."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    assert snapshot.template_groups is not None
    # template_groups is a MappingProxyType (immutable dict view)
    from types import MappingProxyType
    assert isinstance(snapshot.template_groups, MappingProxyType)
    
    # Each group should be a tuple of PageSnapshots
    for template_name, pages in snapshot.template_groups.items():
        assert isinstance(template_name, str)
        assert isinstance(pages, tuple)
        assert len(pages) > 0
        for page_snap in pages:
            assert isinstance(page_snap, PageSnapshot)


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_scout_hints(site, build_site):
    """Test that scout_hints are generated."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    assert snapshot.scout_hints is not None
    assert isinstance(snapshot.scout_hints, tuple)
    
    # Scout hints should have template paths
    for hint in snapshot.scout_hints:
        assert hint.template_path is not None
        assert hint.priority >= 0


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_immutability(site, build_site):
    """Test that snapshots are immutable (frozen dataclasses)."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    # Try to modify a field (should raise FrozenInstanceError)
    import dataclasses
    
    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.page_count = 999
    
    # Try to modify a page snapshot
    page_snap = snapshot.pages[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        page_snap.title = "Modified"


@pytest.mark.bengal(testroot="test-taxonomy")
def test_snapshot_section_hierarchy(site, build_site):
    """Test that section hierarchy is correctly built."""
    build_site()
    
    snapshot = create_site_snapshot(site)
    
    # Root section should have no parent
    assert snapshot.root_section.parent is None
    
    # All sections should have root set
    for section_snap in snapshot.sections:
        assert section_snap.root is not None
        assert section_snap.root == snapshot.root_section or section_snap == snapshot.root_section
