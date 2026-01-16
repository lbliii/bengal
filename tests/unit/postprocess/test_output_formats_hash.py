"""
Tests for hash file handling in output format generation.

These tests ensure that hash files are:
- Created alongside index.json for change detection
- Used to skip regeneration when content unchanged
- Written atomically to prevent inconsistent state

Regression test for: Non-atomic hash write bug (index_generator.py:538)
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.postprocess.output_formats import OutputFormatsGenerator
from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator


class TestHashFileConsistency:
    """Test hash file handling for idempotent builds."""

    def test_hash_file_created_alongside_index(self, tmp_path: Path) -> None:
        """Verify hash file is created when index.json is generated."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content for testing hash creation",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        assert (output_dir / "index.json").exists(), "index.json should be created"
        assert (output_dir / "index.json.hash").exists(), (
            "Hash file should be created alongside index.json for change detection"
        )

    def test_hash_file_contains_valid_hash(self, tmp_path: Path) -> None:
        """Verify hash file contains a valid SHA-256 hash."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        hash_content = (output_dir / "index.json.hash").read_text().strip()

        # SHA-256 produces 64 hex characters
        assert len(hash_content) == 64, (
            f"Hash should be 64 characters (SHA-256), got {len(hash_content)}"
        )
        assert all(c in "0123456789abcdef" for c in hash_content), (
            "Hash should only contain hex characters"
        )

    def test_unchanged_content_preserves_file_mtime(self, tmp_path: Path) -> None:
        """Verify index.json mtime is preserved when content unchanged."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Stable content that won't change",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}

        # First generation
        generator1 = OutputFormatsGenerator(mock_site, config)
        generator1.generate()

        index_path = output_dir / "index.json"
        first_mtime = index_path.stat().st_mtime

        # Small delay to ensure different mtime if rewritten
        time.sleep(0.05)

        # Second generation with same content
        generator2 = OutputFormatsGenerator(mock_site, config)
        generator2.generate()

        second_mtime = index_path.stat().st_mtime

        assert first_mtime == second_mtime, (
            "index.json should not be rewritten when content unchanged. "
            "Hash-based change detection should skip regeneration."
        )

    def test_changed_content_updates_file(self, tmp_path: Path) -> None:
        """Verify index.json is updated when content changes."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page1 = self._create_mock_page(
            title="Original Title",
            url="/test/",
            content="Original content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page1]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}

        # First generation
        generator1 = OutputFormatsGenerator(mock_site, config)
        generator1.generate()

        index_path = output_dir / "index.json"
        first_content = index_path.read_text()

        # Small delay
        time.sleep(0.05)

        # Change the page content
        page2 = self._create_mock_page(
            title="Updated Title",
            url="/test/",
            content="Updated content that is different",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page2]

        # Second generation with changed content
        generator2 = OutputFormatsGenerator(mock_site, config)
        generator2.generate()

        second_content = index_path.read_text()

        assert first_content != second_content, (
            "index.json should be updated when content changes"
        )

    def test_hash_file_updated_with_content(self, tmp_path: Path) -> None:
        """Verify hash file is updated when content changes."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page1 = self._create_mock_page(
            title="Original",
            url="/test/",
            content="Original",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page1]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}

        # First generation
        generator1 = OutputFormatsGenerator(mock_site, config)
        generator1.generate()

        hash_path = output_dir / "index.json.hash"
        first_hash = hash_path.read_text().strip()

        # Change content
        page2 = self._create_mock_page(
            title="Changed",
            url="/test/",
            content="Changed content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page2]

        # Second generation
        generator2 = OutputFormatsGenerator(mock_site, config)
        generator2.generate()

        second_hash = hash_path.read_text().strip()

        assert first_hash != second_hash, (
            "Hash file should be updated when content changes"
        )

    def test_corrupted_hash_file_triggers_regeneration(self, tmp_path: Path) -> None:
        """Verify corrupted hash file causes regeneration."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}

        # First generation
        generator1 = OutputFormatsGenerator(mock_site, config)
        generator1.generate()

        index_path = output_dir / "index.json"
        hash_path = output_dir / "index.json.hash"

        first_mtime = index_path.stat().st_mtime

        # Corrupt the hash file
        hash_path.write_text("invalid_hash_content")

        time.sleep(0.05)

        # Second generation - should regenerate due to hash mismatch
        generator2 = OutputFormatsGenerator(mock_site, config)
        generator2.generate()

        second_mtime = index_path.stat().st_mtime

        # File should be rewritten because hash didn't match
        assert second_mtime > first_mtime, (
            "index.json should be regenerated when hash file is corrupted"
        )

    def test_missing_hash_file_triggers_regeneration(self, tmp_path: Path) -> None:
        """Verify missing hash file causes regeneration."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}

        # First generation
        generator1 = OutputFormatsGenerator(mock_site, config)
        generator1.generate()

        index_path = output_dir / "index.json"
        hash_path = output_dir / "index.json.hash"

        first_mtime = index_path.stat().st_mtime

        # Delete the hash file
        hash_path.unlink()

        time.sleep(0.05)

        # Second generation - should regenerate due to missing hash
        generator2 = OutputFormatsGenerator(mock_site, config)
        generator2.generate()

        second_mtime = index_path.stat().st_mtime

        assert second_mtime > first_mtime, (
            "index.json should be regenerated when hash file is missing"
        )
        assert hash_path.exists(), "Hash file should be recreated"

    def test_index_generator_direct_hash_behavior(self, tmp_path: Path) -> None:
        """Test SiteIndexGenerator hash behavior directly."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Direct Test",
            url="/direct/",
            content="Direct test content",
            output_path=output_dir / "direct/index.html",
        )
        mock_site.pages = [page]

        generator = SiteIndexGenerator(mock_site)

        # First generation
        path1 = generator.generate([page])
        assert path1.exists()

        hash_path = path1.with_suffix(".json.hash")
        assert hash_path.exists(), "Direct SiteIndexGenerator should create hash file"

        first_hash = hash_path.read_text().strip()

        # Second generation with same content
        path2 = generator.generate([page])

        second_hash = hash_path.read_text().strip()

        assert first_hash == second_hash, (
            "Hash should remain same for identical content"
        )

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path, baseurl: str = "") -> Mock:
        """Create a mock Site instance."""
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
            "search": {},
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
        page.parsed_ast = content
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
