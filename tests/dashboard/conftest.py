"""
Pytest fixtures for Textual dashboard testing.

Provides async fixtures for testing Textual apps in headless mode,
snapshot testing helpers, and mock data generators.

Usage:
    async def test_build_dashboard(app: BengalBuildDashboard):
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert app.is_mounted
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


@pytest.fixture
def snapshot_path() -> Path:
    """Path to store dashboard snapshots for visual regression testing."""
    return Path(__file__).parent / "snapshots"


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
