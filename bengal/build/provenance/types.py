"""
Provenance types for content-addressed incremental builds.

Core types:
- ContentHash: SHA256 hash truncated to 16 chars
- Provenance: Record of what inputs produced an output
- ProvenanceRecord: Stored provenance with metadata
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, NewType

from bengal.build.contracts.keys import CacheKey

# Type-safe content hash (prevents mixing with regular strings)
ContentHash = NewType("ContentHash", str)


def hash_content(content: str | bytes, truncate: int = 16) -> ContentHash:
    """Compute content hash (SHA256, truncated)."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    full_hash = hashlib.sha256(content).hexdigest()
    return ContentHash(full_hash[:truncate])


def hash_file(path: Path, truncate: int = 16) -> ContentHash:
    """Compute file content hash."""
    try:
        content = path.read_bytes()
        return hash_content(content, truncate)
    except (OSError, IOError):
        # File doesn't exist or can't be read
        return ContentHash("_missing_")


def hash_dict(data: dict[str, Any], truncate: int = 16) -> ContentHash:
    """Compute hash of dictionary (for config, metadata)."""
    import json
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hash_content(serialized, truncate)


@dataclass(frozen=True, slots=True)
class InputRecord:
    """Single input that contributed to an output."""

    input_type: str  # "content", "template", "data", "config", "partial"
    path: CacheKey   # Relative path or config key
    hash: ContentHash

    def __str__(self) -> str:
        return f"{self.input_type}:{self.path}={self.hash}"


@dataclass(frozen=True, slots=True)
class Provenance:
    """
    Complete provenance for a rendered page.

    Captures ALL inputs that influenced the output:
    - Source content file
    - Templates (full chain: base → child → ...)
    - Data files accessed
    - Partials included
    - Config values used

    The combined_hash is computed from all inputs.
    If combined_hash matches on next build → cache hit.
    """

    # All inputs that produced this output
    inputs: frozenset[InputRecord] = field(default_factory=frozenset)

    # Computed hash of all inputs (for cache lookup)
    combined_hash: ContentHash = field(default=ContentHash(""))

    def __post_init__(self) -> None:
        """Compute combined hash if not provided."""
        if not self.combined_hash and self.inputs:
            # Sort for deterministic hash
            parts = sorted(str(inp) for inp in self.inputs)
            combined = hash_content("\n".join(parts))
            # Frozen dataclass workaround
            object.__setattr__(self, "combined_hash", combined)

    def with_input(
        self,
        input_type: str,
        path: CacheKey,
        content_hash: ContentHash,
    ) -> Provenance:
        """Add an input (returns new Provenance)."""
        new_input = InputRecord(input_type, path, content_hash)
        new_inputs = self.inputs | {new_input}
        return Provenance(inputs=new_inputs)

    def merge(self, other: Provenance) -> Provenance:
        """Merge two provenances."""
        return Provenance(inputs=self.inputs | other.inputs)

    @property
    def input_count(self) -> int:
        return len(self.inputs)

    def inputs_by_type(self, input_type: str) -> list[InputRecord]:
        """Get all inputs of a specific type."""
        return [inp for inp in self.inputs if inp.input_type == input_type]

    def summary(self) -> str:
        """Human-readable summary."""
        by_type: dict[str, int] = {}
        for inp in self.inputs:
            by_type[inp.input_type] = by_type.get(inp.input_type, 0) + 1

        parts = [f"{count} {typ}" for typ, count in sorted(by_type.items())]
        return f"Provenance({', '.join(parts)}) → {self.combined_hash}"


@dataclass
class ProvenanceRecord:
    """
    Stored provenance record with metadata.

    This is what gets persisted to disk.
    """

    # Page this provenance is for
    page_path: CacheKey

    # The provenance data
    provenance: Provenance

    # Output hash (for integrity verification)
    output_hash: ContentHash

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    build_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "page_path": self.page_path,
            "inputs": [
                {"type": inp.input_type, "path": inp.path, "hash": inp.hash}
                for inp in self.provenance.inputs
            ],
            "combined_hash": self.provenance.combined_hash,
            "output_hash": self.output_hash,
            "created_at": self.created_at.isoformat(),
            "build_id": self.build_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProvenanceRecord:
        """Deserialize from dict."""
        inputs = frozenset(
            InputRecord(inp["type"], CacheKey(inp["path"]), ContentHash(inp["hash"]))
            for inp in data.get("inputs", [])
        )
        return cls(
            page_path=CacheKey(data["page_path"]),
            provenance=Provenance(
                inputs=inputs,
                combined_hash=ContentHash(data.get("combined_hash", "")),
            ),
            output_hash=ContentHash(data.get("output_hash", "")),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            build_id=data.get("build_id", ""),
        )
