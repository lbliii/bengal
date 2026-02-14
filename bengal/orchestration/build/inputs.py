"""
Build input consolidation for Bengal SSG.

Provides BuildInput as a single frozen record of all inputs to a build,
enabling serialization, logging, and replay for debugging.

See Also:
- plan/analysis-pipeline-inputs-and-vertical-stacks.md
- bengal.orchestration.build.options: BuildOptions
- bengal.server.build_executor: BuildRequest (serializable view)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.orchestration.build.options import BuildOptions

if TYPE_CHECKING:
    from bengal.server.build_executor import BuildRequest


@dataclass(frozen=True)
class BuildInput:
    """
    Complete, serializable record of all inputs to a build.

    Consolidates BuildOptions with change hints from the file watcher.
    Used for logging, debugging, and process-isolated build requests.

    Attributes:
        options: BuildOptions with all build configuration
        site_root: Path to site root directory
        config_hash: Optional hash for cache invalidation (empty if not computed)
        changed_sources: Paths to content files that changed (from watcher)
        nav_changed_sources: Paths with navigation-affecting frontmatter changes
        structural_changed: Whether structural changes (create/delete/move) occurred
        event_types: File watcher event types (created, modified, deleted, moved)
        version_scope: Optional version scope for multi-version sites (e.g. "v2")
    """

    options: BuildOptions
    site_root: Path
    config_hash: str = ""
    changed_sources: frozenset[Path] = frozenset()
    nav_changed_sources: frozenset[Path] = frozenset()
    structural_changed: bool = False
    event_types: frozenset[str] = frozenset()
    version_scope: str | None = None

    @classmethod
    def from_options(
        cls,
        options: BuildOptions,
        site_root: Path,
        *,
        config_hash: str = "",
        changed_sources: frozenset[Path] | None = None,
        nav_changed_sources: frozenset[Path] | None = None,
        structural_changed: bool | None = None,
        event_types: frozenset[str] | None = None,
        version_scope: str | None = None,
    ) -> BuildInput:
        """Create BuildInput from BuildOptions with optional overrides."""
        return cls(
            options=options,
            site_root=Path(site_root),
            config_hash=config_hash or "",
            changed_sources=(
                changed_sources
                if changed_sources is not None
                else frozenset(options.changed_sources or ())
            ),
            nav_changed_sources=(
                nav_changed_sources
                if nav_changed_sources is not None
                else frozenset(options.nav_changed_sources or ())
            ),
            structural_changed=structural_changed
            if structural_changed is not None
            else options.structural_changed,
            event_types=event_types if event_types is not None else frozenset(),
            version_scope=version_scope,
        )

    @classmethod
    def from_build_request(cls, request: BuildRequest) -> BuildInput:
        """Create BuildInput from BuildRequest (e.g. in subprocess)."""
        from bengal.utils.observability.profile import BuildProfile

        profile = BuildProfile.from_string(request.profile)
        options = BuildOptions(
            force_sequential=request.force_sequential,
            incremental=request.incremental,
            profile=profile,
            memory_optimized=getattr(request, "memory_optimized", False),
            explain=getattr(request, "explain", False),
            dry_run=getattr(request, "dry_run", False),
            profile_templates=getattr(request, "profile_templates", False),
            changed_sources={Path(p) for p in request.changed_paths},
            nav_changed_sources={Path(p) for p in request.nav_changed_paths},
            structural_changed=request.structural_changed,
        )
        return cls(
            options=options,
            site_root=Path(request.site_root),
            changed_sources=frozenset(Path(p) for p in request.changed_paths),
            nav_changed_sources=frozenset(Path(p) for p in request.nav_changed_paths),
            structural_changed=request.structural_changed,
            version_scope=request.version_scope,
        )

    def to_build_request(self) -> BuildRequest:
        """Convert to BuildRequest for process-isolated builds."""
        from bengal.server.build_executor import BuildRequest

        return BuildRequest(
            site_root=str(self.site_root),
            changed_paths=tuple(str(p) for p in self.changed_sources),
            incremental=bool(self.options.incremental)
            if self.options.incremental is not None
            else True,
            profile=(self.options.profile.value if self.options.profile else "writer"),
            nav_changed_paths=tuple(str(p) for p in self.nav_changed_sources),
            structural_changed=self.structural_changed,
            force_sequential=self.options.force_sequential,
            version_scope=self.version_scope,
            memory_optimized=self.options.memory_optimized,
            explain=self.options.explain,
            dry_run=self.options.dry_run,
            profile_templates=self.options.profile_templates,
        )
