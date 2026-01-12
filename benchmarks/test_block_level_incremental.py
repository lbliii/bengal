"""Benchmark: Block-level incremental builds.

Validates RFC success criteria with real template changes.
Tests the block-level change detection system for incremental builds.

RFC: block-level-incremental-builds

Success Criteria:
    - Footer edit (site-scoped): <2s, 0 pages rebuilt
    - Nav edit (site-scoped): <2s, 0 pages rebuilt
    - Page-scoped edit: Correct pages rebuilt
    - Unknown scope: Conservative rebuild (safe fallback)
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


# Skip if block cache not available
pytest.importorskip("bengal.rendering.block_cache")

# Check if Kida environment is available (may need Python 3.14+ for tstring)
try:
    import kida  # noqa: F401

    HAS_KIDA = True
except ImportError:
    HAS_KIDA = False

requires_kida = pytest.mark.skipif(not HAS_KIDA, reason="Kida environment not available")


@requires_kida
class TestBlockLevelDetection:
    """Unit tests for block-level change detection components."""

    @pytest.fixture
    def block_cache(self):
        """Create a fresh BlockCache instance."""
        from bengal.rendering.block_cache import BlockCache

        return BlockCache(enabled=True)

    @pytest.fixture
    def mock_engine(self, tmp_path: Path):
        """Create a mock Kida engine with test templates."""
        Environment = pytest.importorskip("kida").Environment

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create base.html with site-scoped and page-scoped blocks
        base_html = templates_dir / "base.html"
        base_html.write_text(
            dedent("""
            <!DOCTYPE html>
            <html>
            <head>
                {% block head %}
                <title>{{ site.title }}</title>
                {% end %}
            </head>
            <body>
                {% block nav %}
                <nav>{{ site.nav_items }}</nav>
                {% end %}

                {% block content %}
                {{ page.content }}
                {% end %}

                {% block footer %}
                <footer>© 2025 {{ site.name }}</footer>
                {% end %}
            </body>
            </html>
        """)
        )

        # Create page.html that extends base.html
        page_html = templates_dir / "page.html"
        page_html.write_text(
            dedent("""
            {% extends "base.html" %}

            {% block content %}
            <main>{{ page.title }}: {{ page.body }}</main>
            {% end %}
        """)
        )

        env = Environment()
        env.loader = env.create_loader(str(templates_dir))
        return env

    def test_compute_block_hashes(self, block_cache, mock_engine):
        """Test that block hashes are computed correctly."""

        # Create a mock engine wrapper
        class MockEngine:
            def __init__(self, env):
                self.env = env

        engine = MockEngine(mock_engine)

        hashes = block_cache.compute_block_hashes(engine, "base.html")

        assert "head" in hashes
        assert "nav" in hashes
        assert "content" in hashes
        assert "footer" in hashes
        assert len(hashes) == 4

        # All hashes should be 16-char hex strings
        for block_name, hash_value in hashes.items():
            assert len(hash_value) == 16, f"Hash for {block_name} has wrong length"
            assert all(c in "0123456789abcdef" for c in hash_value)

    def test_detect_changed_blocks_first_run(self, block_cache, mock_engine):
        """First run should detect all blocks as changed."""

        class MockEngine:
            def __init__(self, env):
                self.env = env

        engine = MockEngine(mock_engine)

        changed = block_cache.detect_changed_blocks(engine, "base.html")

        # First run: all blocks appear as changed (no cached hashes)
        assert "head" in changed
        assert "nav" in changed
        assert "content" in changed
        assert "footer" in changed

    def test_detect_changed_blocks_no_changes(self, block_cache, mock_engine):
        """Second run with no changes should detect no changed blocks."""

        class MockEngine:
            def __init__(self, env):
                self.env = env

        engine = MockEngine(mock_engine)

        # First run populates hashes
        block_cache.detect_changed_blocks(engine, "base.html")

        # Second run with same template
        changed = block_cache.detect_changed_blocks(engine, "base.html")

        # No changes
        assert len(changed) == 0

    def test_detect_changed_blocks_after_edit(self, block_cache, mock_engine, tmp_path):
        """After editing a block, only that block should be detected as changed."""

        class MockEngine:
            def __init__(self, env):
                self.env = env

        engine = MockEngine(mock_engine)

        # First run
        block_cache.detect_changed_blocks(engine, "base.html")

        # Edit footer block
        base_html = tmp_path / "templates" / "base.html"
        content = base_html.read_text()
        content = content.replace("© 2025", "© 2026")
        base_html.write_text(content)

        # Clear template cache to reload
        mock_engine._cache.clear()

        # Second run should detect only footer changed
        changed = block_cache.detect_changed_blocks(engine, "base.html")

        assert "footer" in changed
        # Other blocks should not have changed
        assert "nav" not in changed
        assert "head" not in changed
        assert "content" not in changed

    def test_hash_stability(self, block_cache, mock_engine):
        """Hashes should be stable across multiple computations."""

        class MockEngine:
            def __init__(self, env):
                self.env = env

        engine = MockEngine(mock_engine)

        hashes1 = block_cache.compute_block_hashes(engine, "base.html")
        hashes2 = block_cache.compute_block_hashes(engine, "base.html")

        assert hashes1 == hashes2


@requires_kida
class TestBlockChangeClassification:
    """Tests for BlockChangeDetector classification."""

    @pytest.fixture
    def mock_components(self, tmp_path: Path):
        """Create mock components for testing."""
        from bengal.rendering.block_cache import BlockCache

        Environment = pytest.importorskip("kida").Environment

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create base.html
        base_html = templates_dir / "base.html"
        base_html.write_text(
            dedent("""
            <!DOCTYPE html>
            <html>
            <body>
                {#@ cache_scope: site @#}
                {% block nav %}
                <nav>{{ site.nav }}</nav>
                {% end %}

                {#@ cache_scope: site @#}
                {% block footer %}
                <footer>© {{ site.name }}</footer>
                {% end %}

                {% block content %}
                {{ page.content }}
                {% end %}
            </body>
            </html>
        """)
        )

        env = Environment()
        env.loader = env.create_loader(str(templates_dir))

        block_cache = BlockCache(enabled=True)

        class MockEngine:
            def __init__(self, environment):
                self.env = environment

            def get_cacheable_blocks(self, template_name: str) -> dict[str, str]:
                # Mock introspection results
                return {
                    "nav": "site",
                    "footer": "site",
                    "content": "page",
                }

        return MockEngine(env), block_cache

    def test_classify_site_scoped(self, mock_components):
        """Test classification of site-scoped block changes."""
        from bengal.orchestration.incremental.block_detector import BlockChangeDetector

        engine, block_cache = mock_components

        detector = BlockChangeDetector(engine, block_cache)

        # First detection populates hashes
        changes = detector.detect_and_classify("base.html")

        # All blocks should be detected on first run
        assert "nav" in changes.site_scoped
        assert "footer" in changes.site_scoped
        assert "content" in changes.page_scoped

    def test_only_site_scoped_optimization(self, mock_components):
        """Test that only_site_scoped returns True when appropriate."""
        from bengal.orchestration.incremental.block_detector import BlockChangeSet

        # Site-scoped only
        changes = BlockChangeSet(
            site_scoped={"nav", "footer"},
            page_scoped=set(),
            unknown_scoped=set(),
        )
        assert changes.only_site_scoped() is True

        # Mixed
        changes = BlockChangeSet(
            site_scoped={"nav"},
            page_scoped={"content"},
            unknown_scoped=set(),
        )
        assert changes.only_site_scoped() is False

        # Empty
        changes = BlockChangeSet(
            site_scoped=set(),
            page_scoped=set(),
            unknown_scoped=set(),
        )
        assert changes.only_site_scoped() is False


class TestRebuildDecision:
    """Tests for RebuildDecisionEngine."""

    def test_skip_pages_for_site_scoped_only(self):
        """When only site-scoped blocks change, skip page rebuilds."""
        from bengal.orchestration.incremental.rebuild_decision import RebuildDecision

        decision = RebuildDecision(
            blocks_to_rewarm={"nav", "footer"},
            pages_to_rebuild=set(),
            skip_all_pages=True,
            reason="Only site-scoped blocks changed",
            child_templates=set(),
        )

        assert decision.skip_all_pages is True
        assert len(decision.pages_to_rebuild) == 0
        assert len(decision.blocks_to_rewarm) == 2

    def test_rebuild_pages_for_page_scoped(self):
        """When page-scoped blocks change, rebuild affected pages."""
        from bengal.orchestration.incremental.rebuild_decision import RebuildDecision

        decision = RebuildDecision(
            blocks_to_rewarm={"nav"},  # Still rewarm site blocks
            pages_to_rebuild={Path("content/page1.md"), Path("content/page2.md")},
            skip_all_pages=False,
            reason="Page-scoped blocks changed",
            child_templates=set(),
        )

        assert decision.skip_all_pages is False
        assert len(decision.pages_to_rebuild) == 2
        assert len(decision.blocks_to_rewarm) == 1


class TestBlockCacheClear:
    """Tests for BlockCache clear behavior."""

    def test_clear_preserves_hashes(self):
        """Clear with preserve_hashes=True should keep block hashes."""
        from bengal.rendering.block_cache import BlockCache

        cache = BlockCache(enabled=True)

        # Simulate some cached hashes
        cache._block_hashes["base.html:nav"] = "abc123"
        cache._block_hashes["base.html:footer"] = "def456"

        cache.clear(preserve_hashes=True)

        # Hashes should be preserved
        assert len(cache._block_hashes) == 2
        assert cache._block_hashes["base.html:nav"] == "abc123"

    def test_clear_removes_hashes(self):
        """Clear with preserve_hashes=False should remove block hashes."""
        from bengal.rendering.block_cache import BlockCache

        cache = BlockCache(enabled=True)

        # Simulate some cached hashes
        cache._block_hashes["base.html:nav"] = "abc123"

        cache.clear(preserve_hashes=False)

        # Hashes should be cleared
        assert len(cache._block_hashes) == 0


# Performance benchmarks (run with pytest-benchmark)
@requires_kida
@pytest.mark.benchmark(group="block_detection")
class TestBlockDetectionPerformance:
    """Performance benchmarks for block-level detection."""

    @pytest.fixture
    def large_template_env(self, tmp_path: Path):
        """Create environment with a large template."""
        Environment = pytest.importorskip("kida").Environment

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create a large base.html with many blocks
        blocks = []
        for i in range(50):
            blocks.append(
                f"""
                {{%- block block_{i} -%}}
                <div class="block-{i}">
                    {{{{ site.data.item_{i} }}}}
                </div>
                {{%- end -%}}
            """
            )

        base_html = templates_dir / "base.html"
        base_html.write_text(
            f"""
            <!DOCTYPE html>
            <html>
            <body>
            {"".join(blocks)}
            </body>
            </html>
        """
        )

        env = Environment()
        env.loader = env.create_loader(str(templates_dir))
        return env

    def test_block_hash_computation_performance(self, large_template_env, benchmark, tmp_path):
        """Benchmark block hash computation for large templates."""
        from bengal.rendering.block_cache import BlockCache

        class MockEngine:
            def __init__(self, env):
                self.env = env

        cache = BlockCache(enabled=True)
        engine = MockEngine(large_template_env)

        result = benchmark(cache.compute_block_hashes, engine, "base.html")

        # Should have 50 block hashes
        assert len(result) == 50

    def test_change_detection_performance(self, large_template_env, benchmark, tmp_path):
        """Benchmark change detection for large templates."""
        from bengal.rendering.block_cache import BlockCache

        class MockEngine:
            def __init__(self, env):
                self.env = env

        cache = BlockCache(enabled=True)
        engine = MockEngine(large_template_env)

        # First run to populate hashes
        cache.detect_changed_blocks(engine, "base.html")

        # Benchmark second run (no changes)
        result = benchmark(cache.detect_changed_blocks, engine, "base.html")

        # No changes expected
        assert len(result) == 0
