"""Unit tests for bengal.postprocess.output_formats.utils module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.postprocess.output_formats.utils import (
    get_i18n_output_path,
    parallel_write_files,
    write_if_content_changed,
)


class TestGetI18nOutputPath:
    """Test get_i18n_output_path utility."""

    def test_returns_direct_path_without_i18n(self) -> None:
        """Test returns path directly under output_dir when i18n not configured."""
        site = MagicMock()
        site.config = {}
        site.output_dir = Path("/output")

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/index.json")

    def test_returns_direct_path_when_strategy_not_prefix(self) -> None:
        """Test returns direct path when strategy is not 'prefix'."""
        site = MagicMock()
        site.config = {"i18n": {"strategy": "suffix", "default_language": "en"}}
        site.output_dir = Path("/output")

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/index.json")

    def test_returns_direct_path_for_default_language(self) -> None:
        """Test returns direct path for default language without subdir."""
        site = MagicMock()
        site.config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "default_in_subdir": False,
            }
        }
        site.output_dir = Path("/output")
        site.current_language = "en"

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/index.json")

    def test_returns_language_path_for_non_default(self) -> None:
        """Test returns language-prefixed path for non-default language."""
        site = MagicMock()
        site.config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "default_in_subdir": False,
            }
        }
        site.output_dir = Path("/output")
        site.current_language = "es"

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/es/index.json")

    def test_returns_language_path_when_default_in_subdir(self) -> None:
        """Test returns language path when default_in_subdir is True."""
        site = MagicMock()
        site.config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "default_in_subdir": True,
            }
        }
        site.output_dir = Path("/output")
        site.current_language = "en"

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/en/index.json")

    def test_uses_default_language_when_current_not_set(self) -> None:
        """Test falls back to default_language when current_language not set."""
        site = MagicMock()
        site.config = {
            "i18n": {
                "strategy": "prefix",
                "default_language": "en",
                "default_in_subdir": False,
            }
        }
        site.output_dir = Path("/output")
        site.current_language = None

        result = get_i18n_output_path(site, "index.json")

        # Should use default "en" and not add prefix
        assert result == Path("/output/index.json")

    def test_handles_various_filenames(self) -> None:
        """Test with various filename inputs."""
        site = MagicMock()
        site.config = {"i18n": {"strategy": "prefix", "default_language": "en"}}
        site.output_dir = Path("/output")
        site.current_language = "fr"

        test_cases = [
            ("index.json", Path("/output/fr/index.json")),
            ("search-index.json", Path("/output/fr/search-index.json")),
            ("llm-full.txt", Path("/output/fr/llm-full.txt")),
            ("sitemap.xml", Path("/output/fr/sitemap.xml")),
        ]

        for filename, expected in test_cases:
            result = get_i18n_output_path(site, filename)
            assert result == expected, f"Failed for: {filename}"

    def test_handles_empty_i18n_config(self) -> None:
        """Test handles empty i18n config dict."""
        site = MagicMock()
        site.config = {"i18n": {}}
        site.output_dir = Path("/output")

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/index.json")

    def test_handles_none_i18n_config(self) -> None:
        """Test handles None i18n config."""
        site = MagicMock()
        site.config = {"i18n": None}
        site.output_dir = Path("/output")

        result = get_i18n_output_path(site, "index.json")

        assert result == Path("/output/index.json")


class TestParallelWriteFiles:
    """Test parallel_write_files utility."""

    def test_writes_all_files(self) -> None:
        """Test that all files are written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            items = [
                (base / "a.txt", "content a"),
                (base / "b.txt", "content b"),
                (base / "c.txt", "content c"),
            ]

            def write_fn(path: Path, content: str) -> None:
                path.write_text(content)

            count = parallel_write_files(items, write_fn)

            assert count == 3
            assert (base / "a.txt").read_text() == "content a"
            assert (base / "b.txt").read_text() == "content b"
            assert (base / "c.txt").read_text() == "content c"

    def test_returns_zero_for_empty_list(self) -> None:
        """Test returns zero for empty items list."""
        count = parallel_write_files([], lambda p, c: None)

        assert count == 0

    def test_continues_on_single_failure(self) -> None:
        """Test that other files are written even if one fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            items = [
                (base / "a.txt", "content a"),
                (base / "fail.txt", "fail"),
                (base / "c.txt", "content c"),
            ]

            def write_fn(path: Path, content: str) -> None:
                if "fail" in str(path):
                    raise OSError("Simulated failure")
                path.write_text(content)

            count = parallel_write_files(items, write_fn, operation_name="test_write")

            assert count == 2  # 2 succeeded, 1 failed
            assert (base / "a.txt").read_text() == "content a"
            assert (base / "c.txt").read_text() == "content c"
            assert not (base / "fail.txt").exists()

    def test_respects_max_workers(self) -> None:
        """Test that max_workers parameter is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            items = [(base / f"{i}.txt", f"content {i}") for i in range(20)]

            def write_fn(path: Path, content: str) -> None:
                path.write_text(content)

            # Should work with small worker count
            count = parallel_write_files(items, write_fn, max_workers=2)

            assert count == 20

    def test_creates_parent_directories(self) -> None:
        """Test that parent directories are created by write function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            items = [
                (base / "sub" / "dir" / "file.txt", "nested"),
            ]

            def write_fn(path: Path, content: str) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

            count = parallel_write_files(items, write_fn)

            assert count == 1
            assert (base / "sub" / "dir" / "file.txt").read_text() == "nested"


class TestWriteIfContentChanged:
    """Test write_if_content_changed utility."""

    def test_writes_new_file(self) -> None:
        """Test writes file when it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "new.json"

            result = write_if_content_changed(path, '{"key": "value"}')

            assert result is True
            assert path.exists()
            assert path.read_text() == '{"key": "value"}'

    def test_creates_hash_file(self) -> None:
        """Test creates hash sidecar file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"

            write_if_content_changed(path, "content")

            hash_path = path.parent / "data.json.hash"
            assert hash_path.exists()
            # SHA-256 hash is 64 hex characters
            assert len(hash_path.read_text().strip()) == 64

    def test_skips_unchanged_content(self) -> None:
        """Test skips write when content unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"
            content = '{"stable": true}'

            # First write
            result1 = write_if_content_changed(path, content)
            mtime1 = path.stat().st_mtime

            # Wait a tiny bit to ensure mtime would change
            import time

            time.sleep(0.01)

            # Second write with same content
            result2 = write_if_content_changed(path, content)
            mtime2 = path.stat().st_mtime

            assert result1 is True  # First write happened
            assert result2 is False  # Second write skipped
            assert mtime1 == mtime2  # File not modified

    def test_writes_changed_content(self) -> None:
        """Test writes when content has changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"

            result1 = write_if_content_changed(path, "version 1")
            result2 = write_if_content_changed(path, "version 2")

            assert result1 is True
            assert result2 is True
            assert path.read_text() == "version 2"

    def test_updates_hash_on_change(self) -> None:
        """Test hash file is updated when content changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"
            hash_path = path.parent / "data.json.hash"

            write_if_content_changed(path, "content 1")
            hash1 = hash_path.read_text().strip()

            write_if_content_changed(path, "content 2")
            hash2 = hash_path.read_text().strip()

            assert hash1 != hash2

    def test_custom_hash_suffix(self) -> None:
        """Test custom hash suffix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"

            write_if_content_changed(path, "content", hash_suffix=".sha256")

            hash_path = path.parent / "data.json.sha256"
            assert hash_path.exists()

    def test_handles_corrupted_hash_file(self) -> None:
        """Test handles corrupted hash file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.json"
            hash_path = path.parent / "data.json.hash"

            # Write initial content
            write_if_content_changed(path, "content")

            # Corrupt the hash file
            hash_path.write_text("not a valid hash")

            # Should still work (write because hash doesn't match)
            result = write_if_content_changed(path, "content")

            # Should rewrite and fix the hash
            assert result is True

    def test_creates_parent_directories(self) -> None:
        """Test creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "dir" / "data.json"

            result = write_if_content_changed(path, "nested content")

            assert result is True
            assert path.exists()
            assert path.read_text() == "nested content"

    def test_handles_unicode_content(self) -> None:
        """Test handles unicode content correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "unicode.json"
            content = '{"message": "日本語 中文 한국어"}'

            result = write_if_content_changed(path, content)

            assert result is True
            assert path.read_text(encoding="utf-8") == content

    def test_hash_is_content_based(self) -> None:
        """Test that same content produces same hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = Path(tmpdir) / "file1.json"
            path2 = Path(tmpdir) / "file2.json"
            content = '{"same": "content"}'

            write_if_content_changed(path1, content)
            write_if_content_changed(path2, content)

            hash1 = (path1.parent / "file1.json.hash").read_text().strip()
            hash2 = (path2.parent / "file2.json.hash").read_text().strip()

            assert hash1 == hash2
