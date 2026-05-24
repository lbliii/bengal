"""Read-only dependency index contracts for incremental build proofs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from bengal.build.contracts.keys import CacheKey
    from bengal.build.provenance.types import ProvenanceRecord


@dataclass(frozen=True, slots=True)
class DependencyIndexEntry:
    """Serializable read-model entry from one dependency to affected outputs."""

    dependency_kind: str
    dependency_key: str
    page_keys: tuple[str, ...] = ()
    output_keys: tuple[str, ...] = ()
    invalidation_reason: str = ""
    producer: str = ""

    def __post_init__(self) -> None:
        """Normalize tuple fields for deterministic equality and serialization."""
        object.__setattr__(self, "page_keys", tuple(sorted(set(self.page_keys))))
        object.__setattr__(self, "output_keys", tuple(sorted(set(self.output_keys))))

    @property
    def is_empty(self) -> bool:
        """True when the dependency does not map to any known output."""
        return not self.page_keys and not self.output_keys

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize to a cache-friendly dictionary."""
        return {
            "dependency_kind": self.dependency_kind,
            "dependency_key": self.dependency_key,
            "page_keys": list(self.page_keys),
            "output_keys": list(self.output_keys),
            "invalidation_reason": self.invalidation_reason,
            "producer": self.producer,
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> DependencyIndexEntry:
        """Deserialize from a cache-friendly dictionary."""
        page_keys = data.get("page_keys") or ()
        output_keys = data.get("output_keys") or ()
        return cls(
            dependency_kind=str(data.get("dependency_kind", "")),
            dependency_key=str(data.get("dependency_key", "")),
            page_keys=tuple(str(key) for key in page_keys),
            output_keys=tuple(str(key) for key in output_keys),
            invalidation_reason=str(data.get("invalidation_reason", "")),
            producer=str(data.get("producer", "")),
        )


class DependencyReadIndex:
    """Read-only dependency-to-page/output lookup table."""

    def __init__(self, entries: list[DependencyIndexEntry] | None = None) -> None:
        self._entries: dict[tuple[str, str], DependencyIndexEntry] = {}
        for entry in entries or ():
            self._entries[(entry.dependency_kind, entry.dependency_key)] = entry

    def get(self, dependency_kind: str, dependency_key: str) -> DependencyIndexEntry | None:
        """Return the entry for a normalized dependency, if known."""
        return self._entries.get((dependency_kind, dependency_key))

    def affected_page_keys(self, dependency_kind: str, dependency_key: str) -> tuple[str, ...]:
        """Return affected page keys for a dependency."""
        entry = self.get(dependency_kind, dependency_key)
        return entry.page_keys if entry else ()

    def affected_output_keys(self, dependency_kind: str, dependency_key: str) -> tuple[str, ...]:
        """Return affected output keys for a dependency."""
        entry = self.get(dependency_kind, dependency_key)
        return entry.output_keys if entry else ()

    def __len__(self) -> int:
        """Return the number of dependency entries."""
        return len(self._entries)

    @property
    def is_empty(self) -> bool:
        """True when the index has no dependency entries."""
        return not self._entries

    def to_cache_dict(self) -> dict[str, Any]:
        """Serialize entries with stable dependency keys."""
        return {
            f"{kind}:{key}": entry.to_cache_dict()
            for (kind, key), entry in sorted(self._entries.items())
        }

    @classmethod
    def from_cache_dict(cls, data: dict[str, Any]) -> DependencyReadIndex:
        """Deserialize a read index from a cache-friendly dictionary."""
        entries: list[DependencyIndexEntry] = []
        for entry in data.values():
            if not isinstance(entry, dict):
                continue
            try:
                entries.append(DependencyIndexEntry.from_cache_dict(entry))
            except TypeError, ValueError:
                continue
        return cls(entries)


def build_dependency_read_index(
    records: Iterable[ProvenanceRecord],
    *,
    output_keys: Mapping[CacheKey, tuple[str, ...]] | None = None,
    skip_kinds: frozenset[str] = frozenset({"config"}),
) -> DependencyReadIndex:
    """Build a read-only dependency index from existing provenance records."""
    pages_by_dependency: dict[tuple[str, str], set[str]] = {}
    outputs_by_dependency: dict[tuple[str, str], set[str]] = {}

    for record in records:
        page_key = str(record.page_path)
        record_output_keys = tuple(output_keys.get(record.page_path, ())) if output_keys else ()
        for dependency in record.provenance.inputs:
            if dependency.input_type in skip_kinds:
                continue
            key = (dependency.input_type, str(dependency.path))
            pages_by_dependency.setdefault(key, set()).add(page_key)
            outputs_by_dependency.setdefault(key, set()).update(record_output_keys)

    entries = [
        DependencyIndexEntry(
            dependency_kind=kind,
            dependency_key=dependency_key,
            page_keys=tuple(pages_by_dependency[(kind, dependency_key)]),
            output_keys=tuple(outputs_by_dependency.get((kind, dependency_key), ())),
            invalidation_reason=f"{kind}_dependency_changed",
            producer="provenance",
        )
        for kind, dependency_key in pages_by_dependency
    ]
    return DependencyReadIndex(entries)


__all__ = ["DependencyIndexEntry", "DependencyReadIndex", "build_dependency_read_index"]
