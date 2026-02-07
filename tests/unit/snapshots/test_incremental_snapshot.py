"""
Tests for incremental snapshot updates (Phase 2a).

RFC: Snapshot-Enabled v2 Opportunities (Opportunity 2)

Tests cover:
- update_snapshot() with structural sharing
- O(changed) performance for single-file changes
- Template change propagation
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from bengal.snapshots import (
    ShadowModeValidator,
    SpeculativeRenderer,
    predict_affected,
)
from bengal.snapshots.types import NO_SECTION, PageSnapshot, SiteSnapshot

# =============================================================================
# predict_affected() Tests
# =============================================================================


class TestPredictAffected:
    """Tests for predict_affected() heuristic prediction."""

    def _create_mock_snapshot(
        self,
        pages: list[tuple[str, str]],  # (source_path, template_name)
    ) -> SiteSnapshot:
        """Create a mock snapshot for testing."""
        page_snapshots = []
        template_groups: dict[str, list[PageSnapshot]] = {}

        for i, (path_str, template) in enumerate(pages):
            # Note: PageSnapshot is frozen dataclass but contains toc_items
            # which has dicts inside - we use frozenset for the set operations
            page = PageSnapshot(
                title=Path(path_str).stem,
                href=f"/{Path(path_str).stem}/",
                source_path=Path(path_str),
                output_path=Path(f"public/{Path(path_str).stem}/index.html"),
                template_name=template,
                content="",
                parsed_html="",
                toc="",
                toc_items=(),  # Empty tuple is hashable
                excerpt="",
                metadata=MappingProxyType({}),
                tags=(),
                categories=(),
                reading_time=1,
                word_count=100,
                content_hash=f"hash{i}",  # Unique hash for each page
                section=NO_SECTION,
            )
            page_snapshots.append(page)
            template_groups.setdefault(template, []).append(page)

        return SiteSnapshot(
            pages=tuple(page_snapshots),
            regular_pages=tuple(page_snapshots),
            sections=(),
            root_section=NO_SECTION,
            config=MappingProxyType({}),
            params=MappingProxyType({}),
            data=MappingProxyType({}),
            menus=MappingProxyType({}),
            taxonomies=MappingProxyType({}),
            topological_order=(),
            template_groups=MappingProxyType({k: tuple(v) for k, v in template_groups.items()}),
            attention_order=tuple(page_snapshots),
            scout_hints=(),
            snapshot_time=0.0,
            page_count=len(page_snapshots),
            section_count=0,
            templates=MappingProxyType({}),
            template_dependency_graph=MappingProxyType({}),
            template_dependents=MappingProxyType({}),
        )

    def test_markdown_file_predicts_single_page(self):
        """Test that .md file change predicts only that page."""
        snapshot = self._create_mock_snapshot(
            [
                ("content/index.md", "page.html"),
                ("content/about.md", "page.html"),
                ("content/docs/guide.md", "doc.html"),
            ]
        )

        affected = predict_affected(Path("content/about.md"), snapshot)

        assert len(affected) == 1
        assert list(affected)[0].source_path == Path("content/about.md")

    def test_template_file_predicts_using_pages(self):
        """Test that .html template change predicts pages using it."""
        snapshot = self._create_mock_snapshot(
            [
                ("content/index.md", "page.html"),
                ("content/about.md", "page.html"),
                ("content/docs/guide.md", "doc.html"),
            ]
        )

        affected = predict_affected(Path("templates/page.html"), snapshot)

        # Should include pages using page.html
        assert len(affected) >= 2
        paths = {p.source_path for p in affected}
        assert Path("content/index.md") in paths
        assert Path("content/about.md") in paths

    def test_css_file_predicts_all_pages(self):
        """Test that CSS change predicts all pages (conservative)."""
        snapshot = self._create_mock_snapshot(
            [
                ("content/index.md", "page.html"),
                ("content/about.md", "page.html"),
            ]
        )

        affected = predict_affected(Path("assets/style.css"), snapshot)

        assert len(affected) == len(snapshot.pages)

    def test_image_file_predicts_none(self):
        """Test that image change predicts no pages."""
        snapshot = self._create_mock_snapshot(
            [
                ("content/index.md", "page.html"),
            ]
        )

        affected = predict_affected(Path("assets/logo.png"), snapshot)

        assert len(affected) == 0

    def test_unknown_file_type_conservative(self):
        """Test that unknown file type is conservative (all pages)."""
        snapshot = self._create_mock_snapshot(
            [
                ("content/index.md", "page.html"),
                ("content/about.md", "page.html"),
            ]
        )

        affected = predict_affected(Path("unknown.xyz"), snapshot)

        assert len(affected) == len(snapshot.pages)


# =============================================================================
# SpeculativeRenderer Tests
# =============================================================================


class TestSpeculativeRenderer:
    """Tests for SpeculativeRenderer class."""

    def _create_mock_snapshot(self) -> SiteSnapshot:
        """Create a minimal mock snapshot."""
        return SiteSnapshot(
            pages=(),
            regular_pages=(),
            sections=(),
            root_section=NO_SECTION,
            config=MappingProxyType({}),
            params=MappingProxyType({}),
            data=MappingProxyType({}),
            menus=MappingProxyType({}),
            taxonomies=MappingProxyType({}),
            topological_order=(),
            template_groups=MappingProxyType({}),
            attention_order=(),
            scout_hints=(),
            snapshot_time=0.0,
            page_count=0,
            section_count=0,
        )

    def test_initial_accuracy_is_default(self):
        """Test that initial accuracy uses default assumption."""
        snapshot = self._create_mock_snapshot()
        renderer = SpeculativeRenderer(snapshot)

        assert renderer.prediction_accuracy == 0.9  # Default

    def test_should_speculate_with_high_accuracy(self):
        """Test that speculation is enabled with high accuracy."""
        snapshot = self._create_mock_snapshot()
        renderer = SpeculativeRenderer(snapshot)

        # Record high-accuracy predictions
        for _ in range(10):
            renderer.record_prediction_result(5, 5)  # 100% accurate

        assert renderer.should_speculate() is True

    def test_should_not_speculate_with_low_accuracy(self):
        """Test that speculation is disabled with low accuracy."""
        snapshot = self._create_mock_snapshot()
        renderer = SpeculativeRenderer(snapshot)

        # Record low-accuracy predictions
        for _ in range(10):
            renderer.record_prediction_result(10, 2)  # Very inaccurate

        assert renderer.should_speculate() is False

    def test_validate_speculation_records_history(self):
        """Test that validation records prediction history."""
        snapshot = self._create_mock_snapshot()
        renderer = SpeculativeRenderer(snapshot)

        page1 = PageSnapshot(
            title="Test",
            href="/test/",
            source_path=Path("test.md"),
            output_path=Path("public/test/index.html"),
            template_name="page.html",
            content="",
            parsed_html="",
            toc="",
            toc_items=(),
            excerpt="",
            metadata=MappingProxyType({}),
            tags=(),
            categories=(),
            reading_time=1,
            word_count=100,
            content_hash="abc",
            section=NO_SECTION,
        )

        predicted = {page1}
        actual = {page1}

        result = renderer.validate_speculation(predicted, actual)

        assert result["hits"] == 1
        assert result["misses"] == 0
        assert result["accuracy"] == 1.0


# =============================================================================
# ShadowModeValidator Tests
# =============================================================================


class TestShadowModeValidator:
    """Tests for ShadowModeValidator class."""

    def _create_page(self, name: str) -> PageSnapshot:
        """Create a mock page snapshot."""
        return PageSnapshot(
            title=name,
            href=f"/{name}/",
            source_path=Path(f"content/{name}.md"),
            output_path=Path(f"public/{name}/index.html"),
            template_name="page.html",
            content="",
            parsed_html="",
            toc="",
            toc_items=(),
            excerpt="",
            metadata=MappingProxyType({}),
            tags=(),
            categories=(),
            reading_time=1,
            word_count=100,
            content_hash="abc",
            section=NO_SECTION,
        )

    def _create_mock_snapshot(self, pages: list[PageSnapshot]) -> SiteSnapshot:
        """Create a mock snapshot with given pages."""
        return SiteSnapshot(
            pages=tuple(pages),
            regular_pages=tuple(pages),
            sections=(),
            root_section=NO_SECTION,
            config=MappingProxyType({}),
            params=MappingProxyType({}),
            data=MappingProxyType({}),
            menus=MappingProxyType({}),
            taxonomies=MappingProxyType({}),
            topological_order=(),
            template_groups=MappingProxyType({}),
            attention_order=tuple(pages),
            scout_hints=(),
            snapshot_time=0.0,
            page_count=len(pages),
            section_count=0,
        )

    def test_validate_perfect_prediction(self):
        """Test validation with perfect prediction."""
        validator = ShadowModeValidator()

        page = self._create_page("test")
        snapshot = self._create_mock_snapshot([page])

        result = validator.validate(
            file_path=page.source_path,
            snapshot=snapshot,
            actual_affected={page},
        )

        assert result["accuracy"] == 1.0
        assert result["hit_count"] == 1
        assert result["miss_count"] == 0

    def test_overall_accuracy_tracking(self):
        """Test that overall accuracy is tracked across validations."""
        validator = ShadowModeValidator()

        page1 = self._create_page("page1")
        page2 = self._create_page("page2")
        snapshot = self._create_mock_snapshot([page1, page2])

        # First validation - perfect
        validator.validate(page1.source_path, snapshot, {page1})

        # Second validation - also perfect
        validator.validate(page2.source_path, snapshot, {page2})

        assert validator.overall_accuracy == 1.0

    def test_get_report(self):
        """Test report generation."""
        validator = ShadowModeValidator()

        page = self._create_page("test")
        snapshot = self._create_mock_snapshot([page])

        validator.validate(page.source_path, snapshot, {page})

        report = validator.get_report()

        assert "total_validations" in report
        assert "overall_accuracy" in report
        assert "recommendation" in report
        assert report["total_validations"] == 1

    def test_recommendation_based_on_accuracy(self):
        """Test that recommendation depends on accuracy."""
        validator = ShadowModeValidator()

        page = self._create_page("test")
        snapshot = self._create_mock_snapshot([page])

        # Add high-accuracy validations
        for _ in range(10):
            validator.validate(page.source_path, snapshot, {page})

        report = validator.get_report()

        assert report["recommendation"] == "Enable speculation"


# =============================================================================
# Integration Tests (require full site fixtures)
# =============================================================================


@pytest.mark.bengal(testroot="test-basic")
class TestUpdateSnapshotIntegration:
    """Integration tests for update_snapshot()."""

    def test_update_snapshot_with_no_changes(self, site, build_site):
        """Test that no changes returns same snapshot."""
        from bengal.snapshots import create_site_snapshot, update_snapshot

        build_site()
        original = create_site_snapshot(site)

        updated = update_snapshot(original, site, set())

        # Should return same snapshot object
        assert updated is original

    def test_update_snapshot_preserves_unchanged_pages(self, site, build_site):
        """Test structural sharing for unchanged pages."""
        from bengal.snapshots import create_site_snapshot, update_snapshot

        build_site()
        original = create_site_snapshot(site)

        if not original.pages:
            pytest.skip("No pages in test site")

        # Change one file
        changed = {original.pages[0].source_path}
        updated = update_snapshot(original, site, changed)

        # Config should be reused (structural sharing)
        assert updated.config is original.config
        assert updated.params is original.params
        assert updated.data is original.data
