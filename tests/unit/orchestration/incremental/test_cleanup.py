"""
Tests for cleanup module of the incremental package.
"""

from unittest.mock import Mock

import pytest

from bengal.cache import BuildCache
from bengal.orchestration.incremental.cleanup import cleanup_deleted_files


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site."""
    site = Mock()
    site.root_path = tmp_path
    site.output_dir = tmp_path / "public"
    site.output_dir.mkdir(parents=True, exist_ok=True)
    return site


@pytest.fixture
def mock_cache():
    """Create a mock BuildCache."""
    cache = Mock(spec=BuildCache)
    cache.output_sources = {}
    cache.file_fingerprints = {}
    cache.taxonomy_index = Mock()
    cache.taxonomy_index.page_tags = {}
    cache.parsed_content = {}
    cache.file_fingerprints = {}
    cache.autodoc_tracker = Mock()
    return cache


class TestCleanupDeletedFiles:
    """Test cleanup of deleted source files."""

    def test_no_cleanup_when_output_sources_empty(self, mock_site, mock_cache):
        """No cleanup when output_sources is empty."""
        mock_cache.output_sources = {}

        count = cleanup_deleted_files(mock_site, mock_cache)

        assert count == 0

    def test_cleanup_deleted_source(self, mock_site, mock_cache, tmp_path):
        """Should delete output when source is deleted."""
        # Create output file
        output_path = mock_site.output_dir / "page" / "index.html"
        output_path.parent.mkdir(parents=True)
        output_path.write_text("<html></html>")

        # Source file doesn't exist
        source_path = tmp_path / "content" / "page.md"

        mock_cache.output_sources = {
            "page/index.html": str(source_path),
        }

        count = cleanup_deleted_files(mock_site, mock_cache)

        # Output should be deleted
        assert not output_path.exists()
        assert count == 1
        # Entry should be removed from cache
        assert "page/index.html" not in mock_cache.output_sources

    def test_cleanup_removes_empty_directories(self, mock_site, mock_cache, tmp_path):
        """Should remove empty parent directories after cleanup."""
        # Create nested output directory structure
        output_path = mock_site.output_dir / "deep" / "nested" / "page" / "index.html"
        output_path.parent.mkdir(parents=True)
        output_path.write_text("<html></html>")

        # Source file doesn't exist
        source_path = tmp_path / "content" / "deep" / "nested" / "page.md"

        mock_cache.output_sources = {
            "deep/nested/page/index.html": str(source_path),
        }

        count = cleanup_deleted_files(mock_site, mock_cache)

        # Output file and its parent dir should be deleted
        assert not output_path.exists()
        assert not output_path.parent.exists()
        assert count == 1

    def test_cleanup_removes_cache_entries(self, mock_site, mock_cache, tmp_path):
        """Should remove cache entries for deleted sources."""
        source_path = tmp_path / "content" / "page.md"

        mock_cache.output_sources = {
            "page/index.html": str(source_path),
        }
        mock_cache.file_fingerprints = {
            str(source_path): {"hash": "abc123", "mtime": 0, "size": 0},
        }
        mock_cache.taxonomy_index.page_tags = {
            str(source_path): {"python"},
        }
        mock_cache.parsed_content = {
            str(source_path): {"title": "Page"},
        }

        # Create output file
        output_path = mock_site.output_dir / "page" / "index.html"
        output_path.parent.mkdir(parents=True)
        output_path.write_text("<html></html>")

        cleanup_deleted_files(mock_site, mock_cache)

        # All cache entries for deleted source should be removed
        assert str(source_path) not in mock_cache.file_fingerprints
        assert str(source_path) not in mock_cache.taxonomy_index.page_tags
        assert str(source_path) not in mock_cache.parsed_content

    def test_no_cleanup_when_source_exists(self, mock_site, mock_cache, tmp_path):
        """Should not delete output when source exists."""
        # Create output file
        output_path = mock_site.output_dir / "page" / "index.html"
        output_path.parent.mkdir(parents=True)
        output_path.write_text("<html></html>")

        # Source file exists
        source_path = tmp_path / "content" / "page.md"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("Content")

        mock_cache.output_sources = {
            "page/index.html": str(source_path),
        }

        count = cleanup_deleted_files(mock_site, mock_cache)

        # Output should still exist
        assert output_path.exists()
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
