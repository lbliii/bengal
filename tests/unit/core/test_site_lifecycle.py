"""
Tests for Site.prepare_for_rebuild() lifecycle management.

Verifies that warm rebuild state reset correctly clears all per-build
mutable state — especially the cascade snapshot — while preserving
immutable configuration state.

Also verifies BuildState delegation: per-build state (cascade, template
caches, features_detected) is structurally fresh via BuildState.
"""

from pathlib import Path

import pytest

from bengal.core.cascade_snapshot import CascadeSnapshot
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site
from bengal.orchestration.build_state import BuildState


@pytest.fixture()
def site_with_cascade(tmp_path):
    """Create a site with sections, pages, and a populated cascade snapshot."""
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "docs").mkdir()

    site = Site(root_path=tmp_path)

    # Create an index page with cascade data
    index_page = Page(
        source_path=content_dir / "docs" / "_index.md",
        _raw_metadata={
            "title": "Documentation",
            "cascade": {"type": "doc", "layout": "docs-sidebar"},
        },
    )
    index_page._site = site

    # Create a section with the index page
    section = Section(
        name="docs",
        path=content_dir / "docs",
        pages=[],
        index_page=index_page,
        metadata={"title": "Documentation"},
    )

    # Create a child page (no explicit type/layout — relies on cascade)
    child_page = Page(
        source_path=content_dir / "docs" / "guide.md",
        _raw_metadata={"title": "Getting Started Guide"},
    )
    child_page._site = site
    child_page._section_path = content_dir / "docs"
    section.pages.append(child_page)

    site.sections = [section]
    site.pages = [index_page, child_page]

    # Build the cascade snapshot
    site.build_cascade_snapshot()

    return site, child_page


class TestPrepareForRebuild:
    """Tests for Site.prepare_for_rebuild()."""

    def test_resets_pages_and_sections(self, tmp_path):
        """prepare_for_rebuild clears pages and sections."""
        site = Site(root_path=tmp_path)
        site.pages = [Page(source_path=tmp_path / "p.md", _raw_metadata={"title": "P"})]
        site.sections = [Section(name="s", path=tmp_path / "s")]

        site.prepare_for_rebuild()

        assert site.pages == []
        assert site.sections == []

    def test_resets_cascade_snapshot(self, site_with_cascade):
        """prepare_for_rebuild clears the cascade snapshot to None."""
        site, _ = site_with_cascade

        # Cascade should be populated before reset
        assert site._cascade_snapshot is not None
        assert len(site.cascade) > 0

        site.prepare_for_rebuild()

        # After reset, _cascade_snapshot is None and .cascade returns empty
        assert site._cascade_snapshot is None
        assert len(site.cascade) == 0

    def test_resets_taxonomies_and_menus(self, tmp_path):
        """prepare_for_rebuild clears taxonomies and menus."""
        site = Site(root_path=tmp_path)
        site.taxonomies = {"tags": {"python": {"pages": []}}}
        site.menu = {"main": []}
        site.menu_builders = {"main": object()}
        site.xref_index = {"by_path": {}}

        site.prepare_for_rebuild()

        assert site.taxonomies == {}
        assert site.menu == {}
        assert site.menu_builders == {}
        assert site.xref_index == {}

    def test_preserves_config(self, tmp_path):
        """prepare_for_rebuild does NOT touch config, theme, or paths."""
        site = Site(root_path=tmp_path, config={"site": {"title": "My Site"}})
        original_config = site.config
        original_theme = site.theme
        original_output = site.output_dir

        site.prepare_for_rebuild()

        assert site.config is original_config
        assert site.theme == original_theme
        assert site.output_dir == original_output
        assert site.root_path == tmp_path

    def test_invalidates_page_caches(self, tmp_path):
        """prepare_for_rebuild invalidates all page caches."""
        site = Site(root_path=tmp_path)
        page = Page(source_path=tmp_path / "p.md", _raw_metadata={"title": "P"})
        site.pages = [page]

        # Populate caches
        _ = site.regular_pages
        assert site._regular_pages_cache is not None

        site.prepare_for_rebuild()

        assert site._regular_pages_cache is None


class TestCascadePreservedAcrossRebuild:
    """
    Tests that cascade values survive the warm rebuild cycle.

    This class tests the scenario that was broken before the fix:
    1. First build populates cascade from section _index.md
    2. Warm rebuild resets state
    3. Rediscovery repopulates sections and rebuilds cascade
    4. Child pages should still resolve cascaded layout/type
    """

    def test_cascade_survives_rebuild_cycle(self, tmp_path):
        """
        Simulate a warm rebuild cycle and verify cascade values are preserved.

        This is the core regression test for the hot-reload cascade loss bug.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "docs").mkdir()

        site = Site(root_path=tmp_path)

        # --- First build ---
        index_page = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"type": "doc", "layout": "docs-sidebar"},
            },
        )
        index_page._site = site

        section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=index_page,
            metadata={"title": "Docs"},
        )

        child = Page(
            source_path=content_dir / "docs" / "guide.md",
            _raw_metadata={"title": "Guide"},
        )
        child._site = site
        child._section_path = content_dir / "docs"
        section.pages.append(child)

        site.sections = [section]
        site.pages = [index_page, child]
        site.build_cascade_snapshot()

        # Verify cascade works on first build
        assert child.metadata.get("type") == "doc"
        assert child.metadata.get("layout") == "docs-sidebar"

        # --- Warm rebuild (simulates BuildTrigger) ---
        site.prepare_for_rebuild()

        # Cascade should be cleared
        assert site._cascade_snapshot is None

        # --- Rediscovery (simulates ContentOrchestrator.discover_content) ---
        # Recreate sections and pages (as discovery would)
        new_index = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"type": "doc", "layout": "docs-sidebar"},
            },
        )
        new_index._site = site

        new_section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=new_index,
            metadata={"title": "Docs"},
        )

        new_child = Page(
            source_path=content_dir / "docs" / "guide.md",
            _raw_metadata={"title": "Guide"},
        )
        new_child._site = site
        new_child._section_path = content_dir / "docs"
        new_section.pages.append(new_child)

        site.sections = [new_section]
        site.pages = [new_index, new_child]

        # Rebuild cascade (as _apply_cascades would)
        site.build_cascade_snapshot()

        # --- Verify cascade values survived the rebuild ---
        assert new_child.metadata.get("type") == "doc"
        assert new_child.metadata.get("layout") == "docs-sidebar"
        assert new_child.type == "doc"
        assert new_child.variant == "docs-sidebar"

    def test_stale_snapshot_cannot_leak(self, tmp_path):
        """
        After prepare_for_rebuild, accessing cascade returns empty snapshot.

        This verifies that pages cannot accidentally resolve values from
        a stale cascade snapshot between reset and rebuild.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "docs").mkdir()

        site = Site(root_path=tmp_path)

        # Build with cascade data
        index_page = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"layout": "special"},
            },
        )
        index_page._site = site

        section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=index_page,
        )
        site.sections = [section]
        site.pages = [index_page]
        site.build_cascade_snapshot()

        assert site.cascade.resolve("docs", "layout") == "special"

        # Reset
        site.prepare_for_rebuild()

        # Between reset and rebuild, cascade should be empty
        assert site.cascade.resolve("docs", "layout") is None

    def test_cascade_view_invalidated_after_rebuild(self, tmp_path):
        """
        CascadeView cache key (id(snapshot)) invalidates when snapshot changes.

        After prepare_for_rebuild + rebuild, old CascadeView caches on pages
        must not return stale values.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "blog").mkdir()

        site = Site(root_path=tmp_path)

        # First build with layout=alpha
        index_page = Page(
            source_path=content_dir / "blog" / "_index.md",
            _raw_metadata={
                "title": "Blog",
                "cascade": {"layout": "alpha"},
            },
        )
        index_page._site = site

        section = Section(
            name="blog",
            path=content_dir / "blog",
            pages=[],
            index_page=index_page,
        )

        child = Page(
            source_path=content_dir / "blog" / "post.md",
            _raw_metadata={"title": "Post"},
        )
        child._site = site
        child._section_path = content_dir / "blog"
        section.pages.append(child)

        site.sections = [section]
        site.pages = [index_page, child]
        site.build_cascade_snapshot()

        first_snapshot_id = id(site._cascade_snapshot)
        assert child.metadata.get("layout") == "alpha"

        # Rebuild with layout=beta
        site.prepare_for_rebuild()

        new_index = Page(
            source_path=content_dir / "blog" / "_index.md",
            _raw_metadata={
                "title": "Blog",
                "cascade": {"layout": "beta"},
            },
        )
        new_index._site = site

        new_section = Section(
            name="blog",
            path=content_dir / "blog",
            pages=[],
            index_page=new_index,
        )

        # Same child page object survives (simulates reuse)
        child._metadata_view_cache = None  # Reset cache
        child._metadata_view_cache_key = None
        new_section.pages.append(child)

        site.sections = [new_section]
        site.pages = [new_index, child]
        site.build_cascade_snapshot()

        # Snapshot should be a new object
        assert id(site._cascade_snapshot) != first_snapshot_id

        # Child should see the NEW cascade value
        assert child.metadata.get("layout") == "beta"


class TestBuildStateDelegation:
    """
    Tests that per-build state delegates to BuildState when available.

    During builds, BuildState is the primary source of truth for cascade,
    template caches, features_detected, and discovery timing. These tests
    verify the delegation works correctly.
    """

    def test_cascade_delegates_to_build_state(self, tmp_path):
        """
        When BuildState is set, site.cascade reads from BuildState.cascade_snapshot.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "docs").mkdir()

        site = Site(root_path=tmp_path)

        # Set up BuildState with a cascade snapshot
        bs = BuildState()
        site.set_build_state(bs)

        # Build cascade — should write to BuildState
        index_page = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"type": "doc"},
            },
        )
        index_page._site = site

        section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=index_page,
        )
        site.sections = [section]
        site.pages = [index_page]
        site.build_cascade_snapshot()

        # BuildState should have the snapshot
        assert bs.cascade_snapshot is not None
        assert len(bs.cascade_snapshot) > 0

        # site.cascade should delegate to BuildState
        assert site.cascade is bs.cascade_snapshot

        # Local fallback should also be populated
        assert site._cascade_snapshot is not None

    def test_cascade_falls_back_without_build_state(self, tmp_path):
        """
        Without BuildState, site.cascade falls back to local _cascade_snapshot.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "docs").mkdir()

        site = Site(root_path=tmp_path)

        # No BuildState set — common in tests
        assert site.build_state is None

        index_page = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"type": "doc"},
            },
        )
        index_page._site = site

        section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=index_page,
        )
        site.sections = [section]
        site.pages = [index_page]
        site.build_cascade_snapshot()

        # Should use local fallback
        assert site._cascade_snapshot is not None
        assert site.cascade is site._cascade_snapshot

    def test_cascade_structurally_fresh_with_new_build_state(self, tmp_path):
        """
        When a new BuildState is created (simulating a warm rebuild), the
        cascade is structurally fresh even without prepare_for_rebuild()
        resetting _cascade_snapshot.
        """
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "docs").mkdir()

        site = Site(root_path=tmp_path)

        # First "build" — set BuildState with cascade
        bs1 = BuildState()
        site.set_build_state(bs1)

        index_page = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"layout": "alpha"},
            },
        )
        index_page._site = site
        section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=index_page,
        )
        site.sections = [section]
        site.pages = [index_page]
        site.build_cascade_snapshot()

        assert site.cascade.resolve("docs", "layout") == "alpha"
        old_snapshot = bs1.cascade_snapshot

        # Simulate warm rebuild: new BuildState (structurally fresh)
        bs2 = BuildState()
        site.set_build_state(bs2)

        # Without rebuild, BuildState.cascade_snapshot is None
        # site.cascade should still return old local fallback
        # (not ideal, but safe — prepare_for_rebuild resets it)
        assert bs2.cascade_snapshot is None

        # Now rebuild with different cascade data
        new_index = Page(
            source_path=content_dir / "docs" / "_index.md",
            _raw_metadata={
                "title": "Docs",
                "cascade": {"layout": "beta"},
            },
        )
        new_index._site = site
        new_section = Section(
            name="docs",
            path=content_dir / "docs",
            pages=[],
            index_page=new_index,
        )
        site.sections = [new_section]
        site.pages = [new_index]
        site.build_cascade_snapshot()

        # New BuildState has the new snapshot
        assert bs2.cascade_snapshot is not old_snapshot
        assert site.cascade.resolve("docs", "layout") == "beta"

        # Old BuildState is NOT affected
        assert bs1.cascade_snapshot is old_snapshot

    def test_features_detected_on_build_state(self, tmp_path):
        """BuildState.features_detected is independent from Site.features_detected."""
        site = Site(root_path=tmp_path)
        bs = BuildState()
        site.set_build_state(bs)

        # Write to BuildState
        bs.features_detected.add("mermaid")
        bs.features_detected.add("data_tables")

        # Site field should be separate
        assert "mermaid" not in site.features_detected

        # BuildState should have the features
        assert bs.features_detected == {"mermaid", "data_tables"}

        # New BuildState is fresh
        bs2 = BuildState()
        assert bs2.features_detected == set()

    def test_discovery_timing_on_build_state(self, tmp_path):
        """BuildState.discovery_timing_ms is fresh each build."""
        site = Site(root_path=tmp_path)
        bs = BuildState()
        site.set_build_state(bs)

        bs.discovery_timing_ms = {"pages": 100.0, "total": 200.0}

        # New BuildState is fresh
        bs2 = BuildState()
        assert bs2.discovery_timing_ms == {}

    def test_template_caches_on_build_state(self, tmp_path):
        """BuildState template caches are fresh each build."""
        bs = BuildState()

        # Set caches
        bs.theme_chain_cache = {"key": ("default", "/tmp"), "chain": ["default"]}
        bs.template_dirs_cache = {"key": ("default", "/tmp"), "template_dirs": ["/tmp/templates"]}
        bs.template_metadata_cache = {"key": "x", "metadata": {"engine": "bengal"}}

        # Verify they're set
        assert bs.theme_chain_cache is not None
        assert bs.template_dirs_cache is not None
        assert bs.template_metadata_cache is not None

        # New BuildState is structurally fresh
        bs2 = BuildState()
        assert bs2.theme_chain_cache is None
        assert bs2.template_dirs_cache is None
        assert bs2.template_metadata_cache is None

    def test_build_state_cleared_after_build(self, tmp_path):
        """After build completes, BuildState is cleared from Site."""
        site = Site(root_path=tmp_path)
        bs = BuildState()
        site.set_build_state(bs)

        assert site.build_state is bs

        # Simulate build end
        site.set_build_state(None)

        assert site.build_state is None
        # cascade falls back to local
        assert len(site.cascade) == 0  # empty snapshot
