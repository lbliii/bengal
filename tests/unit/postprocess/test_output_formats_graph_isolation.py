"""
Tests for graph data isolation in per-page JSON generation.

These tests ensure that shared graph_data passed to PageJSONGenerator
is not mutated when processing multiple pages. This prevents the
'isCurrent' flag from leaking across pages.

Regression test for: Graph data mutation bug (json_generator.py:454-456)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import Mock

from bengal.postprocess.output_formats.json_generator import PageJSONGenerator


class TestGraphDataIsolation:
    """Ensure graph data is not mutated when generating per-page JSON."""

    def test_graph_data_not_mutated_across_pages(self, tmp_path: Path) -> None:
        """CRITICAL: Verify shared graph_data is not mutated when processing multiple pages.

        This is a regression test for a bug where adding isCurrent=True to nodes
        would persist in the shared graph_data, causing incorrect visualization
        for subsequent pages.
        """
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create shared graph data with multiple interconnected nodes
        graph_data = {
            "nodes": [
                {"id": "page1", "url": "/page1/", "incoming_refs": 5, "outgoing_refs": 3},
                {"id": "page2", "url": "/page2/", "incoming_refs": 3, "outgoing_refs": 2},
                {"id": "page3", "url": "/page3/", "incoming_refs": 1, "outgoing_refs": 1},
            ],
            "edges": [
                {"source": "page1", "target": "page2"},
                {"source": "page2", "target": "page3"},
                {"source": "page1", "target": "page3"},
            ],
        }

        # Deep copy to compare later
        original_graph_data = copy.deepcopy(graph_data)

        # Create pages matching graph nodes
        pages = []
        for i in range(1, 4):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content for page {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        # Generate JSON with shared graph data
        generator = PageJSONGenerator(mock_site, graph_data=graph_data)
        generator.generate(pages)

        # CRITICAL ASSERTION: Original graph_data must not be mutated
        assert graph_data == original_graph_data, (
            "graph_data was mutated! This causes 'isCurrent' flags to leak across pages. "
            "The PageJSONGenerator should copy nodes before adding isCurrent."
        )

        # Verify no node in original data has isCurrent
        for node in graph_data["nodes"]:
            assert "isCurrent" not in node, (
                f"Node {node['id']} has 'isCurrent' flag in shared graph_data. "
                "This mutation will cause incorrect behavior for other pages."
            )

    def test_each_page_json_has_single_current_node(self, tmp_path: Path) -> None:
        """Verify each page's graph connections have exactly one isCurrent node."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        graph_data = {
            "nodes": [
                {"id": "page1", "url": "/page1/", "incoming_refs": 5, "outgoing_refs": 3},
                {"id": "page2", "url": "/page2/", "incoming_refs": 3, "outgoing_refs": 2},
                {"id": "page3", "url": "/page3/", "incoming_refs": 1, "outgoing_refs": 1},
            ],
            "edges": [
                {"source": "page1", "target": "page2"},
                {"source": "page2", "target": "page3"},
            ],
        }

        pages = []
        for i in range(1, 4):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        generator = PageJSONGenerator(mock_site, graph_data=graph_data)
        generator.generate(pages)

        # Check each generated JSON file
        for i in range(1, 4):
            json_path = output_dir / f"page{i}/index.json"
            assert json_path.exists(), f"JSON file for page{i} should exist"

            data = json.loads(json_path.read_text())

            if "graph" in data and data["graph"].get("nodes"):
                current_nodes = [n for n in data["graph"]["nodes"] if n.get("isCurrent")]
                assert len(current_nodes) == 1, (
                    f"Page {i} should have exactly 1 current node, found {len(current_nodes)}. "
                    "Multiple current nodes indicates mutation bug."
                )
                assert current_nodes[0]["id"] == f"page{i}", (
                    f"Wrong node marked as current for page{i}. "
                    f"Expected 'page{i}', got '{current_nodes[0]['id']}'"
                )

    def test_graph_data_reusable_after_generation(self, tmp_path: Path) -> None:
        """Verify graph_data can be reused for multiple generation calls."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        graph_data = {
            "nodes": [
                {"id": "page1", "url": "/page1/", "incoming_refs": 2, "outgoing_refs": 1},
                {"id": "page2", "url": "/page2/", "incoming_refs": 1, "outgoing_refs": 2},
            ],
            "edges": [{"source": "page1", "target": "page2"}],
        }

        page1 = self._create_mock_page(
            title="Page 1",
            url="/page1/",
            content="Content 1",
            output_path=output_dir / "page1/index.html",
        )

        page2 = self._create_mock_page(
            title="Page 2",
            url="/page2/",
            content="Content 2",
            output_path=output_dir / "page2/index.html",
        )

        mock_site.pages = [page1, page2]

        # First generation
        generator1 = PageJSONGenerator(mock_site, graph_data=graph_data)
        generator1.generate([page1])

        # Second generation with SAME graph_data (simulates incremental build)
        generator2 = PageJSONGenerator(mock_site, graph_data=graph_data)
        generator2.generate([page2])

        # Verify page2's JSON has correct current node (not page1)
        json_path = output_dir / "page2/index.json"
        data = json.loads(json_path.read_text())

        if "graph" in data and data["graph"].get("nodes"):
            current_nodes = [n for n in data["graph"]["nodes"] if n.get("isCurrent")]
            assert len(current_nodes) == 1
            assert current_nodes[0]["id"] == "page2", (
                "Second generation should mark page2 as current, not page1. "
                "This indicates graph_data was mutated by first generation."
            )

    def test_empty_graph_data_handled(self, tmp_path: Path) -> None:
        """Verify empty or missing graph data is handled gracefully."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test Page",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        # Test with None
        generator = PageJSONGenerator(mock_site, graph_data=None)
        count = generator.generate([page])
        assert count == 1

        json_path = output_dir / "test/index.json"
        data = json.loads(json_path.read_text())
        assert "graph" not in data, "No graph key should be present when graph_data is None"

    def test_graph_with_no_edges_for_page(self, tmp_path: Path) -> None:
        """Verify pages not in graph are handled gracefully."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Graph data that doesn't include our test page
        graph_data = {
            "nodes": [
                {"id": "other1", "url": "/other1/", "incoming_refs": 1, "outgoing_refs": 1},
            ],
            "edges": [],
        }

        page = self._create_mock_page(
            title="Isolated Page",
            url="/isolated/",
            content="Not in graph",
            output_path=output_dir / "isolated/index.html",
        )
        mock_site.pages = [page]

        generator = PageJSONGenerator(mock_site, graph_data=graph_data)
        count = generator.generate([page])
        assert count == 1

        json_path = output_dir / "isolated/index.json"
        data = json.loads(json_path.read_text())
        # Page not in graph should not have graph connections
        assert "graph" not in data or data.get("graph") is None

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path, baseurl: str = "") -> Mock:
        """Create a mock Site instance."""
        from datetime import datetime

        site = Mock()
        site.site_dir = site_dir
        site.output_dir = output_dir
        site.dev_mode = False
        site.versioning_enabled = False
        site.build_time = datetime(2024, 1, 1, 12, 0, 0)
        site.config = {
            "title": "Test Site",
            "baseurl": baseurl,
            "description": "Test site description",
        }
        site.title = "Test Site"
        site.baseurl = baseurl
        site.description = "Test site description"
        site.pages = []
        return site

    def _create_mock_page(
        self,
        title: str,
        url: str,
        content: str,
        output_path: Path | None,
        tags: list[str] | None = None,
        section_name: str | None = None,
        metadata: dict | None = None,
    ) -> Mock:
        """Create a mock Page instance."""
        page = Mock()
        page.title = title
        page.href = url
        page._path = url
        page.content = content
        page.html_content = content
        page.plain_text = content
        page.output_path = output_path
        page.tags = tags or []
        page.date = None
        page.metadata = metadata or {}
        page.source_path = Path("content/test.md")
        page.version = None

        if section_name:
            section = Mock()
            section.name = section_name
            page._section = section
        else:
            page._section = None

        return page
