"""Serializable build request records shared by server and orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BuildRequest:
    """
    Serializable build request for cross-process execution.

    All fields must be picklable for use with ProcessPoolExecutor.
    Uses strings instead of Path objects for serialization.
    """

    site_root: str
    changed_paths: tuple[str, ...] = field(default_factory=tuple)
    incremental: bool = True
    profile: str = "WRITER"
    nav_changed_paths: tuple[str, ...] = field(default_factory=tuple)
    structural_changed: bool = False
    force_sequential: bool = False
    version_scope: str | None = None
    memory_optimized: bool = False
    explain: bool = False
    dry_run: bool = False
    profile_templates: bool = False
    completion_policy: str = "complete"
    quiet: bool = False


__all__ = ["BuildRequest"]
