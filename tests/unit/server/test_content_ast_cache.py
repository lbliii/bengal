"""
Unit tests for ContentASTCache (bengal.server.fragment_update).

Tests save_to_disk/load_from_disk round-trip, get_by_hash,
and the _index.json generation for cache reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from bengal.server.fragment_update import ContentASTCache


@dataclass(frozen=True, slots=True)
class _FakeDocument:
    children: tuple[object, ...] = ()
    location: object | None = None


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    """Clear ContentASTCache before each test."""
    ContentASTCache.clear()


class TestContentASTCacheBasics:
    """Tests for ContentASTCache get/put/get_by_hash."""

    def test_put_and_get(self) -> None:
        """put() stores entry, get() retrieves it."""
        path = Path("/content/test.md")
        fake_doc = _FakeDocument()
        ContentASTCache.put(path, "hash123", "# Hello", fake_doc)

        result = ContentASTCache.get(path)
        assert result is not None
        body, ast = result
        assert body == "# Hello"
        assert ast == fake_doc

    def test_get_missing_returns_none(self) -> None:
        """get() returns None for missing path."""
        assert ContentASTCache.get(Path("/missing.md")) is None

    def test_get_by_hash_matching(self) -> None:
        """get_by_hash() returns AST when content hash matches."""
        path = Path("/content/test.md")
        fake_doc = _FakeDocument()
        ContentASTCache.put(path, "hash123", "# Hello", fake_doc)

        result = ContentASTCache.get_by_hash(path, "hash123")
        assert result == fake_doc

    def test_get_by_hash_mismatch(self) -> None:
        """get_by_hash() returns None when content hash differs."""
        path = Path("/content/test.md")
        ContentASTCache.put(path, "hash123", "# Hello", _FakeDocument())

        result = ContentASTCache.get_by_hash(path, "different_hash")
        assert result is None

    def test_get_by_hash_missing_path(self) -> None:
        """get_by_hash() returns None for missing path."""
        result = ContentASTCache.get_by_hash(Path("/missing.md"), "hash123")
        assert result is None

    def test_clear(self) -> None:
        """clear() removes all entries."""
        ContentASTCache.put(Path("/a.md"), "h1", "a", _FakeDocument())
        ContentASTCache.put(Path("/b.md"), "h2", "b", _FakeDocument())
        ContentASTCache.clear()

        assert ContentASTCache.stats()["entries"] == 0

    def test_stats(self) -> None:
        """stats() reports correct entry count."""
        ContentASTCache.put(Path("/a.md"), "h1", "a", _FakeDocument())
        ContentASTCache.put(Path("/b.md"), "h2", "b", _FakeDocument())

        stats = ContentASTCache.stats()
        assert stats["entries"] == 2

    def test_put_rejects_legacy_tuple_ast(self) -> None:
        """put() ignores legacy tuple ASTs to avoid cache contamination."""
        path = Path("/content/legacy.md")
        ContentASTCache.put(path, "legacy_hash", "# Legacy", ("heading", "text"))

        assert ContentASTCache.get(path) is None


def _serialization_available() -> bool:
    """Check if patitas.serialization (to_json/from_json) is importable."""
    try:
        from patitas.serialization import from_json, to_json  # noqa: F401

        return True
    except ImportError:
        return False


class TestContentASTCacheDiskPersistence:
    """Tests for save_to_disk/load_from_disk round-trip."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """save_to_disk() + load_from_disk() restores cached ASTs."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not _serialization_available():
            pytest.skip("patitas.serialization not available")

        # Populate cache with real Patitas Documents
        doc1 = parse("# Hello\n\nWorld")
        doc2 = parse("## Section\n\nContent here")
        path1 = Path("/content/page1.md")
        path2 = Path("/content/page2.md")

        ContentASTCache.put(path1, "hash_a", "# Hello\n\nWorld", doc1)
        ContentASTCache.put(path2, "hash_b", "## Section\n\nContent here", doc2)

        # Save to disk
        cache_dir = tmp_path / "ast_cache"
        saved = ContentASTCache.save_to_disk(cache_dir)
        assert saved == 2

        # Verify _index.json was created
        index_path = cache_dir / "_index.json"
        assert index_path.exists()

        # Clear and reload
        ContentASTCache.clear()
        assert ContentASTCache.stats()["entries"] == 0

        loaded = ContentASTCache.load_from_disk(cache_dir)
        assert loaded == 2
        assert ContentASTCache.stats()["entries"] == 2

        # Verify ASTs are accessible by hash
        ast1 = ContentASTCache.get_by_hash(path1, "hash_a")
        assert ast1 is not None

        ast2 = ContentASTCache.get_by_hash(path2, "hash_b")
        assert ast2 is not None

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """save_to_disk() creates cache directory if missing."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not _serialization_available():
            pytest.skip("patitas.serialization not available")

        doc = parse("# Test")
        ContentASTCache.put(Path("/test.md"), "h1", "# Test", doc)

        cache_dir = tmp_path / "nested" / "ast_cache"
        assert not cache_dir.exists()

        ContentASTCache.save_to_disk(cache_dir)
        assert cache_dir.exists()

    def test_load_missing_directory_returns_zero(self, tmp_path: Path) -> None:
        """load_from_disk() returns 0 for missing directory."""
        loaded = ContentASTCache.load_from_disk(tmp_path / "nonexistent")
        assert loaded == 0

    def test_load_missing_index_returns_zero(self, tmp_path: Path) -> None:
        """load_from_disk() returns 0 when _index.json is missing."""
        cache_dir = tmp_path / "ast_cache"
        cache_dir.mkdir()
        loaded = ContentASTCache.load_from_disk(cache_dir)
        assert loaded == 0

    def test_save_empty_cache(self, tmp_path: Path) -> None:
        """save_to_disk() handles empty cache gracefully."""
        cache_dir = tmp_path / "ast_cache"
        saved = ContentASTCache.save_to_disk(cache_dir)
        assert saved == 0

    def test_save_without_serialization_returns_zero(self, tmp_path: Path) -> None:
        """save_to_disk() returns 0 when patitas.serialization is unavailable."""
        if _serialization_available():
            pytest.skip("patitas.serialization is available (test is for when it's not)")

        ContentASTCache.put(Path("/test.md"), "h1", "# Test", _FakeDocument())
        cache_dir = tmp_path / "ast_cache"
        saved = ContentASTCache.save_to_disk(cache_dir)
        assert saved == 0

    def test_index_maps_paths_to_hashes(self, tmp_path: Path) -> None:
        """_index.json maps source paths to content hashes."""
        try:
            import json

            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not _serialization_available():
            pytest.skip("patitas.serialization not available")

        doc = parse("# Hello")
        path = Path("/content/page.md")
        ContentASTCache.put(path, "content_hash_abc", "# Hello", doc)

        cache_dir = tmp_path / "ast_cache"
        ContentASTCache.save_to_disk(cache_dir)

        index_path = cache_dir / "_index.json"
        index = json.loads(index_path.read_text())
        assert str(path) in index
        assert index[str(path)] == "content_hash_abc"
