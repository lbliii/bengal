"""
Tests for build content phases.

Covers:
- phase_sections(): Section finalization phase
- phase_taxonomies(): Taxonomy collection phase
- phase_taxonomy_index(): Taxonomy index persistence
- phase_menus(): Menu building phase
- phase_related_posts(): Related posts computation
- phase_query_indexes(): Query index building
- phase_update_pages_list(): Pages list update
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from bengal.orchestration.build.content import (
    phase_menus,
    phase_query_indexes,
    phase_related_posts,
    phase_sections,
    phase_taxonomies,
    phase_taxonomy_index,
    phase_update_pages_list,
)


class MockPhaseContext:
    """Helper to create mock context for phase functions."""

    @staticmethod
    def create_orchestrator(tmp_path, config=None):
        """Create a mock orchestrator."""
        orchestrator = MagicMock()
        orchestrator.site = MagicMock()
        orchestrator.site.root_path = tmp_path
        orchestrator.site.config = config or {}
        orchestrator.site.pages = []
        orchestrator.site.regular_pages = []
        orchestrator.site.generated_pages = []
        orchestrator.site.sections = []
        orchestrator.site.taxonomies = {}

        orchestrator.stats = MagicMock()
        orchestrator.stats.taxonomy_time_ms = 0
        orchestrator.stats.menu_time_ms = 0
        orchestrator.stats.related_posts_time_ms = 0

        orchestrator.logger = MagicMock()
        orchestrator.logger.phase = MagicMock(
            return_value=MagicMock(__enter__=Mock(), __exit__=Mock())
        )

        orchestrator.sections = MagicMock()
        orchestrator.taxonomy = MagicMock()
        orchestrator.menu = MagicMock()
        orchestrator.incremental = MagicMock()

        return orchestrator

    @staticmethod
    def create_cli():
        """Create a mock CLI."""
        return MagicMock()


class TestPhaseSections:
    """Tests for phase_sections function."""

    def test_finalizes_sections(self, tmp_path):
        """Calls section orchestrator finalize."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        orchestrator.sections.validate_sections.return_value = []

        phase_sections(orchestrator, cli, incremental=False, affected_sections=None)

        orchestrator.sections.finalize_sections.assert_called_once()

    def test_validates_sections(self, tmp_path):
        """Validates section structure after finalization."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        orchestrator.sections.validate_sections.return_value = []

        phase_sections(orchestrator, cli, incremental=False, affected_sections=None)

        orchestrator.sections.validate_sections.assert_called_once()

    def test_skips_when_no_affected_sections_incremental(self, tmp_path):
        """Skips finalization when no sections affected in incremental build."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()

        # Empty set means no affected sections
        phase_sections(orchestrator, cli, incremental=True, affected_sections=set())

        # Should skip finalization
        orchestrator.sections.finalize_sections.assert_not_called()

    def test_raises_in_strict_mode_with_errors(self, tmp_path):
        """Raises exception in strict mode with validation errors."""
        # Create orchestrator with strict_mode directly in config
        orchestrator = MagicMock()
        orchestrator.site = MagicMock()
        orchestrator.site.root_path = tmp_path
        orchestrator.site.config = {"strict_mode": True}  # Real dict

        # Setup logger context manager
        orchestrator.logger = MagicMock()
        orchestrator.logger.phase = MagicMock(
            return_value=MagicMock(
                __enter__=Mock(return_value=None), __exit__=Mock(return_value=False)
            )
        )

        # Setup sections with validation errors
        orchestrator.sections = MagicMock()
        orchestrator.sections.validate_sections.return_value = ["Error 1", "Error 2"]

        cli = MockPhaseContext.create_cli()

        with pytest.raises(Exception, match="Build failed"):
            phase_sections(orchestrator, cli, incremental=False, affected_sections=None)

    def test_warns_in_non_strict_mode_with_errors(self, tmp_path):
        """Warns but continues in non-strict mode with validation errors."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path, config={"strict_mode": False})
        cli = MockPhaseContext.create_cli()
        orchestrator.sections.validate_sections.return_value = ["Error 1"]

        # Should not raise
        phase_sections(orchestrator, cli, incremental=False, affected_sections=None)

        cli.warning.assert_called()

    def test_invalidates_page_cache(self, tmp_path):
        """Invalidates regular_pages cache after finalization."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cli = MockPhaseContext.create_cli()
        orchestrator.sections.validate_sections.return_value = []

        phase_sections(orchestrator, cli, incremental=False, affected_sections=None)

        orchestrator.site.invalidate_regular_pages_cache.assert_called_once()


class TestPhaseTaxonomies:
    """Tests for phase_taxonomies function."""

    def test_full_build_collects_and_generates(self, tmp_path):
        """Full build calls collect_and_generate."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()

        phase_taxonomies(orchestrator, cache, incremental=False, parallel=True, pages_to_build=[])

        orchestrator.taxonomy.collect_and_generate.assert_called_once_with(parallel=True)

    def test_incremental_build_uses_incremental_method(self, tmp_path):
        """Incremental build uses collect_and_generate_incremental."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()
        mock_pages = [MagicMock()]
        orchestrator.taxonomy.collect_and_generate_incremental.return_value = {"python"}

        result = phase_taxonomies(
            orchestrator, cache, incremental=True, parallel=True, pages_to_build=mock_pages
        )

        orchestrator.taxonomy.collect_and_generate_incremental.assert_called_once_with(
            mock_pages, cache
        )
        assert result == {"python"}

    def test_returns_affected_tags(self, tmp_path):
        """Returns set of affected tag slugs."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {"tags": {"python": {}, "rust": {}}}
        cache = MagicMock()

        result = phase_taxonomies(
            orchestrator, cache, incremental=False, parallel=False, pages_to_build=[]
        )

        # Full build marks all tags as affected
        assert "python" in result
        assert "rust" in result

    def test_updates_taxonomy_time_stats(self, tmp_path):
        """Updates taxonomy time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()

        phase_taxonomies(orchestrator, cache, incremental=False, parallel=False, pages_to_build=[])

        assert orchestrator.stats.taxonomy_time_ms >= 0

    def test_invalidates_page_cache(self, tmp_path):
        """Invalidates regular_pages cache after taxonomy generation."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()

        phase_taxonomies(orchestrator, cache, incremental=False, parallel=False, pages_to_build=[])

        orchestrator.site.invalidate_regular_pages_cache.assert_called_once()

    def test_metadata_cascade_does_not_duplicate_already_generated_tags(self, tmp_path):
        """Metadata cascade only regenerates NEW tags, not ones already handled.

        Regression test for bug where tags from pages_to_build that were already
        returned by collect_and_generate_incremental were being regenerated twice,
        causing URL collisions.
        """
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()

        # Page with tags that overlap with already-generated tags
        mock_page = MagicMock()
        mock_page.metadata = {}  # Not generated
        mock_page.tags = ["python", "new-tag"]  # "python" will be already generated
        mock_page.source_path = MagicMock()
        mock_page.source_path.name = "test.md"

        # collect_and_generate_incremental already handled "python"
        orchestrator.taxonomy.collect_and_generate_incremental.return_value = {"python"}

        phase_taxonomies(
            orchestrator, cache, incremental=True, parallel=True, pages_to_build=[mock_page]
        )

        # Should only call generate_dynamic_pages_for_tags_with_cache with NEW tags
        # (not "python" which was already generated)
        calls = orchestrator.taxonomy.generate_dynamic_pages_for_tags_with_cache.call_args_list
        if calls:
            # If called, should only have the cascaded tag, not already-handled ones
            for call in calls:
                cascaded_tags = call[0][0]  # First positional arg
                assert "python" not in cascaded_tags, (
                    "Should not regenerate 'python' - already handled by collect_and_generate_incremental"
                )
                assert "new-tag" in cascaded_tags, "Should include new cascaded tag"

    def test_metadata_cascade_no_call_when_all_tags_already_generated(self, tmp_path):
        """No regeneration call when all page tags were already handled.

        If a page has tags that were ALL already returned by collect_and_generate_incremental,
        generate_dynamic_pages_for_tags_with_cache should not be called again.
        """
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()

        # Page with tags that are ALL already generated
        mock_page = MagicMock()
        mock_page.metadata = {}
        mock_page.tags = ["python", "rust"]  # Both already generated
        mock_page.source_path = MagicMock()
        mock_page.source_path.name = "test.md"

        # collect_and_generate_incremental already handled both tags
        orchestrator.taxonomy.collect_and_generate_incremental.return_value = {"python", "rust"}

        phase_taxonomies(
            orchestrator, cache, incremental=True, parallel=True, pages_to_build=[mock_page]
        )

        # Should NOT call generate_dynamic_pages_for_tags_with_cache
        # since there are no NEW cascaded tags
        orchestrator.taxonomy.generate_dynamic_pages_for_tags_with_cache.assert_not_called()


class TestPhaseTaxonomyIndex:
    """Tests for phase_taxonomy_index function."""

    def test_saves_taxonomy_index(self, tmp_path):
        """Saves taxonomy index to disk."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {
            "tags": {
                "python": {
                    "name": "Python",
                    "slug": "python",
                    "pages": [MagicMock(source_path=Path("test.md"))],
                }
            }
        }

        with patch("bengal.cache.taxonomy_index.TaxonomyIndex") as MockIndex:
            mock_index = MagicMock()
            MockIndex.return_value = mock_index

            phase_taxonomy_index(orchestrator)

        mock_index.update_tag.assert_called()
        mock_index.save_to_disk.assert_called_once()

    def test_handles_string_page_paths(self, tmp_path):
        """Handles string page paths in taxonomy data."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {
            "tags": {
                "python": {
                    "name": "Python",
                    "slug": "python",
                    "pages": ["path/to/page.md"],  # String paths
                }
            }
        }

        with patch("bengal.cache.taxonomy_index.TaxonomyIndex") as MockIndex:
            mock_index = MagicMock()
            MockIndex.return_value = mock_index

            phase_taxonomy_index(orchestrator)

        # Should handle string paths
        mock_index.update_tag.assert_called()

    def test_handles_save_errors(self, tmp_path):
        """Handles taxonomy index save errors gracefully."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {"tags": {}}

        with patch(
            "bengal.cache.taxonomy_index.TaxonomyIndex",
            side_effect=Exception("Save error"),
        ):
            # Should not raise
            phase_taxonomy_index(orchestrator)

        orchestrator.logger.warning.assert_called()


class TestPhaseMenus:
    """Tests for phase_menus function."""

    def test_builds_menus(self, tmp_path):
        """Calls menu orchestrator build."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.menu = []
        orchestrator.incremental.check_config_changed.return_value = False

        phase_menus(orchestrator, incremental=False, changed_page_paths=set())

        orchestrator.menu.build.assert_called_once()

    def test_incremental_passes_changed_pages(self, tmp_path):
        """Passes changed page paths for incremental builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.menu = []
        orchestrator.incremental.check_config_changed.return_value = False
        changed_paths = {Path("test.md")}

        phase_menus(orchestrator, incremental=True, changed_page_paths=changed_paths)

        orchestrator.menu.build.assert_called_once_with(
            changed_pages=changed_paths,
            config_changed=False,
        )

    def test_full_build_passes_none_for_changed_pages(self, tmp_path):
        """Passes None for changed_pages on full builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.menu = []
        orchestrator.incremental.check_config_changed.return_value = False

        phase_menus(orchestrator, incremental=False, changed_page_paths=set())

        orchestrator.menu.build.assert_called_once_with(
            changed_pages=None,
            config_changed=False,
        )

    def test_updates_menu_time_stats(self, tmp_path):
        """Updates menu time statistics."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.menu = []
        orchestrator.incremental.check_config_changed.return_value = False

        phase_menus(orchestrator, incremental=False, changed_page_paths=set())

        assert orchestrator.stats.menu_time_ms >= 0


class TestPhaseRelatedPosts:
    """Tests for phase_related_posts function."""

    def test_builds_related_posts_when_enabled(self, tmp_path):
        """Builds related posts index when tags exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {"tags": {"python": {}}}
        orchestrator.site.pages = [MagicMock() for _ in range(10)]

        with patch("bengal.orchestration.related_posts.RelatedPostsOrchestrator") as MockRelated:
            mock_related = MagicMock()
            MockRelated.return_value = mock_related

            phase_related_posts(orchestrator, incremental=False, parallel=True, pages_to_build=[])

        MockRelated.assert_called_once()
        mock_related.build_index.assert_called_once()

    def test_skips_for_large_sites(self, tmp_path):
        """Skips related posts for sites with >5000 pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {"tags": {"python": {}}}
        orchestrator.site.pages = [MagicMock() for _ in range(5001)]

        phase_related_posts(orchestrator, incremental=False, parallel=True, pages_to_build=[])

        # Should set empty related_posts, not build index
        for page in orchestrator.site.pages:
            assert page.related_posts == []

    def test_skips_when_no_tags(self, tmp_path):
        """Skips related posts when no tags exist."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {}  # No tags
        orchestrator.site.pages = [MagicMock() for _ in range(10)]

        phase_related_posts(orchestrator, incremental=False, parallel=True, pages_to_build=[])

        # Should set empty related_posts
        for page in orchestrator.site.pages:
            assert page.related_posts == []

    def test_incremental_passes_affected_pages(self, tmp_path):
        """Passes affected pages for incremental builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.taxonomies = {"tags": {"python": {}}}
        orchestrator.site.pages = [MagicMock() for _ in range(10)]
        orchestrator.site.regular_pages = orchestrator.site.pages
        affected_pages = [MagicMock()]

        with patch("bengal.orchestration.related_posts.RelatedPostsOrchestrator") as MockRelated:
            mock_related = MagicMock()
            MockRelated.return_value = mock_related

            phase_related_posts(
                orchestrator,
                incremental=True,
                parallel=True,
                pages_to_build=affected_pages,
            )

        mock_related.build_index.assert_called_once_with(
            limit=5,
            parallel=True,
            affected_pages=affected_pages,
        )


class TestPhaseQueryIndexes:
    """Tests for phase_query_indexes function."""

    def test_full_build_rebuilds_all(self, tmp_path):
        """Full build rebuilds all query indexes."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()

        phase_query_indexes(orchestrator, cache, incremental=False, pages_to_build=[])

        orchestrator.site.indexes.build_all.assert_called_once_with(orchestrator.site.pages, cache)

    def test_incremental_updates_affected(self, tmp_path):
        """Incremental build updates only affected indexes."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        cache = MagicMock()
        pages_to_build = [MagicMock()]

        orchestrator.site.indexes.update_incremental.return_value = {
            "by_date": {"2024-01"},
            "by_section": {"docs"},
        }

        phase_query_indexes(orchestrator, cache, incremental=True, pages_to_build=pages_to_build)

        orchestrator.site.indexes.update_incremental.assert_called_once_with(pages_to_build, cache)


class TestPhaseUpdatePagesList:
    """Tests for phase_update_pages_list function."""

    def test_adds_generated_tag_pages_full_build(self, tmp_path):
        """Adds generated tag pages on full builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        # Existing pages
        regular_page = MagicMock()
        pages_to_build = [regular_page]

        # Generated tag page
        tag_page = MagicMock()
        tag_page.metadata = {"type": "tag", "_tag_slug": "python"}
        orchestrator.site.generated_pages = [tag_page]

        result = phase_update_pages_list(
            orchestrator,
            incremental=False,
            pages_to_build=pages_to_build,
            affected_tags=set(),
        )

        # Should include both regular and tag pages
        assert regular_page in result
        assert tag_page in result

    def test_adds_only_affected_tag_pages_incremental(self, tmp_path):
        """Adds only affected tag pages on incremental builds."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        pages_to_build = []

        # Generated tag pages
        python_tag = MagicMock()
        python_tag.metadata = {"type": "tag", "_tag_slug": "python"}

        rust_tag = MagicMock()
        rust_tag.metadata = {"type": "tag", "_tag_slug": "rust"}

        tag_index = MagicMock()
        tag_index.metadata = {"type": "tag-index"}

        orchestrator.site.generated_pages = [python_tag, rust_tag, tag_index]

        result = phase_update_pages_list(
            orchestrator,
            incremental=True,
            pages_to_build=pages_to_build,
            affected_tags={"python"},  # Only python affected
        )

        # Should include python tag and tag-index, not rust
        assert python_tag in result
        assert tag_index in result
        assert rust_tag not in result

    def test_invalidates_page_caches(self, tmp_path):
        """Invalidates page caches before accessing generated_pages."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)
        orchestrator.site.generated_pages = []

        phase_update_pages_list(
            orchestrator,
            incremental=False,
            pages_to_build=[],
            affected_tags=set(),
        )

        orchestrator.site.invalidate_page_caches.assert_called_once()

    def test_deduplicates_pages(self, tmp_path):
        """Deduplicates pages in result."""
        orchestrator = MockPhaseContext.create_orchestrator(tmp_path)

        # Same page in both lists
        page = MagicMock()
        pages_to_build = [page, page]  # Duplicate

        orchestrator.site.generated_pages = []

        result = phase_update_pages_list(
            orchestrator,
            incremental=False,
            pages_to_build=pages_to_build,
            affected_tags=set(),
        )

        # Should be deduplicated
        assert len(result) == 1
