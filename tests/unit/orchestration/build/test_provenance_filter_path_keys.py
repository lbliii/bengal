"""Tests for provenance filter path key alignment.

Ensures _detect_changed_data_files and _detect_changed_templates use
cache._cache_key for file_fingerprints lookups (not str(path)).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import content_key
from bengal.orchestration.build.provenance_filter import (
    _detect_changed_data_files,
    _detect_changed_templates,
    _get_pages_for_data_file,
    _get_pages_for_template,
    _get_taxonomy_term_pages_for_member,
)
from bengal.utils.primitives.hashing import hash_file


@pytest.fixture
def mock_cache(tmp_path: Path):
    """BuildCache mock with _cache_key, file_fingerprints, and encapsulated API."""
    cache = MagicMock()
    cache.site_root = tmp_path
    cache.file_fingerprints = {}

    def _cache_key(path: Path) -> str:
        return str(content_key(path, tmp_path))

    from bengal.cache.build_cache.fingerprint import FileFingerprint

    def get_fp(path):
        raw = cache.file_fingerprints.get(cache._cache_key(path))
        return FileFingerprint.from_dict(raw) if raw else None

    def set_fp(path, data):
        store = data.to_dict() if isinstance(data, FileFingerprint) else data
        cache.file_fingerprints[cache._cache_key(path)] = store

    cache._cache_key = _cache_key
    cache.get_file_fingerprint = get_fp
    cache.set_file_fingerprint = set_fp
    return cache


@pytest.fixture
def mock_site(tmp_path: Path):
    """Site mock with root_path."""
    site = MagicMock()
    site.root_path = tmp_path
    site.theme_path = None
    return site


class TestDetectChangedDataFilesPathKeys:
    """Tests for _detect_changed_data_files path key alignment."""

    def test_uses_cache_key_for_lookup(
        self, mock_cache: MagicMock, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Data file lookup uses cache._cache_key, not str(path)."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        data_file = data_dir / "team.yaml"
        data_file.write_text("name: test")

        # Store fingerprint with content_key format (as cache.update_file would)
        file_key = mock_cache._cache_key(data_file)
        mock_cache.file_fingerprints[file_key] = {
            "mtime": data_file.stat().st_mtime,
            "size": data_file.stat().st_size,
            "hash": hash_file(data_file),
        }

        changed = _detect_changed_data_files(mock_cache, mock_site)

        # File unchanged - should NOT be in changed (cache hit)
        assert data_file not in changed

    def test_detects_changed_data_file(
        self, mock_cache: MagicMock, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Changed data file is detected via cache_key lookup."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        data_file = data_dir / "team.yaml"
        data_file.write_text("name: test")

        file_key = mock_cache._cache_key(data_file)
        mock_cache.file_fingerprints[file_key] = {
            "mtime": 0,
            "size": 0,
            "hash": "old_hash",
        }

        changed = _detect_changed_data_files(mock_cache, mock_site)

        assert data_file in changed


class TestDetectChangedTemplatesPathKeys:
    """Tests for _detect_changed_templates path key alignment."""

    def test_uses_cache_key_for_lookup_and_store(
        self, mock_cache: MagicMock, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Template lookup and store use cache._cache_key."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        tpl_file = templates_dir / "base.html"
        tpl_file.write_text("<html></html>")

        file_key = mock_cache._cache_key(tpl_file)
        mock_cache.file_fingerprints[file_key] = {
            "mtime": tpl_file.stat().st_mtime,
            "size": tpl_file.stat().st_size,
            "hash": hash_file(tpl_file),
        }

        changed = _detect_changed_templates(mock_cache, mock_site)

        assert tpl_file not in changed
        # Should have stored current fingerprint with same key
        assert file_key in mock_cache.file_fingerprints


class TestGetTaxonomyTermPagesForMemberPathKeys:
    """Tests for _get_taxonomy_term_pages_for_member path key alignment."""

    def test_uses_cache_key_for_page_tags_lookup(
        self, mock_cache: MagicMock, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Page_tags lookup uses cache._cache_key, not str(path)."""
        # page_tags is keyed by content_key (as taxonomy orchestration does)
        content_key_str = "content/docs/post.md"
        mock_cache.taxonomy_index = MagicMock()
        mock_cache.taxonomy_index.page_tags = {
            content_key_str: {"python", "web"},
        }

        # Call with absolute path (as watcher/forced_changed would supply)
        member_path_absolute = tmp_path / "content" / "docs" / "post.md"
        member_path_absolute.parent.mkdir(parents=True, exist_ok=True)
        member_path_absolute.touch()

        term_pages = _get_taxonomy_term_pages_for_member(
            mock_cache, member_path_absolute, mock_site
        )

        # Should find tags and return term page paths (virtual tag pages)
        assert len(term_pages) == 2
        term_paths = {str(p) for p in term_pages}
        assert "_generated/tags/tag:python" in term_paths
        assert "_generated/tags/tag:web" in term_paths

    def test_absolute_and_relative_path_return_same_terms(
        self, mock_cache: MagicMock, mock_site: MagicMock, tmp_path: Path
    ) -> None:
        """Absolute and relative member_path produce same lookup result."""
        content_key_str = "content/blog/foo.md"
        mock_cache.taxonomy_index = MagicMock()
        mock_cache.taxonomy_index.page_tags = {content_key_str: {"devops"}}

        member_absolute = tmp_path / "content" / "blog" / "foo.md"
        member_absolute.parent.mkdir(parents=True, exist_ok=True)
        member_absolute.touch()

        terms_absolute = _get_taxonomy_term_pages_for_member(mock_cache, member_absolute, mock_site)
        # Relative path must resolve under site_root for content_key to match
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            terms_relative = _get_taxonomy_term_pages_for_member(
                mock_cache, Path("content/blog/foo.md"), mock_site
            )
        finally:
            os.chdir(old_cwd)

        assert terms_absolute == terms_relative
        assert len(terms_absolute) == 1
        assert any("devops" in str(p) for p in terms_absolute)


class TestGetPagesForDataFilePathKeys:
    """Tests for _get_pages_for_data_file path key alignment."""

    def test_uses_cache_key_for_dependency_lookup(
        self, mock_cache: MagicMock, tmp_path: Path
    ) -> None:
        """Data file dependency lookup uses cache._cache_key, not f'data:{path}'."""
        data_file = tmp_path / "data" / "team.yaml"
        data_file.parent.mkdir(parents=True)
        data_file.write_text("name: test")

        dep_key = mock_cache._cache_key(data_file)
        mock_cache.dependencies = {
            "content/blog/post.md": {dep_key},
        }

        pages = _get_pages_for_data_file(mock_cache, data_file)

        assert len(pages) == 1
        assert Path("content/blog/post.md") in pages


class TestGetPagesForTemplatePathKeys:
    """Tests for _get_pages_for_template path key alignment."""

    def test_uses_cache_key_for_reverse_dependency_lookup(
        self, mock_cache: MagicMock, tmp_path: Path
    ) -> None:
        """Template reverse dependency lookup uses cache._cache_key, not str(path)."""
        template_file = tmp_path / "templates" / "base.html"
        template_file.parent.mkdir(parents=True)
        template_file.write_text("<html></html>")

        template_key = mock_cache._cache_key(template_file)
        mock_cache.reverse_dependencies = {
            template_key: {"content/about.md"},
        }
        mock_cache.dependencies = {}

        pages = _get_pages_for_template(mock_cache, template_file)

        assert len(pages) == 1
        assert Path("content/about.md") in pages
