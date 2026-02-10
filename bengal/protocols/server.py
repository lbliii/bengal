"""
Server-facing protocols for rebuild and fragment update seams.

These protocols let `bengal.server` depend on behavior contracts rather than
concrete orchestration implementations.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class RebuildDecisionLike(Protocol):
    """Structural type for rebuild decision objects."""

    @property
    def full_rebuild(self) -> bool:
        ...

    @property
    def reason(self) -> str:
        ...


@runtime_checkable
class RebuildClassifierProtocol(Protocol):
    """Classify whether a change set requires a full rebuild."""

    def classify(
        self,
        changed_paths: set[Path],
        event_types: set[str],
        *,
        is_template_change: Callable[[set[Path]], bool],
        should_regenerate_autodoc: Callable[[set[Path]], bool],
        is_shared_content_change: Callable[[set[Path]], bool],
        is_version_config_change: Callable[[set[Path]], bool],
    ) -> RebuildDecisionLike:
        """Return a decision object with full_rebuild/reason fields."""
        ...


@runtime_checkable
class FragmentFastPathProtocol(Protocol):
    """Try fast-path fragment updates before falling back to full build."""

    def try_content_update(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        """Return True when content fragment update handled all changes."""
        ...

    def try_template_update(self, changed_paths: set[Path], event_types: set[str]) -> bool:
        """Return True when template fragment update handled all changes."""
        ...


@runtime_checkable
class ReloadControllerProtocol(Protocol):
    """Protocol for reload decision controller used by dev server trigger."""

    @property
    def _use_content_hashes(self) -> bool:  # noqa: SLF001 - protocol mirrors existing surface
        ...

    @property
    def _baseline_content_hashes(self) -> object | None:  # noqa: SLF001
        ...

    def capture_content_hash_baseline(self, output_dir: Path) -> None:
        ...

    def decide_from_outputs(self, records: list[object]) -> object:
        ...

    def decide_from_changed_paths(self, changed_paths: list[str]) -> object:
        ...

    def decide_with_content_hashes(self, output_dir: Path) -> object:
        ...
