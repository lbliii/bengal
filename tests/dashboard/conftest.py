"""
Pytest fixtures for Textual dashboard testing.

Provides async fixtures for testing Textual apps in headless mode,
snapshot testing helpers, and mock data generators.

Usage:
    @pytest.mark.asyncio
    async def test_navigation(pilot):
        await pilot.press("1")
        assert pilot.app.screen.name == "build"

    def test_build_screen_snapshot(snap_compare):
        assert snap_compare(APP_PATH, press=["1"])
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from textual.pilot import Pilot

    from bengal.cli.dashboard.app import BengalApp


# Path to the main dashboard app module (for snapshot tests)
APP_PATH = str(Path(__file__).parent.parent.parent / "bengal" / "cli" / "dashboard" / "app.py")


@pytest.fixture
def snapshot_path() -> Path:
    """Path to store dashboard snapshots for visual regression testing."""
    return Path(__file__).parent / "snapshots"


def _create_mock_asset(index: int, category: str = "styles") -> MagicMock:
    """Create a properly configured mock asset."""
    asset = MagicMock()
    asset.path = f"assets/{category}/file-{index}.css"

    # Configure source_path to avoid TypeError in _format_size
    source_path_mock = MagicMock()
    source_path_mock.name = f"file-{index}.css"
    source_path_mock.parent = Path(f"assets/{category}")
    source_path_mock.exists.return_value = True
    source_path_mock.stat.return_value.st_size = 1024 * (index + 1)  # Return an int
    source_path_mock.__str__ = lambda self: f"assets/{category}/file-{index}.css"

    asset.source_path = source_path_mock
    asset.category = category

    return asset


@pytest.fixture
def mock_site() -> MagicMock:
    """
    Create a mock Site object for dashboard testing.
    
    Provides realistic data for rendering dashboards without
    requiring actual site files.
        
    """
    site = MagicMock()
    site.title = "Test Site"
    site.baseurl = "/"
    site.output_dir = Path("/tmp/test-output")
    site.content_dir = Path("/tmp/test-content")

    # Mock pages
    site.pages = [
        MagicMock(
            title=f"Page {i}",
            url=f"/page-{i}/",
            source_path=Path(f"content/page-{i}.md"),
        )
        for i in range(5)
    ]

    # Mock assets with proper source_path configuration
    site.assets = [_create_mock_asset(i) for i in range(10)]

    # Mock sections
    site.sections = [MagicMock(title="Docs", path="docs/")]

    # Mock taxonomies (empty list for health screen)
    site.taxonomies = {}

    return site


@pytest.fixture
def bengal_app(mock_site: MagicMock) -> BengalApp:
    """
    Create BengalApp instance for testing.
    
    Returns app configured with mock site, starting on landing screen.
        
    """
    from bengal.cli.dashboard.app import BengalApp

    return BengalApp(site=mock_site, start_screen="landing")


@pytest.fixture
def bengal_app_no_site() -> BengalApp:
    """
    Create BengalApp instance without a site.
    
    Useful for testing error handling and empty states.
        
    """
    from bengal.cli.dashboard.app import BengalApp

    return BengalApp(site=None, start_screen="landing")


@pytest.fixture
async def pilot(bengal_app: BengalApp) -> AsyncGenerator[Pilot]:
    """
    Async fixture providing Textual pilot for interaction testing.
    
    Waits for app to mount before yielding.
    
    Usage:
        @pytest.mark.asyncio
        async def test_navigation(pilot):
            await pilot.press("1")
            assert pilot.app.screen.name == "build"
        
    """
    async with bengal_app.run_test() as pilot:
        # Wait for app to fully mount and install screens
        await pilot.pause()
        yield pilot


@pytest.fixture
async def pilot_no_site(bengal_app_no_site: BengalApp) -> AsyncGenerator[Pilot]:
    """
    Async fixture providing pilot for app without site.
    
    Useful for testing error states and notifications.
        
    """
    async with bengal_app_no_site.run_test() as pilot:
        await pilot.pause()
        yield pilot


@pytest.fixture
def mock_build_stats() -> dict:
    """Mock build statistics for testing."""
    return {
        "pages": 245,
        "sections": 18,
        "assets": 134,
        "taxonomies": 3,
        "duration_ms": 820,
        "phases": [
            {"name": "Discovery", "duration_ms": 45, "details": "245 pages"},
            {"name": "Taxonomies", "duration_ms": 12, "details": "3 taxonomies"},
            {"name": "Rendering", "duration_ms": 501, "details": "245 pages, 489/sec"},
            {"name": "Assets", "duration_ms": 150, "details": "134 files"},
            {"name": "Postprocess", "duration_ms": 112, "details": "sitemap, rss"},
        ],
        "cache_hit_rate": 0.95,
        "output_dir": "public/",
        "output_size_bytes": 4404019,
    }


@pytest.fixture
def mock_health_report() -> dict:
    """Mock health report for testing."""
    return {
        "summary": {
            "total_issues": 5,
            "errors": 1,
            "warnings": 4,
        },
        "categories": {
            "Links": {
                "issues": [
                    {
                        "severity": "error",
                        "message": "Broken internal link",
                        "file": "content/docs/guide.md",
                        "line": 45,
                        "link": "/docs/old-page",
                    }
                ]
            },
            "Images": {
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Missing alt text",
                        "file": "content/blog/post.md",
                        "line": 23,
                    },
                    {
                        "severity": "warning",
                        "message": "Large image (>1MB)",
                        "file": "content/assets/hero.png",
                        "size_bytes": 2500000,
                    },
                ]
            },
            "Frontmatter": {
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Missing title",
                        "file": "content/docs/untitled.md",
                    }
                ]
            },
            "Performance": {
                "issues": [
                    {
                        "severity": "warning",
                        "message": "Page exceeds size threshold",
                        "file": "content/api/reference.md",
                        "size_kb": 450,
                    }
                ]
            },
        },
    }


@pytest.fixture
def mock_serve_stats() -> dict:
    """Mock serve statistics for testing."""
    return {
        "host": "localhost",
        "port": 3000,
        "url": "http://localhost:3000",
        "watching": True,
        "rebuild_count": 3,
        "last_rebuild_ms": 145,
        "build_history": [820, 145, 132, 128, 125],
        "watched_files": 378,
        "changes": [
            {"file": "content/docs/guide.md", "type": "modified", "time": "12:45:32"},
            {"file": "content/blog/new-post.md", "type": "created", "time": "12:44:15"},
        ],
    }


@pytest.fixture
async def headless_app():
    """
    Async context manager for testing Textual apps in headless mode.
    
    Usage:
        async with headless_app() as create_app:
            app = create_app(BengalBuildDashboard)
            async with app.run_test() as pilot:
                await pilot.press("q")
        
    """

    async def _create_app(app_class, *args, **kwargs):
        """Create an app instance for testing."""
        return app_class(*args, **kwargs)

    yield _create_app
