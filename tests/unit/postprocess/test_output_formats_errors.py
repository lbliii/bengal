"""
Tests for error handling in parallel file writes.

These tests ensure that:
- Write failures are logged and don't crash the generator
- Partial failures result in correct counts
- All writes complete before generate() returns
- Errors are properly propagated

Regression test for: ThreadPoolExecutor error handling (json_generator.py:206-208)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from bengal.postprocess.output_formats.json_generator import PageJSONGenerator
from bengal.postprocess.output_formats.txt_generator import PageTxtGenerator


class TestParallelWriteErrorHandling:
    """Test error handling during parallel file writes."""

    def test_single_write_failure_doesnt_crash(self, tmp_path: Path) -> None:
        """Verify a single write failure doesn't crash the entire generation."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create multiple pages
        pages = []
        for i in range(5):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        # Make one directory unwritable to simulate failure
        # Create all directories first
        for i in range(5):
            (output_dir / f"page{i}").mkdir(parents=True)

        # Make page2 directory read-only (causes write to fail)
        readonly_dir = output_dir / "page2"
        readonly_dir.chmod(0o444)

        try:
            generator = PageJSONGenerator(mock_site)
            count = generator.generate(pages)

            # Should have generated 4 out of 5 files (page2 failed)
            assert count == 4, f"Expected 4 successful writes (1 should fail), got {count}"

            # Verify the successful files exist
            for i in [0, 1, 3, 4]:
                assert (output_dir / f"page{i}/index.json").exists(), (
                    f"page{i}/index.json should exist"
                )

            # page2 should not have a JSON file
            assert not (output_dir / "page2/index.json").exists(), (
                "page2/index.json should not exist due to write failure"
            )
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_all_writes_complete_before_return(self, tmp_path: Path) -> None:
        """Verify all parallel writes complete before generate() returns."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        pages = []
        for i in range(10):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        generator = PageJSONGenerator(mock_site)
        count = generator.generate(pages)

        # After generate() returns, all files should exist
        assert count == 10, f"Expected 10 writes, got {count}"

        for i in range(10):
            json_path = output_dir / f"page{i}/index.json"
            assert json_path.exists(), (
                f"page{i}/index.json should exist after generate() returns. "
                "If missing, writes may not have completed before return."
            )

    def test_write_count_accurate_with_failures(self, tmp_path: Path, monkeypatch) -> None:
        """Verify write count is accurate when some writes fail."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        pages = []
        for i in range(6):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        # Track how many times write is called
        fail_indices = {1, 3, 5}  # Fail pages 1, 3, 5

        original_mkdir = Path.mkdir

        def selective_mkdir(self, *args, **kwargs):
            # Check if this is a page directory we want to fail
            for idx in fail_indices:
                if f"page{idx}" in str(self):
                    raise PermissionError(f"Simulated failure for {self}")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", selective_mkdir)

        generator = PageJSONGenerator(mock_site)
        count = generator.generate(pages)

        # Should succeed for pages 0, 2, 4 (3 successes)
        assert count == 3, f"Expected 3 successful writes (3 should fail), got {count}"

    def test_txt_generator_handles_write_failure(self, tmp_path: Path) -> None:
        """Verify PageTxtGenerator handles write failures gracefully."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        pages = []
        for i in range(3):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        # Create directories and make one readonly
        for i in range(3):
            (output_dir / f"page{i}").mkdir(parents=True)

        readonly_dir = output_dir / "page1"
        readonly_dir.chmod(0o444)

        try:
            generator = PageTxtGenerator(mock_site)
            count = generator.generate(pages)

            # Should have 2 successful writes
            assert count == 2, f"Expected 2 successful writes, got {count}"

            # Verify successful files
            assert (output_dir / "page0/index.txt").exists()
            assert not (output_dir / "page1/index.txt").exists()
            assert (output_dir / "page2/index.txt").exists()
        finally:
            readonly_dir.chmod(0o755)

    def test_empty_pages_returns_zero(self, tmp_path: Path) -> None:
        """Verify empty pages list returns 0 without error."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        mock_site.pages = []

        generator = PageJSONGenerator(mock_site)
        count = generator.generate([])

        assert count == 0, "Empty pages should return 0"

    def test_pages_without_output_path_skipped(self, tmp_path: Path) -> None:
        """Verify pages without output_path are skipped gracefully."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Mix of pages with and without output_path
        pages = []

        page_with_output = self._create_mock_page(
            title="Has Output",
            url="/has-output/",
            content="Content",
            output_path=output_dir / "has-output/index.html",
        )
        pages.append(page_with_output)

        page_without_output = self._create_mock_page(
            title="No Output",
            url="/no-output/",
            content="Content",
            output_path=None,  # No output path
        )
        pages.append(page_without_output)

        mock_site.pages = pages

        generator = PageJSONGenerator(mock_site)
        count = generator.generate(pages)

        # Should only generate for page with output_path
        assert count == 1
        assert (output_dir / "has-output/index.json").exists()

    def test_concurrent_writes_thread_safe(self, tmp_path: Path) -> None:
        """Verify concurrent writes don't cause race conditions."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create many pages to increase chance of race conditions
        pages = []
        for i in range(50):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i} with some additional text to make it more realistic",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        generator = PageJSONGenerator(mock_site)
        count = generator.generate(pages)

        # All should succeed
        assert count == 50, f"Expected 50 successful writes, got {count}"

        # Verify all files exist and have valid JSON
        import json

        for i in range(50):
            json_path = output_dir / f"page{i}/index.json"
            assert json_path.exists(), f"page{i}/index.json should exist"

            # Verify JSON is valid
            try:
                data = json.loads(json_path.read_text())
                assert data["title"] == f"Page {i}"
            except json.JSONDecodeError as e:
                pytest.fail(f"page{i}/index.json has invalid JSON: {e}")

    def test_accumulated_json_path_with_write_failure(self, tmp_path: Path) -> None:
        """Verify accumulated JSON mode handles write failures correctly."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create pages
        pages = []
        for i in range(3):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        # Create pre-accumulated JSON data (simulating rendering phase)
        accumulated_json = [
            (output_dir / "page0/index.json", {"url": "/page0/", "title": "Page 0"}),
            (output_dir / "page1/index.json", {"url": "/page1/", "title": "Page 1"}),
            (output_dir / "page2/index.json", {"url": "/page2/", "title": "Page 2"}),
        ]

        # Create directories and make one readonly
        for i in range(3):
            (output_dir / f"page{i}").mkdir(parents=True)

        readonly_dir = output_dir / "page1"
        readonly_dir.chmod(0o444)

        try:
            generator = PageJSONGenerator(mock_site)
            count = generator.generate(pages, accumulated_json=accumulated_json)

            # Should have 2 successful writes
            assert count == 2, f"Expected 2 successful writes, got {count}"
        finally:
            readonly_dir.chmod(0o755)

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
