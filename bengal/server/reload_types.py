"""
Reload-related data contracts for build → trigger handoff.
"""

from __future__ import annotations

from dataclasses import dataclass

from bengal.orchestration.stats import ReloadHint


@dataclass(frozen=True, slots=True)
class SerializedOutputRecord:
    """Serialized output record for cross-process handoff (path, type, phase)."""

    path: str
    type_value: str  # OutputType.value
    phase: str

    def to_tuple(self) -> tuple[str, str, str]:
        """Return (path, type_value, phase) for backward compatibility."""
        return (self.path, self.type_value, self.phase)

    @classmethod
    def from_tuple(cls, t: tuple[str, str, str]) -> SerializedOutputRecord:
        """Create from (path, type_value, phase) tuple."""
        if len(t) != 3:
            raise ValueError(f"Expected 3-tuple, got {len(t)}")
        return cls(path=t[0], type_value=t[1], phase=t[2])


@dataclass(frozen=True, slots=True)
class BuildReloadInfo:
    """Contract passed from build to trigger for reload decisions."""

    changed_files: tuple[str, ...]
    changed_outputs: tuple[SerializedOutputRecord, ...]
    reload_hint: ReloadHint | None
