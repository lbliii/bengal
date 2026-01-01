"""
Tests for memory release behavior in StreamingRenderOrchestrator.

Verifies that:
1. Page cache attributes are correctly cleared after batch processing
2. Batching divides pages into expected batch sizes
3. gc.collect() is called after leaf batches
4. Hub/mid-tier batches preserve cache attributes

These tests ensure the memory-optimized build mode actually releases memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@dataclass
class MockPage:
    """
    Mock page with cache attributes matching bengal.core.page.Page.

    Includes all cache attributes that should be cleared for memory optimization.
    """

    path: Path
    # Cache attributes from Page dataclass (core/page/__init__.py)
    _ast_cache: list[dict[str, Any]] | None = field(default=None)
    _html_cache: str | None = field(default=None)
    _plain_text_cache: str | None = field(default=None)
    _toc_items_cache: list[dict[str, Any]] | None = field(default=None)

    def __hash__(self) -> int:
        """Make MockPage hashable for set operations in streaming.py."""
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        """Compare MockPages by path."""
        if not isinstance(other, MockPage):
            return NotImplemented
        return self.path == other.path


class TestMemoryReleaseCleanup:
    """Test that streaming render correctly clears page cache attributes."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for StreamingRenderOrchestrator."""
        return SimpleNamespace(
            root_path=tmp_path,
            output_dir=tmp_path / "public",
            config={},
            pages=[],
            theme=None,
        )

    @pytest.fixture
    def pages_with_caches(self, tmp_path) -> list[MockPage]:
        """Create pages with populated cache attributes."""
        pages = []
        for i in range(5):
            page = MockPage(
                path=tmp_path / f"page{i}.md",
                _ast_cache=[{"type": "paragraph", "content": f"Content {i}"}],
                _html_cache=f"<p>Content {i}</p>",
                _plain_text_cache=f"Content {i}",
                _toc_items_cache=[{"id": f"heading-{i}", "text": f"Heading {i}"}],
            )
            pages.append(page)
        return pages

    def test_release_memory_clears_ast_cache(self, mock_site, pages_with_caches):
        """Verify _ast_cache is cleared after memory release."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Confirm caches are populated
        for page in pages_with_caches:
            assert page._ast_cache is not None

        orch = StreamingRenderOrchestrator(mock_site)

        # Call _render_batches with release_memory=True
        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            orch._render_batches(
                renderer=mock_renderer,
                pages=pages_with_caches,
                batch_size=10,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="leaves",
                release_memory=True,
            )

        # All _ast_cache should be cleared
        for page in pages_with_caches:
            assert page._ast_cache is None, "_ast_cache should be cleared"

    def test_release_memory_clears_html_cache(self, mock_site, pages_with_caches):
        """Verify _html_cache is cleared after memory release."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Confirm caches are populated
        for page in pages_with_caches:
            assert page._html_cache is not None

        orch = StreamingRenderOrchestrator(mock_site)

        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            orch._render_batches(
                renderer=mock_renderer,
                pages=pages_with_caches,
                batch_size=10,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="leaves",
                release_memory=True,
            )

        # All _html_cache should be cleared
        for page in pages_with_caches:
            assert page._html_cache is None, "_html_cache should be cleared"

    def test_release_memory_clears_plain_text_cache(self, mock_site, pages_with_caches):
        """Verify _plain_text_cache is cleared after memory release."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        for page in pages_with_caches:
            assert page._plain_text_cache is not None

        orch = StreamingRenderOrchestrator(mock_site)

        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            orch._render_batches(
                renderer=mock_renderer,
                pages=pages_with_caches,
                batch_size=10,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="leaves",
                release_memory=True,
            )

        for page in pages_with_caches:
            assert page._plain_text_cache is None, "_plain_text_cache should be cleared"

    def test_release_memory_clears_toc_items_cache(self, mock_site, pages_with_caches):
        """Verify _toc_items_cache is cleared after memory release."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        for page in pages_with_caches:
            assert page._toc_items_cache is not None

        orch = StreamingRenderOrchestrator(mock_site)

        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            orch._render_batches(
                renderer=mock_renderer,
                pages=pages_with_caches,
                batch_size=10,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="leaves",
                release_memory=True,
            )

        for page in pages_with_caches:
            assert page._toc_items_cache is None, "_toc_items_cache should be cleared"

    def test_release_memory_false_preserves_caches(self, mock_site, pages_with_caches):
        """Verify caches are preserved when release_memory=False."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Store original values
        original_caches = [
            (p._ast_cache, p._html_cache, p._plain_text_cache, p._toc_items_cache)
            for p in pages_with_caches
        ]

        orch = StreamingRenderOrchestrator(mock_site)

        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            orch._render_batches(
                renderer=mock_renderer,
                pages=pages_with_caches,
                batch_size=10,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="mid-tier",
                release_memory=False,  # Should NOT clear
            )

        # All caches should be preserved
        for i, page in enumerate(pages_with_caches):
            assert page._ast_cache == original_caches[i][0]
            assert page._html_cache == original_caches[i][1]
            assert page._plain_text_cache == original_caches[i][2]
            assert page._toc_items_cache == original_caches[i][3]


class TestBatchProcessing:
    """Test batch division and processing behavior."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site."""
        return SimpleNamespace(
            root_path=tmp_path,
            output_dir=tmp_path / "public",
            config={},
            pages=[],
            theme=None,
        )

    def test_batches_divided_correctly(self, mock_site, tmp_path):
        """Verify pages are divided into correct batch sizes."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create 25 pages
        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(25)]

        orch = StreamingRenderOrchestrator(mock_site)

        # Track process calls
        process_calls = []

        def track_process(batch, *args, **kwargs):
            process_calls.append(len(batch))

        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            mock_renderer.process = track_process

            orch._render_batches(
                renderer=mock_renderer,
                pages=pages,
                batch_size=10,  # Should create 3 batches: 10, 10, 5
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="test",
                release_memory=False,
            )

        assert process_calls == [10, 10, 5], f"Expected [10, 10, 5], got {process_calls}"

    def test_single_batch_when_pages_less_than_batch_size(self, mock_site, tmp_path):
        """Verify single batch when page count < batch_size."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(5)]

        orch = StreamingRenderOrchestrator(mock_site)

        process_calls = []

        def track_process(batch, *args, **kwargs):
            process_calls.append(len(batch))

        with patch.object(orch, "site"):
            mock_renderer = MagicMock()
            mock_renderer.process = track_process

            orch._render_batches(
                renderer=mock_renderer,
                pages=pages,
                batch_size=100,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="test",
                release_memory=False,
            )

        assert process_calls == [5]

    def test_gc_collect_called_per_batch_when_release_memory(self, mock_site, tmp_path):
        """Verify gc.collect() is called after each batch when release_memory=True."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(25)]

        orch = StreamingRenderOrchestrator(mock_site)

        with (
            patch.object(orch, "site"),
            patch("bengal.orchestration.streaming.gc.collect") as mock_gc,
        ):
            mock_renderer = MagicMock()

            orch._render_batches(
                renderer=mock_renderer,
                pages=pages,
                batch_size=10,  # 3 batches
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="leaves",
                release_memory=True,
            )

            # gc.collect should be called once per batch
            assert mock_gc.call_count == 3

    def test_gc_not_called_when_release_memory_false(self, mock_site, tmp_path):
        """Verify gc.collect() is NOT called when release_memory=False."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(10)]

        orch = StreamingRenderOrchestrator(mock_site)

        with (
            patch.object(orch, "site"),
            patch("bengal.orchestration.streaming.gc.collect") as mock_gc,
        ):
            mock_renderer = MagicMock()

            orch._render_batches(
                renderer=mock_renderer,
                pages=pages,
                batch_size=5,
                parallel=False,
                quiet=True,
                tracker=None,
                stats=None,
                batch_label="mid-tier",
                release_memory=False,
            )

            # gc.collect should NOT be called
            assert mock_gc.call_count == 0


class TestLayerProcessing:
    """Test hub/mid-tier/leaf processing integration."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site."""
        return SimpleNamespace(
            root_path=tmp_path,
            output_dir=tmp_path / "public",
            config={},
            pages=[],
            theme=None,
        )

    @pytest.fixture
    def mock_knowledge_graph(self):
        """Create a mock knowledge graph with layers."""

        class MockLayers:
            def __init__(self, hubs, mid_tier, leaves):
                self.hubs = hubs
                self.mid_tier = mid_tier
                self.leaves = leaves

        class MockGraph:
            def __init__(self, hubs, mid_tier, leaves):
                self._layers = MockLayers(hubs, mid_tier, leaves)

            def build(self):
                pass

            def get_layers(self):
                return self._layers

        return MockGraph

    def test_only_leaves_get_memory_released(self, mock_site, mock_knowledge_graph, tmp_path):
        """Verify only leaf pages have caches cleared, not hubs/mid-tier."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create pages with caches
        hub_page = MockPage(
            path=tmp_path / "hub.md",
            _html_cache="<p>Hub</p>",
            _ast_cache=[{"type": "p"}],
        )
        mid_page = MockPage(
            path=tmp_path / "mid.md",
            _html_cache="<p>Mid</p>",
            _ast_cache=[{"type": "p"}],
        )
        leaf_page = MockPage(
            path=tmp_path / "leaf.md",
            _html_cache="<p>Leaf</p>",
            _ast_cache=[{"type": "p"}],
        )

        all_pages = [hub_page, mid_page, leaf_page]

        # Create graph that classifies pages
        graph = mock_knowledge_graph(
            hubs=[hub_page],
            mid_tier=[mid_page],
            leaves=[leaf_page],
        )

        orch = StreamingRenderOrchestrator(mock_site)

        # RenderOrchestrator is imported inside process(), so patch at render module level
        with (
            patch("bengal.orchestration.render.RenderOrchestrator") as MockRenderOrch,
            patch.object(orch, "site"),
        ):
            # Configure mock to track calls but not fail
            mock_render_instance = MagicMock()
            MockRenderOrch.return_value = mock_render_instance

            # Inject our mock graph via build_context
            mock_context = MagicMock()
            mock_context.knowledge_graph = graph
            mock_context.reporter = None
            mock_context.progress_manager = None

            orch.process(
                pages=all_pages,
                parallel=False,
                quiet=True,
                build_context=mock_context,
            )

        # Hub should preserve caches (rendered first, not in leaf batch)
        assert hub_page._html_cache == "<p>Hub</p>", "Hub cache should be preserved"
        assert hub_page._ast_cache == [{"type": "p"}], "Hub AST should be preserved"

        # Mid-tier should preserve caches (release_memory=False for mid-tier)
        assert mid_page._html_cache == "<p>Mid</p>", "Mid-tier cache should be preserved"
        assert mid_page._ast_cache == [{"type": "p"}], "Mid-tier AST should be preserved"

        # Leaf should have caches cleared (release_memory=True for leaves)
        assert leaf_page._html_cache is None, "Leaf cache should be cleared"
        assert leaf_page._ast_cache is None, "Leaf AST should be cleared"


class TestSmallSiteWarnings:
    """Test warnings for small sites using memory optimization."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site."""
        return SimpleNamespace(
            root_path=tmp_path,
            output_dir=tmp_path / "public",
            config={},
            pages=[],
            theme=None,
        )

    def test_warns_for_small_sites_via_reporter(self, mock_site, tmp_path):
        """Verify warning is logged via reporter for sites under 1000 pages."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create 100 pages (under warning threshold of 1000)
        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(100)]

        orch = StreamingRenderOrchestrator(mock_site)

        # Create a mock reporter to capture log messages
        mock_reporter = MagicMock()
        logged_messages = []
        mock_reporter.log = lambda msg: logged_messages.append(msg)

        with patch("bengal.orchestration.render.RenderOrchestrator"):
            orch.process(
                pages=pages,
                parallel=False,
                quiet=False,
                reporter=mock_reporter,
            )

        # Check that warning was logged
        warning_logged = any(
            "Memory optimization is designed for large sites" in msg for msg in logged_messages
        )
        assert warning_logged, f"Expected warning in messages: {logged_messages}"

    def test_no_warning_for_large_sites(self, mock_site, tmp_path):
        """Verify no warning for sites at or above recommended threshold."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create 5000 pages (at recommended threshold)
        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(5000)]

        orch = StreamingRenderOrchestrator(mock_site)

        mock_reporter = MagicMock()
        logged_messages = []
        mock_reporter.log = lambda msg: logged_messages.append(msg)

        with patch("bengal.orchestration.render.RenderOrchestrator"):
            orch.process(
                pages=pages,
                parallel=False,
                quiet=False,
                reporter=mock_reporter,
            )

        # Should NOT have warning about small sites
        warning_logged = any(
            "Memory optimization is designed for large sites" in msg for msg in logged_messages
        )
        assert not warning_logged, f"Should not warn for large sites: {logged_messages}"

    def test_marginal_benefit_warning_for_medium_sites(self, mock_site, tmp_path):
        """Verify marginal benefit warning for sites between 1000-5000 pages."""
        from bengal.orchestration.streaming import StreamingRenderOrchestrator

        # Create 2000 pages (above warning threshold, below recommended)
        pages = [MockPage(path=tmp_path / f"page{i}.md") for i in range(2000)]

        orch = StreamingRenderOrchestrator(mock_site)

        mock_reporter = MagicMock()
        logged_messages = []
        mock_reporter.log = lambda msg: logged_messages.append(msg)

        with patch("bengal.orchestration.render.RenderOrchestrator"):
            orch.process(
                pages=pages,
                parallel=False,
                quiet=False,
                reporter=mock_reporter,
            )

        # Should have marginal benefit info message
        info_logged = any("marginal benefit" in msg for msg in logged_messages)
        assert info_logged, f"Expected marginal benefit info in messages: {logged_messages}"
