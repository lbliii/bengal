"""Tests for cascade propagation through warm rebuild + template resolution.

These tests target the untested seam between three subsystems:
  1. Cascade propagation (type:/layout:/template: from _index.md → child pages)
  2. Warm rebuild lifecycle (prepare_for_rebuild → build on same Site instance)
  3. Template resolution (_get_template_name uses page.type from cascade)

The goal is to surface bugs where warm rebuilds cause cascaded fields to
disappear, leading to wrong template selection or emergency fallback HTML.

Each test uses a single Site instance across multiple discover_content() calls
(simulating warm rebuilds) rather than creating fresh Site instances, which is
how the dev server actually operates.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from bengal.core.site import Site


@pytest.fixture
def temp_site():
    """Create a temporary site directory with minimal config."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "bengal.toml").write_text(
        '[site]\ntitle = "Cascade Rebuild Test"\nbaseurl = "/"\n\n'
        '[build]\ncontent_dir = "content"\noutput_dir = "public"\ntheme = "default"\n\n'
        "[markdown]\n"
    )
    yield temp_dir
    shutil.rmtree(temp_dir)


def _discover(site: Site) -> None:
    """Run content discovery on a site (used by warm rebuild simulation)."""
    content_dir = site.root_path / "content"
    site.discover_content(content_dir)


def _warm_rebuild(site: Site) -> None:
    """Simulate the warm rebuild cycle: clear state → re-discover.

    This is what BuildTrigger._execute_build does (minus the actual render/write).
    """
    site.prepare_for_rebuild()
    _discover(site)


def _find_page(site: Site, name_fragment: str):
    """Find a page by substring match on source_path."""
    matches = [p for p in site.pages if name_fragment in str(p.source_path)]
    assert matches, (
        f"No page found matching '{name_fragment}' in {[str(p.source_path) for p in site.pages]}"
    )
    return matches[0]


# ---------------------------------------------------------------------------
# 1. Cascade type: survives prepare_for_rebuild on same Site instance
# ---------------------------------------------------------------------------


class TestCascadeSurvivesWarmRebuild:
    """Verify cascaded fields persist when the SAME Site object is reused."""

    def test_type_persists_after_warm_rebuild(self, temp_site: Path) -> None:
        """Cascaded type: must be present after prepare_for_rebuild + re-discover."""
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)

        (content / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (content / "setup.md").write_text("---\ntitle: Setup Guide\n---\nHow to set up.\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "setup").metadata.get("type") == "doc"

        _warm_rebuild(site)
        assert _find_page(site, "setup").metadata.get("type") == "doc", (
            "Cascaded type: lost after warm rebuild"
        )

    def test_multiple_warm_rebuilds_stable(self, temp_site: Path) -> None:
        """Cascade must be stable through 5 consecutive warm rebuilds."""
        content = temp_site / "content" / "blog"
        content.mkdir(parents=True)

        (content / "_index.md").write_text(
            "---\ntitle: Blog\ncascade:\n  type: post\n  layout: blog-layout\n---\n"
        )
        (content / "hello.md").write_text("---\ntitle: Hello World\n---\nFirst post.\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        for i in range(5):
            _warm_rebuild(site)
            page = _find_page(site, "hello")
            assert page.metadata.get("type") == "post", f"type: lost on rebuild {i + 1}"
            assert page.metadata.get("layout") == "blog-layout", f"layout: lost on rebuild {i + 1}"

    def test_deep_nested_cascade_survives_warm_rebuild(self, temp_site: Path) -> None:
        """3-level nested cascade: docs → api → v2 → page."""
        docs = temp_site / "content" / "docs"
        api = docs / "api"
        v2 = api / "v2"
        v2.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (api / "_index.md").write_text("---\ntitle: API\ncascade:\n  variant: api-sidebar\n---\n")
        (v2 / "_index.md").write_text("---\ntitle: API v2\n---\n")
        (v2 / "endpoints.md").write_text("---\ntitle: Endpoints\n---\nEndpoint docs.\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "endpoints")
        assert page.metadata.get("type") == "doc"
        assert page.metadata.get("variant") == "api-sidebar"

        _warm_rebuild(site)

        page = _find_page(site, "endpoints")
        assert page.metadata.get("type") == "doc", "Deep cascaded type: lost after warm rebuild"
        assert page.metadata.get("variant") == "api-sidebar", "Deep cascaded variant: lost"


# ---------------------------------------------------------------------------
# 2. Cascade changes between warm rebuilds
# ---------------------------------------------------------------------------


class TestCascadeChangesAcrossRebuilds:
    """Verify cascade updates/additions/removals propagate correctly."""

    def test_cascade_value_update_propagates(self, temp_site: Path) -> None:
        """Changing cascade version in _index.md must propagate on warm rebuild."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text(
            "---\ntitle: Docs\ncascade:\n  type: doc\n  version: '1.0'\n---\n"
        )
        (docs / "guide.md").write_text("---\ntitle: Guide\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "guide").metadata.get("version") == "1.0"

        # Change cascade version
        (docs / "_index.md").write_text(
            "---\ntitle: Docs\ncascade:\n  type: doc\n  version: '2.0'\n---\n"
        )

        _warm_rebuild(site)
        assert _find_page(site, "guide").metadata.get("version") == "2.0", (
            "Updated cascade value not propagated after warm rebuild"
        )

    def test_cascade_added_between_rebuilds(self, temp_site: Path) -> None:
        """Adding cascade to a section mid-session must take effect."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        # Start without cascade
        (docs / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (docs / "intro.md").write_text("---\ntitle: Intro\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "intro").metadata.get("type") is None

        # Add cascade
        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")

        _warm_rebuild(site)
        assert _find_page(site, "intro").metadata.get("type") == "doc", (
            "Newly added cascade not picked up after warm rebuild"
        )

    def test_cascade_removed_between_rebuilds(self, temp_site: Path) -> None:
        """Removing cascade from _index.md must stop propagation."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "guide.md").write_text("---\ntitle: Guide\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "guide").metadata.get("type") == "doc"

        # Remove cascade
        (docs / "_index.md").write_text("---\ntitle: Docs\n---\n")

        _warm_rebuild(site)
        assert _find_page(site, "guide").metadata.get("type") is None, (
            "Removed cascade still present after warm rebuild"
        )

    def test_new_section_with_cascade_mid_session(self, temp_site: Path) -> None:
        """Adding an entirely new section with cascade mid-session."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)
        (docs / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        # Add new section with cascade
        blog = temp_site / "content" / "blog"
        blog.mkdir(parents=True)
        (blog / "_index.md").write_text("---\ntitle: Blog\ncascade:\n  type: post\n---\n")
        (blog / "first.md").write_text("---\ntitle: First Post\n---\n")

        _warm_rebuild(site)

        assert _find_page(site, "first").metadata.get("type") == "post"
        # Original section should be unaffected
        assert _find_page(site, "page").metadata.get("type") is None

    def test_section_removed_cascade_clears(self, temp_site: Path) -> None:
        """Removing a section directory must clear its cascade for any remaining pages."""
        docs = temp_site / "content" / "docs"
        blog = temp_site / "content" / "blog"
        docs.mkdir(parents=True)
        blog.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "guide.md").write_text("---\ntitle: Guide\n---\n")
        (blog / "_index.md").write_text("---\ntitle: Blog\ncascade:\n  type: post\n---\n")
        (blog / "hello.md").write_text("---\ntitle: Hello\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "guide").metadata.get("type") == "doc"
        assert _find_page(site, "hello").metadata.get("type") == "post"

        # Remove blog section
        shutil.rmtree(blog)

        _warm_rebuild(site)
        # Docs cascade should survive
        assert _find_page(site, "guide").metadata.get("type") == "doc"
        # Blog pages should be gone
        assert not any("hello" in str(p.source_path) for p in site.pages)


# ---------------------------------------------------------------------------
# 3. Frontmatter override of cascade through warm rebuilds
# ---------------------------------------------------------------------------


class TestFrontmatterOverrideCascadeRebuild:
    """Verify frontmatter overrides survive warm rebuilds and don't leak."""

    def test_override_persists(self, temp_site: Path) -> None:
        """Page-level type: override must persist through warm rebuild."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "regular.md").write_text("---\ntitle: Regular\n---\n")
        (docs / "special.md").write_text("---\ntitle: Special\ntype: custom-type\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        assert _find_page(site, "regular").metadata.get("type") == "doc"
        assert _find_page(site, "special").metadata.get("type") == "custom-type"

        _warm_rebuild(site)

        assert _find_page(site, "regular").metadata.get("type") == "doc", (
            "Cascade type: lost after warm rebuild"
        )
        assert _find_page(site, "special").metadata.get("type") == "custom-type", (
            "Frontmatter override lost after warm rebuild"
        )

    def test_override_added_mid_session(self, temp_site: Path) -> None:
        """Adding frontmatter override between builds must take effect."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "page").metadata.get("type") == "doc"

        # Add frontmatter override
        (docs / "page.md").write_text("---\ntitle: Page\ntype: special\n---\n")

        _warm_rebuild(site)
        assert _find_page(site, "page").metadata.get("type") == "special", (
            "Frontmatter override not applied after warm rebuild"
        )

    def test_override_removed_falls_back_to_cascade(self, temp_site: Path) -> None:
        """Removing frontmatter override must restore cascade value."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\ntype: custom\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        assert _find_page(site, "page").metadata.get("type") == "custom"

        # Remove override
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        _warm_rebuild(site)
        assert _find_page(site, "page").metadata.get("type") == "doc", (
            "Cascade not restored after frontmatter override removed"
        )


# ---------------------------------------------------------------------------
# 4. page.type property matches page.metadata.get("type") through rebuilds
# ---------------------------------------------------------------------------


class TestTypePropertyDualityRebuild:
    """The page.type property and metadata.get('type') must always agree.

    Template resolution uses page.type. If it diverges from metadata.get('type'),
    the template lookup uses a different value than what the context provides.
    """

    def test_type_property_equals_metadata_after_rebuild(self, temp_site: Path) -> None:
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)

        (content / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (content / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        for _ in range(3):
            _warm_rebuild(site)
            page = _find_page(site, "page")
            assert page.type == page.metadata.get("type"), (
                f"page.type ({page.type!r}) != metadata.get('type') "
                f"({page.metadata.get('type')!r}) after warm rebuild"
            )
            assert page.type == "doc"

    def test_type_duality_with_override(self, temp_site: Path) -> None:
        content = temp_site / "content" / "docs"
        content.mkdir(parents=True)

        (content / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (content / "special.md").write_text("---\ntitle: Special\ntype: custom\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        _warm_rebuild(site)

        page = _find_page(site, "special")
        assert page.type == "custom"
        assert page.type == page.metadata.get("type")


# ---------------------------------------------------------------------------
# 5. Cascade snapshot correctness through warm rebuild
# ---------------------------------------------------------------------------


class TestCascadeSnapshotRebuild:
    """Verify the CascadeSnapshot object is correctly rebuilt."""

    def test_snapshot_not_none_after_warm_rebuild(self, temp_site: Path) -> None:
        """site.cascade must not be None or empty after warm rebuild."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        cascade_before = site.cascade
        assert cascade_before is not None

        _warm_rebuild(site)

        cascade_after = site.cascade
        assert cascade_after is not None, "Cascade snapshot is None after warm rebuild"

    def test_snapshot_isolation_between_sections(self, temp_site: Path) -> None:
        """Cascade from section A must not leak into section B after rebuild."""
        content = temp_site / "content"
        (content / "blog").mkdir(parents=True)
        (content / "docs").mkdir(parents=True)

        (content / "blog" / "_index.md").write_text(
            "---\ntitle: Blog\ncascade:\n  type: post\n  author: Blog Team\n---\n"
        )
        (content / "blog" / "entry.md").write_text("---\ntitle: Entry\n---\n")
        (content / "docs" / "_index.md").write_text(
            "---\ntitle: Docs\ncascade:\n  type: doc\n---\n"
        )
        (content / "docs" / "guide.md").write_text("---\ntitle: Guide\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        _warm_rebuild(site)
        _warm_rebuild(site)

        entry = _find_page(site, "entry")
        guide = _find_page(site, "guide")

        assert entry.metadata.get("type") == "post"
        assert entry.metadata.get("author") == "Blog Team"
        assert guide.metadata.get("type") == "doc"
        assert guide.metadata.get("author") is None, "Blog cascade leaked into docs"


# ---------------------------------------------------------------------------
# 6. Content additions/deletions during warm rebuild
# ---------------------------------------------------------------------------


class TestContentChurnWarmRebuild:
    """Simulate rapid content edits that trigger multiple warm rebuilds."""

    def test_add_page_to_cascaded_section(self, temp_site: Path) -> None:
        """New page added to section with cascade picks up cascade on rebuild."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "existing.md").write_text("---\ntitle: Existing\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        # Add new page between rebuilds
        (docs / "new-page.md").write_text("---\ntitle: New Page\n---\n")

        _warm_rebuild(site)
        new_page = _find_page(site, "new-page")
        assert new_page.metadata.get("type") == "doc", "Newly added page did not pick up cascade"

    def test_delete_page_cascade_still_works_for_siblings(self, temp_site: Path) -> None:
        """Deleting a page must not break cascade for remaining siblings."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "keep.md").write_text("---\ntitle: Keep\n---\n")
        (docs / "delete-me.md").write_text("---\ntitle: Delete Me\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        (docs / "delete-me.md").unlink()

        _warm_rebuild(site)
        keep = _find_page(site, "keep")
        assert keep.metadata.get("type") == "doc", "Sibling lost cascade after page deletion"

    def test_rapid_edit_cycle(self, temp_site: Path) -> None:
        """Simulate 10 rapid edits to a page in a cascaded section."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page v0\n---\nInitial.\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        for i in range(1, 11):
            (docs / "page.md").write_text(f"---\ntitle: Page v{i}\n---\nEdit {i}.\n")
            _warm_rebuild(site)

            page = _find_page(site, "page")
            assert page.metadata.get("type") == "doc", f"Cascade lost on edit {i}"
            assert page.metadata.get("title") == f"Page v{i}"


# ---------------------------------------------------------------------------
# 7. Cascade + section_path assignment
# ---------------------------------------------------------------------------


class TestSectionPathAssignment:
    """page._section_path is the key for cascade resolution.

    If it's wrong or missing after warm rebuild, cascade silently fails.
    """

    def test_section_path_set_after_warm_rebuild(self, temp_site: Path) -> None:
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "page")
        section_path_before = getattr(page, "_section_path", None)
        assert section_path_before is not None, "_section_path not set after initial discover"

        _warm_rebuild(site)

        page = _find_page(site, "page")
        section_path_after = getattr(page, "_section_path", None)
        assert section_path_after is not None, "_section_path not set after warm rebuild"

    def test_section_path_correct_for_nested(self, temp_site: Path) -> None:
        docs = temp_site / "content" / "docs"
        api = docs / "api"
        api.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\n---\n")
        (api / "_index.md").write_text("---\ntitle: API\n---\n")
        (api / "auth.md").write_text("---\ntitle: Auth\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        _warm_rebuild(site)

        auth = _find_page(site, "auth")
        section_path = getattr(auth, "_section_path", "")
        assert "api" in str(section_path), (
            f"Expected section_path to contain 'api', got {section_path!r}"
        )


# ---------------------------------------------------------------------------
# 8. Cascade with mixed page types (index + regular + generated-like)
# ---------------------------------------------------------------------------


class TestMixedPageTypesCascade:
    """Section index pages and regular pages both resolve cascade correctly."""

    def test_section_index_gets_cascade(self, temp_site: Path) -> None:
        """_index.md pages should also see their own section's cascade."""
        docs = temp_site / "content" / "docs"
        sub = docs / "getting-started"
        sub.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (sub / "_index.md").write_text("---\ntitle: Getting Started\n---\n")
        (sub / "install.md").write_text("---\ntitle: Install\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        _warm_rebuild(site)

        sub_index = _find_page(site, "getting-started/_index")
        install = _find_page(site, "install")

        assert sub_index.metadata.get("type") == "doc", "Section index page did not inherit cascade"
        assert install.metadata.get("type") == "doc"

    def test_root_index_no_cascade_leak(self, temp_site: Path) -> None:
        """Root content/index.md should not pick up cascade from subsections."""
        content = temp_site / "content"
        content.mkdir(parents=True)
        docs = content / "docs"
        docs.mkdir(parents=True)

        (content / "index.md").write_text("---\ntitle: Home\n---\nWelcome.\n")
        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)
        _warm_rebuild(site)

        home_matches = [p for p in site.pages if str(p.source_path).endswith("content/index.md")]
        assert home_matches, "Root index.md not found"
        home = home_matches[0]
        doc_page = _find_page(site, "docs/page")

        assert home.metadata.get("type") is None, (
            f"Root index picked up docs cascade: type={home.metadata.get('type')}"
        )
        assert doc_page.metadata.get("type") == "doc"


# ---------------------------------------------------------------------------
# 9. Template resolution uses cascade-derived type through warm rebuilds
# ---------------------------------------------------------------------------


class TestTemplateResolutionFromCascade:
    """Verify _get_template_name uses cascade-derived page.type correctly.

    This is the critical integration point: cascade assigns type: → renderer
    resolves to a content-type-specific template → correct HTML. If this
    chain breaks on warm rebuild, we get emergency fallback HTML.
    """

    def test_cascaded_type_selects_strategy_template(self, temp_site: Path) -> None:
        """Cascade type: 'blog' should route through BlogStrategy template cascade."""
        from bengal.content_types.registry import get_strategy, normalize_page_type_to_content_type
        from bengal.content_types.templates import build_template_cascade, classify_page

        blog = temp_site / "content" / "blog"
        blog.mkdir(parents=True)

        (blog / "_index.md").write_text("---\ntitle: Blog\ncascade:\n  type: blog\n---\n")
        (blog / "post.md").write_text("---\ntitle: My Post\n---\nContent.\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "post")
        assert page.type == "blog"

        strategy_type = normalize_page_type_to_content_type(page.type)
        assert strategy_type == "blog", f"Expected 'blog' strategy, got {strategy_type!r}"

        assert get_strategy(strategy_type) is not None
        page_classification = classify_page(page)
        candidates = build_template_cascade("blog", page_classification)
        assert "blog/single.html" in candidates

        # Warm rebuild — verify chain still works
        _warm_rebuild(site)
        page = _find_page(site, "post")
        assert page.type == "blog", "page.type lost after warm rebuild"

        strategy_type_after = normalize_page_type_to_content_type(page.type)
        assert strategy_type_after == "blog", (
            f"Strategy type changed after warm rebuild: {strategy_type_after!r}"
        )

    def test_cascaded_doc_type_selects_doc_strategy(self, temp_site: Path) -> None:
        """Cascade type: 'doc' → DocsStrategy → doc/single.html."""
        from bengal.content_types.registry import normalize_page_type_to_content_type
        from bengal.content_types.templates import build_template_cascade, classify_page

        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "setup.md").write_text("---\ntitle: Setup\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        for rebuild_num in range(3):
            if rebuild_num > 0:
                _warm_rebuild(site)

            page = _find_page(site, "setup")
            assert page.type == "doc", f"page.type wrong on rebuild {rebuild_num}"

            strategy_type = normalize_page_type_to_content_type(page.type)
            assert strategy_type == "doc", f"Strategy wrong on rebuild {rebuild_num}"

            candidates = build_template_cascade("doc", classify_page(page))
            assert candidates[0] == "doc/single.html", (
                f"First template candidate wrong on rebuild {rebuild_num}: {candidates}"
            )

    def test_unregistered_cascade_type_falls_through(self, temp_site: Path) -> None:
        """Cascade type: 'custom-thing' (unregistered) should fall through to section-based."""
        from bengal.content_types.registry import normalize_page_type_to_content_type

        custom = temp_site / "content" / "custom"
        custom.mkdir(parents=True)

        (custom / "_index.md").write_text(
            "---\ntitle: Custom\ncascade:\n  type: custom-thing\n---\n"
        )
        (custom / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "page")
        assert page.type == "custom-thing"
        assert normalize_page_type_to_content_type("custom-thing") is None, (
            "custom-thing should not map to any registered strategy"
        )

        _warm_rebuild(site)
        page = _find_page(site, "page")
        assert page.type == "custom-thing", "Unregistered cascade type lost on rebuild"

    def test_explicit_template_overrides_cascade_type(self, temp_site: Path) -> None:
        """Frontmatter template: takes priority over cascade type: for resolution."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "special.md").write_text("---\ntitle: Special\ntemplate: custom-layout.html\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "special")
        assert page.type == "doc"
        assert page.metadata.get("template") == "custom-layout.html"

        _warm_rebuild(site)
        page = _find_page(site, "special")
        assert page.metadata.get("template") == "custom-layout.html", (
            "Explicit template: lost after warm rebuild"
        )
        assert page.type == "doc", "Cascade type: lost even though template: present"

    def test_section_index_cascade_template_resolution(self, temp_site: Path) -> None:
        """Section _index.md with cascade should resolve list templates correctly."""
        from bengal.content_types.templates import build_template_cascade, classify_page

        blog = temp_site / "content" / "blog"
        blog.mkdir(parents=True)

        (blog / "_index.md").write_text("---\ntitle: Blog\ncascade:\n  type: blog\n---\n")
        (blog / "post1.md").write_text("---\ntitle: Post 1\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        index_page = _find_page(site, "_index")
        classification = classify_page(index_page)
        assert classification == "list", f"Expected 'list', got {classification!r}"

        candidates = build_template_cascade("blog", classification)
        assert "blog/list.html" in candidates
        assert "blog/index.html" in candidates

        _warm_rebuild(site)
        index_page = _find_page(site, "_index")
        assert index_page.type == "blog"
        assert classify_page(index_page) == "list"


# ---------------------------------------------------------------------------
# 10. Cascade key provenance through warm rebuild
# ---------------------------------------------------------------------------


class TestCascadeKeyProvenanceRebuild:
    """Verify cascade_keys() correctly tracks what came from cascade vs frontmatter."""

    def test_cascade_keys_stable_through_rebuild(self, temp_site: Path) -> None:
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text(
            "---\ntitle: Docs\ncascade:\n  type: doc\n  sidebar: true\n---\n"
        )
        (docs / "page.md").write_text("---\ntitle: Page\nauthor: Alice\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "page")
        keys_before = set(page.metadata.cascade_keys())
        assert "type" in keys_before
        assert "sidebar" in keys_before
        assert "author" not in keys_before
        assert "title" not in keys_before

        _warm_rebuild(site)

        page = _find_page(site, "page")
        keys_after = set(page.metadata.cascade_keys())
        assert keys_after == keys_before, (
            f"cascade_keys() changed after rebuild: {keys_before} → {keys_after}"
        )

    def test_provenance_shifts_when_frontmatter_overrides_cascade(self, temp_site: Path) -> None:
        """When frontmatter adds type: override, it should leave cascade_keys."""
        docs = temp_site / "content" / "docs"
        docs.mkdir(parents=True)

        (docs / "_index.md").write_text("---\ntitle: Docs\ncascade:\n  type: doc\n---\n")
        (docs / "page.md").write_text("---\ntitle: Page\n---\n")

        site = Site(root_path=temp_site, config={})
        _discover(site)

        page = _find_page(site, "page")
        assert "type" in page.metadata.cascade_keys()

        # Add frontmatter override
        (docs / "page.md").write_text("---\ntitle: Page\ntype: custom\n---\n")

        _warm_rebuild(site)
        page = _find_page(site, "page")
        assert page.metadata.get("type") == "custom"
        assert "type" not in page.metadata.cascade_keys(), (
            "type should not be in cascade_keys when overridden by frontmatter"
        )
