"""
Tests for BuildContext state management.

Covers:
- BuildContext initialization and defaults
- Lazy artifact caching (knowledge_graph)
- Thread-safe content caching
- State lifecycle management
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

from bengal.utils.build_context import BuildContext


class TestBuildContextInitialization:
    """Tests for BuildContext initialization and defaults."""

    def test_default_values(self):
        """BuildContext has sensible defaults."""
        ctx = BuildContext()

        # Core attributes default to None
        assert ctx.site is None
        assert ctx.stats is None
        assert ctx.profile is None

        # Cache/tracking default to None
        assert ctx.cache is None
        assert ctx.tracker is None

        # Build mode flags have defaults
        assert ctx.incremental is False
        assert ctx.verbose is False
        assert ctx.quiet is False
        assert ctx.strict is False
        assert ctx.parallel is True  # Default to parallel
        assert ctx.memory_optimized is False
        assert ctx.full_output is False
        assert ctx.profile_templates is False

        # Work items default to None
        assert ctx.pages is None
        assert ctx.pages_to_build is None
        assert ctx.assets is None
        assert ctx.assets_to_process is None

        # Incremental state
        assert ctx.affected_tags == set()
        assert ctx.affected_sections is None
        assert ctx.changed_page_paths == set()
        assert ctx.config_changed is False

        # Output/progress default to None
        assert ctx.cli is None
        assert ctx.progress_manager is None
        assert ctx.reporter is None

        # Timing
        assert ctx.build_start == 0.0

    def test_custom_initialization(self):
        """BuildContext can be initialized with custom values."""
        mock_site = MagicMock()
        mock_stats = MagicMock()

        ctx = BuildContext(
            site=mock_site,
            stats=mock_stats,
            incremental=True,
            verbose=True,
            parallel=False,
        )

        assert ctx.site is mock_site
        assert ctx.stats is mock_stats
        assert ctx.incremental is True
        assert ctx.verbose is True
        assert ctx.parallel is False

    def test_affected_tags_is_new_set_per_instance(self):
        """Each BuildContext gets its own affected_tags set."""
        ctx1 = BuildContext()
        ctx2 = BuildContext()

        ctx1.affected_tags.add("python")

        assert "python" in ctx1.affected_tags
        assert "python" not in ctx2.affected_tags

    def test_changed_page_paths_is_new_set_per_instance(self):
        """Each BuildContext gets its own changed_page_paths set."""
        ctx1 = BuildContext()
        ctx2 = BuildContext()

        ctx1.changed_page_paths.add(Path("test.md"))

        assert Path("test.md") in ctx1.changed_page_paths
        assert Path("test.md") not in ctx2.changed_page_paths


class TestKnowledgeGraphLazyLoading:
    """Tests for knowledge graph lazy loading."""

    def test_knowledge_graph_initially_none(self):
        """Knowledge graph is None before first access."""
        ctx = BuildContext()
        # Access internal field directly to check without triggering build
        assert ctx._knowledge_graph is None

    def test_knowledge_graph_returns_none_when_disabled(self):
        """Knowledge graph returns None when disabled."""
        ctx = BuildContext()
        ctx._knowledge_graph_enabled = False

        assert ctx.knowledge_graph is None

    def test_knowledge_graph_returns_none_without_site(self):
        """Knowledge graph returns None when site is not set."""
        ctx = BuildContext()
        ctx._knowledge_graph_enabled = True

        assert ctx.knowledge_graph is None

    def test_knowledge_graph_caches_result(self):
        """Knowledge graph is cached after first build."""
        ctx = BuildContext()
        mock_site = MagicMock()
        mock_site.config = {"features": {"graph": True}}
        ctx.site = mock_site

        mock_graph = MagicMock()

        with (
            patch("bengal.analysis.knowledge_graph.KnowledgeGraph") as MockKnowledgeGraph,
            patch("bengal.config.defaults.is_feature_enabled", return_value=True),
        ):
            MockKnowledgeGraph.return_value = mock_graph

            # First access builds the graph
            result1 = ctx.knowledge_graph
            # Second access returns cached
            result2 = ctx.knowledge_graph

            # Should only build once
            MockKnowledgeGraph.assert_called_once()
            assert result1 is mock_graph
            assert result2 is mock_graph

    def test_knowledge_graph_disabled_when_feature_off(self):
        """Knowledge graph is disabled when feature is not enabled."""
        ctx = BuildContext()
        mock_site = MagicMock()
        mock_site.config = {"features": {"graph": False}}
        ctx.site = mock_site

        with patch("bengal.config.defaults.is_feature_enabled", return_value=False):
            result = ctx.knowledge_graph

        assert result is None
        assert ctx._knowledge_graph_enabled is False

    def test_clear_lazy_artifacts(self):
        """clear_lazy_artifacts clears cached graph and content."""
        ctx = BuildContext()
        ctx._knowledge_graph = MagicMock()
        ctx._page_contents = {"test.md": "content"}

        ctx.clear_lazy_artifacts()

        assert ctx._knowledge_graph is None
        assert len(ctx._page_contents) == 0


class TestContentCaching:
    """Tests for thread-safe content caching."""

    def test_cache_content(self):
        """cache_content stores content by path."""
        ctx = BuildContext()
        path = Path("/test/page.md")
        content = "# Test Content"

        ctx.cache_content(path, content)

        assert ctx.get_content(path) == content

    def test_get_content_returns_none_for_uncached(self):
        """get_content returns None for paths not in cache."""
        ctx = BuildContext()

        result = ctx.get_content(Path("/nonexistent.md"))

        assert result is None

    def test_content_cache_size(self):
        """content_cache_size returns correct count."""
        ctx = BuildContext()

        assert ctx.content_cache_size == 0

        ctx.cache_content(Path("a.md"), "a")
        ctx.cache_content(Path("b.md"), "b")

        assert ctx.content_cache_size == 2

    def test_has_cached_content(self):
        """has_cached_content reflects cache state."""
        ctx = BuildContext()

        assert ctx.has_cached_content is False

        ctx.cache_content(Path("test.md"), "content")

        assert ctx.has_cached_content is True

    def test_clear_content_cache(self):
        """clear_content_cache empties the cache."""
        ctx = BuildContext()
        ctx.cache_content(Path("a.md"), "a")
        ctx.cache_content(Path("b.md"), "b")

        ctx.clear_content_cache()

        assert ctx.content_cache_size == 0
        assert ctx.has_cached_content is False

    def test_get_all_cached_contents(self):
        """get_all_cached_contents returns copy of cache."""
        ctx = BuildContext()
        ctx.cache_content(Path("a.md"), "content a")
        ctx.cache_content(Path("b.md"), "content b")

        contents = ctx.get_all_cached_contents()

        assert len(contents) == 2
        # Keys are string paths
        assert "a.md" in contents
        assert "b.md" in contents
        assert contents["a.md"] == "content a"
        assert contents["b.md"] == "content b"

    def test_get_all_cached_contents_returns_copy(self):
        """get_all_cached_contents returns a copy, not the original."""
        ctx = BuildContext()
        ctx.cache_content(Path("test.md"), "original")

        contents = ctx.get_all_cached_contents()
        contents["test.md"] = "modified"

        # Original should be unchanged
        assert ctx.get_content(Path("test.md")) == "original"


class TestContentCacheThreadSafety:
    """Tests for thread-safe content caching."""

    def test_concurrent_cache_writes(self):
        """Multiple threads can write to cache safely."""
        ctx = BuildContext()
        num_threads = 10
        items_per_thread = 100

        def cache_items(thread_id: int):
            for i in range(items_per_thread):
                path = Path(f"thread_{thread_id}_item_{i}.md")
                ctx.cache_content(path, f"content_{thread_id}_{i}")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(cache_items, i) for i in range(num_threads)]
            for f in futures:
                f.result()

        # All items should be in cache
        assert ctx.content_cache_size == num_threads * items_per_thread

    def test_concurrent_cache_reads_and_writes(self):
        """Concurrent reads and writes don't cause race conditions."""
        ctx = BuildContext()
        errors = []

        def writer():
            for i in range(100):
                ctx.cache_content(Path(f"item_{i}.md"), f"content_{i}")

        def reader():
            for i in range(100):
                try:
                    # Read may or may not find the item depending on timing
                    ctx.get_content(Path(f"item_{i}.md"))
                    ctx.get_all_cached_contents()
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur from race conditions
        assert len(errors) == 0

    def test_concurrent_clear_and_write(self):
        """Clearing cache while writing doesn't cause errors."""
        ctx = BuildContext()
        errors = []

        def writer():
            for i in range(100):
                try:
                    ctx.cache_content(Path(f"item_{i}.md"), f"content_{i}")
                except Exception as e:
                    errors.append(e)

        def clearer():
            for _ in range(10):
                try:
                    ctx.clear_content_cache()
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=clearer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0


class TestBuildContextLifecycle:
    """Tests for BuildContext lifecycle management."""

    def test_typical_lifecycle(self):
        """Test typical BuildContext usage through build phases."""
        # Phase 1: Create context at build start
        ctx = BuildContext(incremental=False, parallel=True)
        ctx.build_start = 1000.0

        # Phase 2: Set site after discovery
        mock_site = MagicMock()
        ctx.site = mock_site

        # Phase 3: Cache content during discovery
        ctx.cache_content(Path("page1.md"), "# Page 1")
        ctx.cache_content(Path("page2.md"), "# Page 2")

        # Phase 4: Set work items
        mock_pages = [MagicMock(), MagicMock()]
        ctx.pages = mock_pages
        ctx.pages_to_build = mock_pages

        # Phase 5: Track changes during build
        ctx.affected_tags.add("python")
        ctx.changed_page_paths.add(Path("page1.md"))

        # Phase 6: Cleanup at end
        ctx.clear_lazy_artifacts()

        # Verify state after cleanup
        assert ctx.site is mock_site  # Site not cleared
        assert ctx.content_cache_size == 0  # Content cache cleared

    def test_incremental_build_lifecycle(self):
        """Test BuildContext for incremental builds."""
        ctx = BuildContext(incremental=True)

        # Incremental builds track affected items
        ctx.affected_sections = {"docs", "tutorials"}
        ctx.affected_tags = {"python", "rust"}
        ctx.changed_page_paths = {Path("docs/intro.md"), Path("tutorials/start.md")}

        # Verify tracking
        assert "docs" in ctx.affected_sections
        assert "python" in ctx.affected_tags
        assert Path("docs/intro.md") in ctx.changed_page_paths

    def test_memory_optimized_mode(self):
        """Test BuildContext in memory-optimized mode."""
        ctx = BuildContext(memory_optimized=True)

        assert ctx.memory_optimized is True

        # Memory-optimized builds still use content cache
        ctx.cache_content(Path("test.md"), "content")
        assert ctx.has_cached_content is True

        # But should clear aggressively
        ctx.clear_lazy_artifacts()
        assert ctx.has_cached_content is False
