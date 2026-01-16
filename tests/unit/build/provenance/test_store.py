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


# =============================================================================
# get_stored_hash Tests
# =============================================================================


class TestGetStoredHash:
    """Tests for get_stored_hash method (public API for hash lookup)."""

    def test_get_stored_hash_returns_none_for_missing(
        self, store: ProvenanceCache
    ) -> None:
        """get_stored_hash returns None for unstored page."""
        result = store.get_stored_hash(CacheKey("nonexistent.md"))
        assert result is None

    def test_get_stored_hash_returns_hash_for_stored(
        self, store: ProvenanceCache, sample_record: ProvenanceRecord
    ) -> None:
        """get_stored_hash returns combined hash for stored page."""
        store.store(sample_record)
        
        result = store.get_stored_hash(sample_record.page_path)
        
        assert result is not None
        assert result == sample_record.provenance.combined_hash


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestProvenanceCacheThreadSafety:
    """Tests for thread safety in ProvenanceCache."""

    def test_concurrent_store_operations(self, store: ProvenanceCache) -> None:
        """Concurrent store operations are thread-safe."""
        import threading
        
        errors: list[Exception] = []
        
        def store_record(idx: int) -> None:
            try:
                prov = Provenance().with_input(
                    "content",
                    CacheKey(f"content/page{idx}.md"),
                    ContentHash(f"hash{idx}"),
                )
                record = ProvenanceRecord(
                    page_path=CacheKey(f"content/page{idx}.md"),
                    provenance=prov,
                    output_hash=ContentHash(f"output{idx}"),
                )
                store.store(record)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=store_record, args=(i,))
            for i in range(20)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Thread errors: {errors}"
        
        # Verify all records stored
        for i in range(20):
            result = store.get(CacheKey(f"content/page{i}.md"))
            assert result is not None

    def test_concurrent_get_and_store(self, store: ProvenanceCache) -> None:
        """Concurrent get and store operations are thread-safe."""
        import threading
        import random
        
        # Pre-populate some records
        for i in range(10):
            prov = Provenance().with_input(
                "content",
                CacheKey(f"content/page{i}.md"),
                ContentHash(f"hash{i}"),
            )
            record = ProvenanceRecord(
                page_path=CacheKey(f"content/page{i}.md"),
                provenance=prov,
                output_hash=ContentHash(f"output{i}"),
            )
            store.store(record)
        
        errors: list[Exception] = []
        
        def reader_writer(idx: int) -> None:
            try:
                for _ in range(10):
                    # Random read
                    page_num = random.randint(0, 9)
                    store.get(CacheKey(f"content/page{page_num}.md"))
                    
                    # Random write (new pages)
                    new_page = f"content/new{idx}_{random.randint(0, 100)}.md"
                    prov = Provenance().with_input(
                        "content",
                        CacheKey(new_page),
                        ContentHash(f"newhash{idx}"),
                    )
                    record = ProvenanceRecord(
                        page_path=CacheKey(new_page),
                        provenance=prov,
                        output_hash=ContentHash(f"newoutput{idx}"),
                    )
                    store.store(record)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=reader_writer, args=(i,))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Thread errors: {errors}"

    def test_concurrent_is_fresh_checks(self, store: ProvenanceCache) -> None:
        """Concurrent is_fresh checks are thread-safe."""
        import threading
        
        # Store a record
        prov = Provenance().with_input(
            "content", CacheKey("content/test.md"), ContentHash("hash123")
        )
        record = ProvenanceRecord(
            page_path=CacheKey("content/test.md"),
            provenance=prov,
            output_hash=ContentHash("output"),
        )
        store.store(record)
        
        results: list[bool] = []
        errors: list[Exception] = []
        lock = threading.Lock()
        
        def check_fresh() -> None:
            try:
                is_fresh = store.is_fresh(record.page_path, prov)
                with lock:
                    results.append(is_fresh)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=check_fresh)
            for _ in range(20)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Thread errors: {errors}"
        assert all(r is True for r in results)

    def test_concurrent_subvenance_queries(self, store: ProvenanceCache) -> None:
        """Concurrent subvenance queries are thread-safe."""
        import threading
        
        # Create records that share a common input
        common_hash = ContentHash("shared_template")
        for i in range(10):
            prov = Provenance().with_input("template", CacheKey("base.html"), common_hash)
            record = ProvenanceRecord(
                page_path=CacheKey(f"content/page{i}.md"),
                provenance=prov,
                output_hash=ContentHash(f"output{i}"),
            )
            store.store(record)
        
        results: list[set[CacheKey]] = []
        errors: list[Exception] = []
        lock = threading.Lock()
        
        def query_affected() -> None:
            try:
                affected = store.get_affected_by(common_hash)
                with lock:
                    results.append(affected)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=query_affected)
            for _ in range(20)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Thread errors: {errors}"
        # All results should have 10 pages
        assert all(len(r) == 10 for r in results)

    def test_concurrent_store_batch(self, store: ProvenanceCache) -> None:
        """Concurrent store_batch operations are thread-safe."""
        import threading
        
        errors: list[Exception] = []
        
        def batch_store(batch_idx: int) -> None:
            try:
                records = []
                for i in range(5):
                    prov = Provenance().with_input(
                        "content",
                        CacheKey(f"batch{batch_idx}/page{i}.md"),
                        ContentHash(f"hash{batch_idx}_{i}"),
                    )
                    records.append(ProvenanceRecord(
                        page_path=CacheKey(f"batch{batch_idx}/page{i}.md"),
                        provenance=prov,
                        output_hash=ContentHash(f"output{batch_idx}_{i}"),
                    ))
                store.store_batch(records)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=batch_store, args=(i,))
            for i in range(10)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert not errors, f"Thread errors: {errors}"
        
        # Verify all batches stored
        for batch_idx in range(10):
            for i in range(5):
                result = store.get(CacheKey(f"batch{batch_idx}/page{i}.md"))
                assert result is not None
