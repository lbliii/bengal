"""
Integration tests for version-scoped search indexes.

Tests that versioned sites generate per-version search indexes and that
each index only contains pages from its corresponding version.

RFC: rfc-version-scoped-search.md
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bengal.postprocess.output_formats import OutputFormatsGenerator


@pytest.mark.bengal(testroot="test-versioned")
class TestVersionedSearchIndexes:
    """Integration tests for version-scoped search indexes."""

    def test_versioned_site_generates_scoped_indexes(self, site, build_site):
        """Full build with versioning generates per-version indexes."""
        build_site()

        # Latest version at root
        latest_index = site.output_dir / "index.json"
        assert latest_index.exists(), "Latest version index should exist at root"

        # v1 version in subdirectory
        v1_index = site.output_dir / "docs" / "v1" / "index.json"
        assert v1_index.exists(), "v1 index should exist in docs/v1/"

        # v2 version in subdirectory
        v2_index = site.output_dir / "docs" / "v2" / "index.json"
        assert v2_index.exists(), "v2 index should exist in docs/v2/"

    def test_versioned_indexes_contain_only_their_version_pages(self, site, build_site):
        """Each version's index only contains pages from that version."""
        build_site()

        # Load latest version index
        latest_index = site.output_dir / "index.json"
        latest_data = json.loads(latest_index.read_text())

        # Load v1 index
        v1_index = site.output_dir / "docs" / "v1" / "index.json"
        v1_data = json.loads(v1_index.read_text())

        # Load v2 index
        v2_index = site.output_dir / "docs" / "v2" / "index.json"
        v2_data = json.loads(v2_index.read_text())

        # Verify content separation
        # Latest version should not have v1 pages
        latest_versions = {p.get("version") for p in latest_data["pages"] if p.get("version")}
        assert "v1" not in latest_versions, "Latest index should not contain v1 pages"
        assert "v2" not in latest_versions, "Latest index should not contain v2 pages"

        # v1 index should only have v1 pages
        v1_versions = {p.get("version") for p in v1_data["pages"] if p.get("version")}
        assert v1_versions == {"v1"} or len(v1_versions) == 0, (
            f"v1 index should only contain v1 pages, got: {v1_versions}"
        )

        # v2 index should only have v2 pages
        v2_versions = {p.get("version") for p in v2_data["pages"] if p.get("version")}
        assert v2_versions == {"v2"} or len(v2_versions) == 0, (
            f"v2 index should only contain v2 pages, got: {v2_versions}"
        )

    def test_versioned_indexes_have_valid_structure(self, site, build_site):
        """Each version index has valid structure with site metadata."""
        build_site()

        # Check all version indexes
        indexes = [
            site.output_dir / "index.json",
            site.output_dir / "docs" / "v1" / "index.json",
            site.output_dir / "docs" / "v2" / "index.json",
        ]

        for index_path in indexes:
            if not index_path.exists():
                continue  # Skip if index doesn't exist

            data = json.loads(index_path.read_text())

            # Assert structure
            assert "site" in data, f"{index_path} must have 'site' key"
            assert "pages" in data, f"{index_path} must have 'pages' key"
            assert "sections" in data, f"{index_path} must have 'sections' key"
            assert "tags" in data, f"{index_path} must have 'tags' key"

            # Assert site metadata
            assert isinstance(data["site"], dict)
            assert "title" in data["site"]
            assert "baseurl" in data["site"]

            # Assert collections are lists
            assert isinstance(data["pages"], list)
            assert isinstance(data["sections"], list)
            assert isinstance(data["tags"], list)

    def test_unversioned_site_generates_single_index(self, tmp_path):
        """Sites without versioning generate single index (backward compatibility)."""
        from unittest.mock import Mock

        output_dir = tmp_path / "public"
        output_dir.mkdir()

        # Create mock site without versioning
        mock_site = Mock()
        mock_site.output_dir = output_dir
        mock_site.dev_mode = False
        mock_site.config = {
            "title": "Test Site",
            "baseurl": "",
            "description": "Test site description",
        }
        mock_site.versioning_enabled = False
        mock_site.pages = []

        # Create a simple page
        page = Mock()
        page.title = "Test Page"
        page.url = "/test/"
        page.content = "Content"
        page.plain_text = "Content"
        page.output_path = output_dir / "test/index.html"
        page.tags = []
        page.date = None
        page.metadata = {}
        page.source_path = Path("content/test.md")
        page._section = None
        page.version = None  # No version

        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Should generate single index at root
        index_path = output_dir / "index.json"
        assert index_path.exists(), "Unversioned site should generate single index.json"

        # Should not generate version-specific indexes
        v1_index = output_dir / "docs" / "v1" / "index.json"
        assert not v1_index.exists(), (
            "Unversioned site should not generate version-specific indexes"
        )


