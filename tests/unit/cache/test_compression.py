"""
Tests for cache compression utilities (PEP 784 - Zstandard).

Tests round-trip compression, format detection, and migration utilities.
Requires Python 3.14+ (uses stdlib compression.zstd).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bengal.cache.compression import (
    COMPRESSION_LEVEL,
    detect_format,
    get_compressed_path,
    get_json_path,
    load_auto,
    load_compressed,
    migrate_to_compressed,
    save_compressed,
)


class TestSaveLoadCompressed:
    """Tests for save_compressed and load_compressed functions."""

    def test_roundtrip_simple(self, tmp_path: Path) -> None:
        """Test basic round-trip: save and load returns same data."""
        data = {"version": 1, "entries": [{"name": "test", "value": 42}]}
        cache_path = tmp_path / "test.json.zst"

        save_compressed(data, cache_path)
        loaded = load_compressed(cache_path)

        assert loaded == data

    def test_roundtrip_complex(self, tmp_path: Path) -> None:
        """Test round-trip with complex nested data."""
        data = {
            "version": 5,
            "file_hashes": {"content/post.md": "abc123", "content/page.md": "def456"},
            "dependencies": {"post.md": ["base.html", "header.html"]},
            "taxonomy_deps": {"python": ["post1.md", "post2.md"]},
            "parsed_content": {
                "post.md": {
                    "html": "<h1>Title</h1><p>Content</p>",
                    "toc": "<nav>...</nav>",
                    "metadata_hash": "xyz789",
                }
            },
        }
        cache_path = tmp_path / "complex.json.zst"

        save_compressed(data, cache_path)
        loaded = load_compressed(cache_path)

        assert loaded == data

    def test_compression_ratio(self, tmp_path: Path) -> None:
        """Test that compression actually reduces file size."""
        # Create repetitive data (compresses well)
        data = {
            "entries": [{"path": f"content/posts/post-{i}.md", "title": f"Post {i}"} for i in range(100)]
        }
        cache_path = tmp_path / "large.json.zst"

        compressed_size = save_compressed(data, cache_path)

        # Calculate uncompressed size
        json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
        uncompressed_size = len(json_bytes)

        # Expect at least 3x compression (spike showed 12-14x)
        ratio = uncompressed_size / compressed_size
        assert ratio >= 3, f"Expected at least 3x compression, got {ratio:.1f}x"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that save_compressed creates parent directories."""
        nested_path = tmp_path / "deep" / "nested" / "cache.json.zst"
        data = {"test": True}

        save_compressed(data, nested_path)

        assert nested_path.exists()
        assert load_compressed(nested_path) == data

    def test_custom_compression_level(self, tmp_path: Path) -> None:
        """Test compression with different levels."""
        data = {"entries": list(range(1000))}

        # Level 1 (fastest)
        path_1 = tmp_path / "level1.json.zst"
        size_1 = save_compressed(data, path_1, level=1)

        # Level 9 (smaller but slower)
        path_9 = tmp_path / "level9.json.zst"
        size_9 = save_compressed(data, path_9, level=9)

        # Both should load correctly
        assert load_compressed(path_1) == data
        assert load_compressed(path_9) == data

        # Both should produce reasonable compression
        # Note: Level 9 doesn't always beat level 1 for small data
        json_size = len(json.dumps(data, separators=(",", ":")).encode("utf-8"))
        assert size_1 < json_size
        assert size_9 < json_size

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        """Test that loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_compressed(tmp_path / "nonexistent.json.zst")


class TestFormatDetection:
    """Tests for format detection utilities."""

    def test_detect_zstd(self) -> None:
        """Test detection of .json.zst files."""
        assert detect_format(Path("cache.json.zst")) == "zstd"
        assert detect_format(Path(".bengal/build_cache.json.zst")) == "zstd"

    def test_detect_json(self) -> None:
        """Test detection of .json files."""
        assert detect_format(Path("cache.json")) == "json"
        assert detect_format(Path(".bengal/build_cache.json")) == "json"

    def test_detect_unknown(self) -> None:
        """Test detection of unknown formats."""
        assert detect_format(Path("cache.txt")) == "unknown"
        assert detect_format(Path("cache")) == "unknown"

    def test_get_compressed_path(self) -> None:
        """Test getting compressed path from JSON path."""
        assert get_compressed_path(Path("cache.json")) == Path("cache.json.zst")
        assert get_compressed_path(Path(".bengal/tags.json")) == Path(".bengal/tags.json.zst")
        # Already compressed - return as-is
        assert get_compressed_path(Path("cache.json.zst")) == Path("cache.json.zst")

    def test_get_json_path(self) -> None:
        """Test getting JSON path from compressed path."""
        assert get_json_path(Path("cache.json.zst")) == Path("cache.json")
        assert get_json_path(Path(".bengal/tags.json.zst")) == Path(".bengal/tags.json")
        # Already JSON - return as-is
        assert get_json_path(Path("cache.json")) == Path("cache.json")


class TestLoadAuto:
    """Tests for auto-detection loading."""

    def test_load_compressed_first(self, tmp_path: Path) -> None:
        """Test that compressed format is preferred when both exist."""
        base_path = tmp_path / "cache.json"
        compressed_path = tmp_path / "cache.json.zst"

        # Create both files with different data
        json_data = {"source": "json"}
        zstd_data = {"source": "zstd"}

        with open(base_path, "w") as f:
            json.dump(json_data, f)
        save_compressed(zstd_data, compressed_path)

        # Should load compressed
        loaded = load_auto(base_path)
        assert loaded == zstd_data

    def test_fallback_to_json(self, tmp_path: Path) -> None:
        """Test fallback to JSON when compressed doesn't exist."""
        base_path = tmp_path / "cache.json"
        json_data = {"source": "json"}

        with open(base_path, "w") as f:
            json.dump(json_data, f)

        loaded = load_auto(base_path)
        assert loaded == json_data

    def test_load_auto_not_found(self, tmp_path: Path) -> None:
        """Test that load_auto raises when neither file exists."""
        with pytest.raises(FileNotFoundError):
            load_auto(tmp_path / "nonexistent.json")


class TestMigration:
    """Tests for cache migration utilities."""

    def test_migrate_creates_compressed(self, tmp_path: Path) -> None:
        """Test that migration creates compressed file."""
        json_path = tmp_path / "cache.json"
        data = {"version": 1, "entries": []}

        with open(json_path, "w") as f:
            json.dump(data, f)

        compressed_path = migrate_to_compressed(json_path)

        assert compressed_path is not None
        assert compressed_path.exists()
        assert load_compressed(compressed_path) == data

    def test_migrate_removes_original(self, tmp_path: Path) -> None:
        """Test that migration removes original JSON by default."""
        json_path = tmp_path / "cache.json"
        with open(json_path, "w") as f:
            json.dump({}, f)

        migrate_to_compressed(json_path)

        assert not json_path.exists()

    def test_migrate_keeps_original(self, tmp_path: Path) -> None:
        """Test that migration can keep original JSON."""
        json_path = tmp_path / "cache.json"
        with open(json_path, "w") as f:
            json.dump({}, f)

        migrate_to_compressed(json_path, remove_original=False)

        assert json_path.exists()

    def test_migrate_nonexistent_returns_none(self, tmp_path: Path) -> None:
        """Test that migrating nonexistent file returns None."""
        result = migrate_to_compressed(tmp_path / "nonexistent.json")
        assert result is None

    def test_migrate_non_json_returns_none(self, tmp_path: Path) -> None:
        """Test that migrating non-.json file returns None."""
        txt_path = tmp_path / "cache.txt"
        txt_path.write_text("{}")

        result = migrate_to_compressed(txt_path)
        assert result is None


class TestCompressionLevel:
    """Tests for compression level constant."""

    def test_default_level_is_3(self) -> None:
        """Test that default compression level is 3."""
        assert COMPRESSION_LEVEL == 3

