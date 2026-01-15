"""
Provenance-Based Incremental Build Prototype.

Experimental implementation of Pachyderm-style provenance tracking
for Bengal's incremental builds.

This prototype demonstrates:
1. Content-addressed hashing of all inputs
2. Automatic provenance capture during rendering
3. Subvenance queries (what depends on X?)
4. Cache validation via input hash comparison

Usage:
    from bengal.experimental.provenance import ProvenanceTracker, ProvenanceStore
    
    store = ProvenanceStore(cache_dir)
    
    # Check if page needs rebuild
    record = store.get(page_path)
    if record and store.is_fresh(page_path, current_provenance):
        print("Cache hit!")
    else:
        # Render and track provenance
        with ProvenanceTracker(page_path) as tracker:
            html = render_page(page)
            # Provenance automatically captured
            print(f"Inputs: {tracker.provenance}")

CLI Commands:
    bengal provenance lineage content/about.md   # What inputs produced this page?
    bengal provenance affected templates/base.html  # What pages depend on this file?
    bengal provenance stats                       # Show provenance cache stats
    bengal provenance build --compare            # Compare with current system
"""

from bengal.experimental.provenance.core_types import (
    ContentHash,
    InputRecord,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)
from bengal.experimental.provenance.store import ProvenanceStore
from bengal.experimental.provenance.tracker import ProvenanceTracker

__all__ = [
    "ContentHash",
    "InputRecord",
    "Provenance",
    "ProvenanceRecord",
    "ProvenanceStore",
    "ProvenanceTracker",
    "hash_content",
    "hash_dict",
    "hash_file",
]
