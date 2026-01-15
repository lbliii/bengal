"""
Provenance store with content-addressed caching.

Stores provenance records and provides:
1. Cache validation (is this page fresh?)
2. Subvenance queries (what depends on this input?)
3. Garbage collection (remove stale entries)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bengal.build.contracts.keys import CacheKey
from bengal.build.provenance.types import (
    ContentHash,
    InputRecord,
    Provenance,
    ProvenanceRecord,
    hash_content,
)


@dataclass
class ProvenanceCache:
    """
    Content-addressed provenance store.
    
    Storage format:
        .bengal/provenance/
        ├── index.json       # page_path → combined_hash mapping
        ├── records/         # Individual provenance records by hash
        │   ├── a1b2c3d4.json
        │   └── ...
        └── subvenance.json  # Reverse index: input_hash → [page_paths]
    
    The subvenance index enables O(1) "what depends on X?" queries.
    """
    
    cache_dir: Path
    
    # In-memory indexes (loaded lazily)
    _index: dict[CacheKey, ContentHash] = field(default_factory=dict)
    _records: dict[ContentHash, ProvenanceRecord] = field(default_factory=dict)
    _subvenance: dict[ContentHash, set[CacheKey]] = field(default_factory=dict)
    _loaded: bool = False
    _dirty: bool = False
    
    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self._records_dir = self.cache_dir / "records"
    
    def _ensure_loaded(self) -> None:
        """Load indexes from disk if not already loaded."""
        if self._loaded:
            return
        
        self._load_index()
        self._load_subvenance()
        self._loaded = True
    
    def _load_index(self) -> None:
        """Load page → hash index."""
        index_path = self.cache_dir / "index.json"
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text())
                self._index = {
                    CacheKey(k): ContentHash(v)
                    for k, v in data.get("pages", {}).items()
                }
            except (json.JSONDecodeError, KeyError):
                self._index = {}
    
    def _load_subvenance(self) -> None:
        """Load reverse index (input → pages)."""
        subvenance_path = self.cache_dir / "subvenance.json"
        if subvenance_path.exists():
            try:
                data = json.loads(subvenance_path.read_text())
                self._subvenance = {
                    ContentHash(k): set(v) for k, v in data.items()
                }
            except (json.JSONDecodeError, KeyError):
                self._subvenance = {}
    
    def _get_record(self, combined_hash: ContentHash) -> ProvenanceRecord | None:
        """Load a provenance record by hash."""
        # Check memory cache first
        if combined_hash in self._records:
            return self._records[combined_hash]
        
        # Load from disk
        record_path = self._records_dir / f"{combined_hash}.json"
        if record_path.exists():
            try:
                data = json.loads(record_path.read_text())
                record = ProvenanceRecord.from_dict(data)
                self._records[combined_hash] = record
                return record
            except (json.JSONDecodeError, KeyError):
                return None
        
        return None
    
    def get(self, page_path: CacheKey) -> ProvenanceRecord | None:
        """Get provenance record for a page."""
        self._ensure_loaded()
        
        combined_hash = self._index.get(page_path)
        if combined_hash is None:
            return None
        
        return self._get_record(combined_hash)
    
    def is_fresh(self, page_path: CacheKey, current_provenance: Provenance) -> bool:
        """
        Check if cached output is still valid.
        
        Returns True if ALL inputs match (cache hit).
        Returns False if ANY input differs (cache miss).
        """
        self._ensure_loaded()
        
        # Get stored hash
        stored_hash = self._index.get(page_path)
        if stored_hash is None:
            return False  # Never built before
        
        # Compare with current inputs hash
        return stored_hash == current_provenance.combined_hash
    
    def store(self, record: ProvenanceRecord) -> None:
        """Store a provenance record."""
        self._ensure_loaded()
        
        # Update page → hash index
        self._index[record.page_path] = record.provenance.combined_hash
        
        # Store record in memory
        self._records[record.provenance.combined_hash] = record
        
        # Update subvenance index
        for inp in record.provenance.inputs:
            if inp.hash not in self._subvenance:
                self._subvenance[inp.hash] = set()
            self._subvenance[inp.hash].add(record.page_path)
        
        # Write record to disk
        self._records_dir.mkdir(parents=True, exist_ok=True)
        record_path = self._records_dir / f"{record.provenance.combined_hash}.json"
        record_path.write_text(json.dumps(record.to_dict(), indent=2))
        
        self._dirty = True
    
    def get_affected_by(self, input_hash: ContentHash) -> set[CacheKey]:
        """
        Subvenance query: What pages depend on this input?
        
        This is the inverse of provenance:
        - Provenance: page → what inputs produced it
        - Subvenance: input → what pages depend on it
        
        Returns set of page paths.
        """
        self._ensure_loaded()
        return self._subvenance.get(input_hash, set()).copy()
    
    def get_affected_by_path(self, input_path: CacheKey, site_root: Path) -> set[CacheKey]:
        """
        Subvenance query by path (computes current hash).
        
        Use this when you know a file changed and want to find
        all pages that need rebuilding.
        """
        from bengal.build.provenance.types import hash_file
        
        full_path = site_root / input_path
        current_hash = hash_file(full_path)
        
        return self.get_affected_by(current_hash)
    
    def save(self) -> None:
        """Persist indexes to disk."""
        if not self._dirty:
            return
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save page index
        index_path = self.cache_dir / "index.json"
        index_path.write_text(json.dumps({
            "version": 1,
            "pages": dict(self._index),
        }, indent=2))
        
        # Save subvenance index
        subvenance_path = self.cache_dir / "subvenance.json"
        subvenance_path.write_text(json.dumps({
            k: sorted(v) for k, v in self._subvenance.items()
        }, indent=2))
        
        self._dirty = False
    
    def stats(self) -> dict[str, Any]:
        """Get store statistics."""
        self._ensure_loaded()
        
        total_inputs = sum(
            len(self._get_record(h).provenance.inputs) if self._get_record(h) else 0
            for h in self._index.values()
        )
        
        return {
            "pages_tracked": len(self._index),
            "records_cached": len(self._records),
            "subvenance_entries": len(self._subvenance),
            "total_input_references": total_inputs,
        }
    
    def gc(self, valid_pages: set[CacheKey]) -> int:
        """
        Garbage collect stale entries.
        
        Removes records for pages that no longer exist.
        Returns number of entries removed.
        """
        self._ensure_loaded()
        
        stale = set(self._index.keys()) - valid_pages
        removed = 0
        
        for page_path in stale:
            combined_hash = self._index.pop(page_path, None)
            if combined_hash:
                # Remove record file
                record_path = self._records_dir / f"{combined_hash}.json"
                if record_path.exists():
                    record_path.unlink()
                
                # Clean up memory
                self._records.pop(combined_hash, None)
                removed += 1
        
        # Clean up subvenance
        for input_hash in list(self._subvenance.keys()):
            self._subvenance[input_hash] -= stale
            if not self._subvenance[input_hash]:
                del self._subvenance[input_hash]
        
        if removed:
            self._dirty = True
        
        return removed
