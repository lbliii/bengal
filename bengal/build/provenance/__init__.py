"""
Provenance-based incremental build primitives.
"""

from __future__ import annotations

from bengal.build.provenance.filter import ProvenanceFilter, ProvenanceFilterResult
from bengal.build.provenance.store import ProvenanceCache
from bengal.build.provenance.types import (
    ContentHash,
    InputRecord,
    Provenance,
    ProvenanceRecord,
    hash_content,
    hash_dict,
    hash_file,
)

__all__ = [
    "ContentHash",
    "InputRecord",
    "Provenance",
    "ProvenanceRecord",
    "ProvenanceCache",
    "ProvenanceFilter",
    "ProvenanceFilterResult",
    "hash_content",
    "hash_dict",
    "hash_file",
]
