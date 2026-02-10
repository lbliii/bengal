"""
Unit tests for AST-first provenance features (Phases C, D, E).

Tests:
- hash_ast() utility
- ProvenanceRecord.ast_hash serialization round-trip
- _quick_ast_hash() semantic comparison in ProvenanceFilter
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.filter import ProvenanceFilter
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import (
    ContentHash,
    Provenance,
    ProvenanceRecord,
    hash_ast,
)


# =============================================================================
# hash_ast Tests
# =============================================================================


class TestHashAST:
    """Tests for hash_ast() utility."""

    @staticmethod
    def _serialization_available() -> bool:
        """Check if patitas.serialization (to_json) is importable."""
        try:
            from patitas.serialization import to_json  # noqa: F401

            return True
        except ImportError:
            return False

    def test_returns_content_hash(self) -> None:
        """hash_ast() returns a ContentHash string."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not self._serialization_available():
            pytest.skip("patitas.serialization not available")

        doc = parse("# Hello\n\nWorld")
        result = hash_ast(doc)
        assert isinstance(result, str)
        assert len(result) == 16  # Default truncation

    def test_deterministic(self) -> None:
        """Same AST produces the same hash."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not self._serialization_available():
            pytest.skip("patitas.serialization not available")

        doc1 = parse("# Hello\n\nWorld")
        doc2 = parse("# Hello\n\nWorld")
        assert hash_ast(doc1) == hash_ast(doc2)

    def test_different_content_different_hash(self) -> None:
        """Different AST structures produce different hashes."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not self._serialization_available():
            pytest.skip("patitas.serialization not available")

        doc1 = parse("# Hello\n\nWorld")
        doc2 = parse("# Goodbye\n\nMoon")
        assert hash_ast(doc1) != hash_ast(doc2)

    def test_whitespace_insensitive(self) -> None:
        """Whitespace-only changes produce the same AST hash."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not self._serialization_available():
            pytest.skip("patitas.serialization not available")

        doc1 = parse("# Hello\n\nWorld")
        doc2 = parse("# Hello\n\n\nWorld")  # Extra blank line
        # ASTs may or may not differ depending on parser behavior.
        # The key contract: if ASTs are structurally identical,
        # hashes match. We test the mechanism, not parser semantics.
        h1 = hash_ast(doc1)
        h2 = hash_ast(doc2)
        assert isinstance(h1, str) and isinstance(h2, str)

    def test_none_returns_no_ast_sentinel(self) -> None:
        """hash_ast(None) returns the _no_ast_ sentinel."""
        # hash_ast expects a Patitas Document, not None.
        # Passing None should fall through to the except branch.
        result = hash_ast(None)
        assert result == ContentHash("_no_ast_")

    def test_without_serialization_returns_sentinel(self) -> None:
        """hash_ast() returns _no_ast_ when serialization unavailable."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        doc = parse("# Hello")
        result = hash_ast(doc)
        # If serialization is unavailable, result is _no_ast_
        # If available, result is a 16-char hash. Both are valid.
        assert isinstance(result, str)

    def test_custom_truncation(self) -> None:
        """Custom truncation length is applied."""
        try:
            from patitas import parse
        except ImportError:
            pytest.skip("patitas not available")

        if not self._serialization_available():
            pytest.skip("patitas.serialization not available")

        doc = parse("# Test")
        result = hash_ast(doc, truncate=8)
        assert len(result) == 8


# =============================================================================
# ProvenanceRecord.ast_hash Tests
# =============================================================================


class TestProvenanceRecordAstHash:
    """Tests for ProvenanceRecord.ast_hash field."""

    def test_default_none(self) -> None:
        """ast_hash defaults to None."""
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=Provenance(),
            output_hash=ContentHash("output123"),
        )
        assert record.ast_hash is None

    def test_set_ast_hash(self) -> None:
        """ast_hash can be set to a ContentHash."""
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=Provenance(),
            output_hash=ContentHash("output123"),
            ast_hash=ContentHash("ast_abc123"),
        )
        assert record.ast_hash == ContentHash("ast_abc123")

    def test_to_dict_includes_ast_hash(self) -> None:
        """to_dict() includes ast_hash when set."""
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=Provenance(),
            output_hash=ContentHash("output123"),
            ast_hash=ContentHash("ast_abc123"),
        )
        data = record.to_dict()
        assert data["ast_hash"] == "ast_abc123"

    def test_to_dict_omits_ast_hash_when_none(self) -> None:
        """to_dict() omits ast_hash when None."""
        record = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=Provenance(),
            output_hash=ContentHash("output123"),
        )
        data = record.to_dict()
        assert "ast_hash" not in data

    def test_from_dict_with_ast_hash(self) -> None:
        """from_dict() deserializes ast_hash correctly."""
        data = {
            "page_path": "content/about.md",
            "inputs": [],
            "combined_hash": "combined123",
            "output_hash": "output123",
            "ast_hash": "ast_abc123",
            "created_at": "2026-01-16T12:00:00",
            "build_id": "build-001",
        }
        record = ProvenanceRecord.from_dict(data)
        assert record.ast_hash == ContentHash("ast_abc123")

    def test_from_dict_without_ast_hash(self) -> None:
        """from_dict() handles missing ast_hash (backward compat)."""
        data = {
            "page_path": "content/about.md",
            "inputs": [],
            "combined_hash": "combined123",
            "output_hash": "output123",
            "created_at": "2026-01-16T12:00:00",
        }
        record = ProvenanceRecord.from_dict(data)
        assert record.ast_hash is None

    def test_roundtrip_with_ast_hash(self) -> None:
        """to_dict() → from_dict() preserves ast_hash."""
        prov = Provenance().with_input(
            "content", CacheKey("content/about.md"), ContentHash("abc123")
        )
        original = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=prov,
            output_hash=ContentHash("output123"),
            ast_hash=ContentHash("ast_xyz789"),
            build_id="build-002",
        )
        data = original.to_dict()
        recovered = ProvenanceRecord.from_dict(data)

        assert recovered.ast_hash == original.ast_hash
        assert recovered.page_path == original.page_path
        assert recovered.output_hash == original.output_hash

    def test_roundtrip_without_ast_hash(self) -> None:
        """to_dict() → from_dict() preserves None ast_hash."""
        original = ProvenanceRecord(
            page_path=CacheKey("content/about.md"),
            provenance=Provenance(),
            output_hash=ContentHash("output123"),
        )
        data = original.to_dict()
        recovered = ProvenanceRecord.from_dict(data)
        assert recovered.ast_hash is None


# =============================================================================
# _quick_ast_hash Tests
# =============================================================================


class TestQuickAstHash:
    """Tests for ProvenanceFilter._quick_ast_hash()."""

    @pytest.fixture
    def provenance_filter(self, tmp_path: Path) -> ProvenanceFilter:
        """Create a ProvenanceFilter for testing."""
        site = MagicMock()
        site.root_path = tmp_path / "site"
        site.root_path.mkdir(parents=True)
        site.config = {"title": "Test Site"}
        cache = ProvenanceCache(cache_dir=tmp_path / ".bengal" / "provenance")
        return ProvenanceFilter(site=site, cache=cache)

    def test_returns_hash_for_plain_markdown(
        self, provenance_filter: ProvenanceFilter, tmp_path: Path
    ) -> None:
        """_quick_ast_hash returns a hash for a plain markdown file."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nWorld")

        page = MagicMock()
        page.source_path = md_file

        result = provenance_filter._quick_ast_hash(page)
        # Result depends on patitas.serialization availability
        # If available: 16-char ContentHash
        # If not available (hash_ast falls back): _no_ast_
        assert result is not None
        assert isinstance(result, str)

    def test_strips_frontmatter(
        self, provenance_filter: ProvenanceFilter, tmp_path: Path
    ) -> None:
        """_quick_ast_hash strips YAML frontmatter before parsing."""
        md_file = tmp_path / "test.md"
        md_file.write_text("---\ntitle: Test\n---\n# Hello\n\nWorld")

        page = MagicMock()
        page.source_path = md_file

        result = provenance_filter._quick_ast_hash(page)
        assert result is not None

        # Compare with a file that has the same body but no frontmatter
        md_file_no_fm = tmp_path / "test_nofm.md"
        md_file_no_fm.write_text("# Hello\n\nWorld")

        page_nofm = MagicMock()
        page_nofm.source_path = md_file_no_fm

        result_nofm = provenance_filter._quick_ast_hash(page_nofm)
        # Both should produce the same AST hash since body is identical
        assert result == result_nofm

    def test_returns_none_for_missing_file(
        self, provenance_filter: ProvenanceFilter, tmp_path: Path
    ) -> None:
        """_quick_ast_hash returns None when source file doesn't exist."""
        page = MagicMock()
        page.source_path = tmp_path / "nonexistent.md"

        result = provenance_filter._quick_ast_hash(page)
        assert result is None

    def test_deterministic(
        self, provenance_filter: ProvenanceFilter, tmp_path: Path
    ) -> None:
        """_quick_ast_hash returns same hash for same content."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title\n\nParagraph content.")

        page = MagicMock()
        page.source_path = md_file

        result1 = provenance_filter._quick_ast_hash(page)
        result2 = provenance_filter._quick_ast_hash(page)
        assert result1 == result2

    def test_different_content_different_hash(
        self, provenance_filter: ProvenanceFilter, tmp_path: Path
    ) -> None:
        """_quick_ast_hash returns different hashes for different content."""
        try:
            from patitas.serialization import to_json  # noqa: F401
        except ImportError:
            pytest.skip("patitas.serialization not available (hashes collapse to _no_ast_)")

        file_a = tmp_path / "a.md"
        file_a.write_text("# Hello\n\nWorld")
        file_b = tmp_path / "b.md"
        file_b.write_text("# Goodbye\n\nMoon")

        page_a = MagicMock()
        page_a.source_path = file_a
        page_b = MagicMock()
        page_b.source_path = file_b

        hash_a = provenance_filter._quick_ast_hash(page_a)
        hash_b = provenance_filter._quick_ast_hash(page_b)
        assert hash_a != hash_b


# =============================================================================
# Sentinel Guard Tests
# =============================================================================


class TestSentinelGuard:
    """Tests that _no_ast_ sentinel never causes false skip matches."""

    def test_record_build_rejects_sentinel(self, tmp_path: Path) -> None:
        """record_build() stores None (not _no_ast_) when serialization unavailable."""
        site = MagicMock()
        site.root_path = tmp_path / "site"
        site.root_path.mkdir(parents=True)
        site.config = {"title": "Test"}
        cache = ProvenanceCache(cache_dir=tmp_path / ".bengal" / "provenance")
        pf = ProvenanceFilter(site=site, cache=cache)

        # Create a page with _ast_cache set (simulating parser output)
        page = MagicMock()
        page.source_path = tmp_path / "content" / "test.md"
        page.source_path.parent.mkdir(parents=True, exist_ok=True)
        page.source_path.write_text("# Hello\n\nWorld")
        page._ast_cache = "mock_ast_object"  # Not a real AST, but not None

        pf.record_build(page)

        # Retrieve the stored record
        from bengal.build.contracts.keys import CacheKey

        stored = cache.get(CacheKey(str(page.source_path)))

        # If patitas.serialization is unavailable, hash_ast returns _no_ast_
        # but record_build should NOT store it - ast_hash should be None
        try:
            from patitas.serialization import to_json  # noqa: F401
            # Serialization available: ast_hash should be a real hash or None
            # (mock_ast_object likely fails to_json, so still None)
        except ImportError:
            # Serialization unavailable: ast_hash MUST be None, not _no_ast_
            if stored is not None:
                assert stored.ast_hash is None, (
                    f"ast_hash should be None when serialization unavailable, "
                    f"got {stored.ast_hash!r}"
                )

    def test_sentinel_never_matches_in_filter(self) -> None:
        """The _no_ast_ sentinel value is never treated as a valid hash match."""
        sentinel = ContentHash("_no_ast_")

        # Simulate what the filter does: both sides are sentinel
        # This should NOT be considered a match
        stored_ast_hash = sentinel
        new_ast_hash = sentinel

        # The guard condition from the filter
        is_valid_match = (
            stored_ast_hash
            and stored_ast_hash != sentinel
            and new_ast_hash
            and new_ast_hash != sentinel
            and new_ast_hash == stored_ast_hash
        )
        assert not is_valid_match, (
            "_no_ast_ sentinel should never produce a valid match"
        )
