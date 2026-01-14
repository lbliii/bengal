"""Unit tests for BuildContext asset accumulation methods."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bengal.orchestration.build_context import BuildContext


class TestBuildContextAssetAccumulation:
    """Tests for asset accumulation in BuildContext."""

    def test_accumulate_page_assets_basic(self):
        """Basic accumulation stores path and assets."""
        ctx = BuildContext()
        path = Path("test.md")
        assets = {"/img/logo.png", "/js/app.js"}

        ctx.accumulate_page_assets(path, assets)

        assert ctx.accumulated_asset_count == 1
        accumulated = ctx.get_accumulated_assets()
        assert len(accumulated) == 1
        assert accumulated[0] == (path, assets)

    def test_accumulate_page_assets_thread_safe(self):
        """Concurrent accumulation doesn't lose data."""
        ctx = BuildContext()

        def accumulate(i: int):
            ctx.accumulate_page_assets(Path(f"page_{i}.md"), {f"/asset_{i}.png"})

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(accumulate, range(100)))

        assert ctx.accumulated_asset_count == 100

    def test_get_accumulated_assets_returns_copy(self):
        """Returns copy, not reference to internal list."""
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("test.md"), {"/img.png"})

        result1 = ctx.get_accumulated_assets()
        result2 = ctx.get_accumulated_assets()

        assert result1 is not result2
        assert result1 == result2

    def test_has_accumulated_assets_false_initially(self):
        """Property returns False before any accumulation."""
        ctx = BuildContext()
        assert not ctx.has_accumulated_assets
        assert ctx.accumulated_asset_count == 0

    def test_has_accumulated_assets_true_after_accumulation(self):
        """Property returns True after accumulation."""
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("test.md"), {"/img.png"})
        assert ctx.has_accumulated_assets

    def test_clear_accumulated_assets(self):
        """Clear releases accumulated data."""
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("test.md"), {"/img.png"})
        assert ctx.accumulated_asset_count == 1

        ctx.clear_accumulated_assets()

        assert ctx.accumulated_asset_count == 0
        assert not ctx.has_accumulated_assets

    def test_clear_lazy_artifacts_clears_assets(self):
        """clear_lazy_artifacts also clears accumulated assets."""
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("test.md"), {"/img.png"})

        ctx.clear_lazy_artifacts()

        assert not ctx.has_accumulated_assets

    def test_multiple_accumulations(self):
        """Multiple pages can be accumulated."""
        ctx = BuildContext()

        ctx.accumulate_page_assets(Path("a.md"), {"/a.png"})
        ctx.accumulate_page_assets(Path("b.md"), {"/b.png", "/b.js"})
        ctx.accumulate_page_assets(Path("c.md"), {"/c.css"})

        assert ctx.accumulated_asset_count == 3
        accumulated = ctx.get_accumulated_assets()
        paths = [p for p, _ in accumulated]
        assert Path("a.md") in paths
        assert Path("b.md") in paths
        assert Path("c.md") in paths

    def test_empty_assets_set(self):
        """Accumulating empty set is allowed."""
        ctx = BuildContext()
        ctx.accumulate_page_assets(Path("test.md"), set())

        assert ctx.accumulated_asset_count == 1
        accumulated = ctx.get_accumulated_assets()
        assert accumulated[0] == (Path("test.md"), set())

    def test_large_asset_sets(self):
        """Handles pages with many assets."""
        ctx = BuildContext()
        large_assets = {f"/asset_{i}.png" for i in range(1000)}

        ctx.accumulate_page_assets(Path("test.md"), large_assets)

        assert ctx.accumulated_asset_count == 1
        accumulated = ctx.get_accumulated_assets()
        assert len(accumulated[0][1]) == 1000
