"""Tests for incremental track item dependency expansion."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.core.page import Page
from bengal.orchestration.incremental.orchestrator import IncrementalOrchestrator


@pytest.fixture
def mock_site_with_tracks():
    """Create a mock site with track page and track items."""
    site = Mock()
    site.root_path = Path("/fake/site")
    content_root = site.root_path / "content"

    # Track page: content/getting-started/_index.md
    track_page_path = content_root / "getting-started" / "_index.md"
    track_page = Mock(spec=Page)
    track_page.source_path = track_page_path
    track_page.metadata = {"template": "tracks/single.html", "track_id": "getting-started"}
    track_page.slug = "getting-started"

    # Track items: content/getting-started/step1.md, step2.md
    item1_path = content_root / "getting-started" / "step1.md"
    item2_path = content_root / "getting-started" / "step2.md"
    item1 = Mock(spec=Page)
    item1.source_path = item1_path
    item2 = Mock(spec=Page)
    item2.source_path = item2_path

    page_by_path = {
        track_page_path: track_page,
        item1_path: item1,
        item2_path: item2,
    }
    site.page_by_source_path = page_by_path
    site.pages = [track_page, item1, item2]

    site.data = Mock()
    site.data.tracks = {
        "getting-started": {
            "title": "Getting Started",
            "items": ["getting-started/step1", "getting-started/step2.md"],
        }
    }

    return site


def test_add_track_item_dependencies_adds_items_when_track_page_dirty(
    mock_site_with_tracks,
) -> None:
    """When track page is in pages_to_rebuild, its track items are added."""
    orchestrator = IncrementalOrchestrator(mock_site_with_tracks)
    content_root = mock_site_with_tracks.root_path / "content"
    track_page_path = content_root / "getting-started" / "_index.md"
    item1_path = content_root / "getting-started" / "step1.md"
    item2_path = content_root / "getting-started" / "step2.md"

    pages_to_rebuild: set[Path] = {track_page_path}

    orchestrator._add_track_item_dependencies(pages_to_rebuild, mock_site_with_tracks)

    assert track_page_path in pages_to_rebuild
    assert item1_path in pages_to_rebuild
    assert item2_path in pages_to_rebuild


def test_add_track_item_dependencies_no_op_when_no_track_page(
    mock_site_with_tracks,
) -> None:
    """When no track page is in pages_to_rebuild, nothing is added."""
    orchestrator = IncrementalOrchestrator(mock_site_with_tracks)
    content_root = mock_site_with_tracks.root_path / "content"
    item1_path = content_root / "getting-started" / "step1.md"

    pages_to_rebuild: set[Path] = {item1_path}

    orchestrator._add_track_item_dependencies(pages_to_rebuild, mock_site_with_tracks)

    assert pages_to_rebuild == {item1_path}


def test_add_track_item_dependencies_no_op_when_no_tracks(mock_site_with_tracks) -> None:
    """When site has no tracks data, nothing is added."""
    mock_site_with_tracks.data.tracks = None
    orchestrator = IncrementalOrchestrator(mock_site_with_tracks)
    content_root = mock_site_with_tracks.root_path / "content"
    track_page_path = content_root / "getting-started" / "_index.md"

    pages_to_rebuild: set[Path] = {track_page_path}

    orchestrator._add_track_item_dependencies(pages_to_rebuild, mock_site_with_tracks)

    assert pages_to_rebuild == {track_page_path}
