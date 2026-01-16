"""
Unit tests for bengal.build.provenance.store.

Tests ProvenanceCache for provenance storage and retrieval.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import (
    ContentHash,
    InputRecord,
    Provenance,
    ProvenanceRecord,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create temp cache directory."""
    return tmp_path / ".bengal" / "provenance"


@pytest.fixture
def store(cache_dir: Path) -> ProvenanceCache:
    """Create ProvenanceCache instance."""
    return ProvenanceCache(cache_dir=cache_dir)


@pytest.fixture
def sample_record() -> ProvenanceRecord:
    """Create sample ProvenanceRecord."""
    prov = Provenance().with_input(
        "content", CacheKey("content/about.md"), ContentHash("abc123")
    )
    return ProvenanceRecord(
        page_path=CacheKey("content/about.md"),
        provenance=prov,
        output_hash=ContentHash("output123"),
    )


# =============================================================================
# Basic Store/Get Tests
# =============================================================================


class TestProvenanceCacheBasics:
    """Basic tests for ProvenanceCache."""

    def test_get_missing_returns_none(self, store: ProvenanceCache) -> None:
        """Getting missing page returns None."""
        result = store.get(CacheKey("nonexistent.md"))
        assert result is None

    def test_store_and_get(
        self, store: ProvenanceCache, sample_record: ProvenanceRecord
    ) -> None:
        """Stored record can be retrieved."""
        store.store(sample_record)
        
        result = store.get(sample_record.page_path)
        
        assert result is not None
        assert result.page_path == sample_record.page_path
        assert result.output_hash == sample_record.output_hash

    def test_store_creates_directory(
        self, store: ProvenanceCache, cache_dir: Path, sample_record: ProvenanceRecord
    ) -> None:
        """Store creates cache directory if missing."""
        assert not cache_dir.exists()
        
        store.store(sample_record)
        
        # Records directory should exist
        records_dir = cache_dir / "records"
        assert records_dir.exists()


# =============================================================================
# is_fresh Tests
# =============================================================================


class TestIsFresh:
    """Tests for is_fresh method."""

    def test_fresh_when_hash_matches(
        self, store: ProvenanceCache, sample_record: ProvenanceRecord
    ) -> None:
        """is_fresh returns True when combined hash matches."""
        store.store(sample_record)
        
        # Same provenance (same combined hash)
        current_prov = sample_record.provenance
        
        result = store.is_fresh(sample_record.page_path, current_prov)
        
        assert result is True

    def test_stale_when_hash_differs(
        self, store: ProvenanceCache, sample_record: ProvenanceRecord
    ) -> None:
        """is_fresh returns False when combined hash differs."""
        store.store(sample_record)
        
        # Different provenance (different combined hash)
        new_prov = Provenance().with_input(
            "content", CacheKey("content/about.md"), ContentHash("different123")
        )
        
        result = store.is_fresh(sample_record.page_path, new_prov)
        
        assert result is False

    def test_stale_when_not_stored(self, store: ProvenanceCache) -> None:
        """is_fresh returns False for unstored page."""
        prov = Provenance()
        
        result = store.is_fresh(CacheKey("unknown.md"), prov)
        
        assert result is False


# =============================================================================
# Batch Store Tests
# =============================================================================


class TestBatchStore:
    """Tests for store_batch method."""

    def test_store_batch_empty(self, store: ProvenanceCache) -> None:
        """Empty batch does nothing."""
        store.store_batch([])
        # Should not raise

    def test_store_batch_multiple(self, store: ProvenanceCache) -> None:
        """Multiple records can be stored in batch."""
        records = []
        for i in range(3):
            prov = Provenance().with_input(
                "content", CacheKey(f"content/page{i}.md"), ContentHash(f"hash{i}")
            )
            records.append(ProvenanceRecord(
                page_path=CacheKey(f"content/page{i}.md"),
                provenance=prov,
                output_hash=ContentHash(f"output{i}"),
            ))
        
        store.store_batch(records)
        
        for i in range(3):
            result = store.get(CacheKey(f"content/page{i}.md"))
            assert result is not None


# =============================================================================
# Subvenance Query Tests
# =============================================================================


class TestSubvenanceQueries:
    """Tests for subvenance (reverse) queries."""

    def test_get_affected_by_hash(self, store: ProvenanceCache) -> None:
        """get_affected_by returns pages using input hash."""
        # Create records that share a common input
        common_input = InputRecord("template", CacheKey("base.html"), ContentHash("template123"))
        
        for page in ["page1.md", "page2.md"]:
            prov = Provenance(inputs=frozenset([common_input]))
            record = ProvenanceRecord(
                page_path=CacheKey(f"content/{page}"),
                provenance=prov,
                output_hash=ContentHash("output"),
            )
            store.store(record)
        
        # Query by template hash
        affected = store.get_affected_by(ContentHash("template123"))
        
        assert CacheKey("content/page1.md") in affected
        assert CacheKey("content/page2.md") in affected

    def test_get_affected_by_unknown_hash(self, store: ProvenanceCache) -> None:
        """get_affected_by returns empty set for unknown hash."""
        result = store.get_affected_by(ContentHash("unknown"))
        assert result == set()


# =============================================================================
# Save/Load Tests
# =============================================================================


class TestSaveLoad:
    """Tests for save and reload functionality."""

    def test_save_persists_index(
        self, store: ProvenanceCache, cache_dir: Path, sample_record: ProvenanceRecord
    ) -> None:
        """save() persists index to disk."""
        store.store(sample_record)
        store.save()
        
        # Check index file exists
        index_path = cache_dir / "index.json"
        assert index_path.exists()

    def test_save_persists_subvenance(
        self, store: ProvenanceCache, cache_dir: Path, sample_record: ProvenanceRecord
    ) -> None:
        """save() persists subvenance index to disk."""
        store.store(sample_record)
        store.save()
        
        # Check subvenance file exists
        subvenance_path = cache_dir / "subvenance.json"
        assert subvenance_path.exists()

    def test_reload_restores_state(
        self, cache_dir: Path, sample_record: ProvenanceRecord
    ) -> None:
        """New store instance loads persisted state."""
        # Store and save
        store1 = ProvenanceCache(cache_dir=cache_dir)
        store1.store(sample_record)
        store1.save()
        
        # Create new store and verify it loads state
        store2 = ProvenanceCache(cache_dir=cache_dir)
        result = store2.get(sample_record.page_path)
        
        assert result is not None
        assert result.page_path == sample_record.page_path

    def test_no_save_when_not_dirty(
        self, store: ProvenanceCache, cache_dir: Path
    ) -> None:
        """save() does nothing when not dirty."""
        store.save()  # Nothing stored
        
        # Index file should not exist
        index_path = cache_dir / "index.json"
        assert not index_path.exists()


# =============================================================================
# Stats Tests
# =============================================================================


class TestStats:
    """Tests for stats method."""

    def test_stats_empty_store(self, store: ProvenanceCache) -> None:
        """stats() returns zeros for empty store."""
        stats = store.stats()
        
        assert stats["pages_tracked"] == 0
        assert stats["records_cached"] == 0
        assert stats["subvenance_entries"] == 0

    def test_stats_with_records(
        self, store: ProvenanceCache, sample_record: ProvenanceRecord
    ) -> None:
        """stats() returns correct counts."""
        store.store(sample_record)
        
        stats = store.stats()
        
        assert stats["pages_tracked"] == 1


# =============================================================================
# Garbage Collection Tests
# =============================================================================


class TestGarbageCollection:
    """Tests for garbage collection."""

    def test_gc_removes_stale_entries(self, store: ProvenanceCache) -> None:
        """gc() removes entries for nonexistent pages."""
        # Store some records
        for page in ["keep.md", "remove.md"]:
            prov = Provenance().with_input(
                "content", CacheKey(f"content/{page}"), ContentHash("hash")
            )
            record = ProvenanceRecord(
                page_path=CacheKey(f"content/{page}"),
                provenance=prov,
                output_hash=ContentHash("output"),
            )
            store.store(record)
        
        # GC with only "keep.md" as valid
        valid_pages = {CacheKey("content/keep.md")}
        removed = store.gc(valid_pages)
        
        assert removed == 1
        assert store.get(CacheKey("content/keep.md")) is not None
        assert store.get(CacheKey("content/remove.md")) is None

    def test_gc_returns_zero_when_nothing_to_remove(
        self, store: ProvenanceCache, sample_record: ProvenanceRecord
    ) -> None:
        """gc() returns 0 when all pages are valid."""
        store.store(sample_record)
        
        valid_pages = {sample_record.page_path}
        removed = store.gc(valid_pages)
        
        assert removed == 0
