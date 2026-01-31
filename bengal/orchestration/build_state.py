"""
Build State - Per-build mutable state for Bengal SSG.

Provides BuildState dataclass for tracking mutable state during a single build
execution. Created fresh for each build, passed through orchestration phases,
and discarded after build completes.

Public API:
BuildState: Per-build mutable state container

Key Concepts:
Per-Build Isolation: Each build gets fresh state, preventing cross-build
    interference and eliminating stale state bugs in dev server.

Thread-Safe Locks: Named locks via get_lock() for parallel operations
    during rendering phase.

Render Context: current_language/current_version set per-page during
    rendering, enabling template functions to access correct context.

Lifecycle:
1. Created at start of BuildOrchestrator.build()
2. Passed through all build phases
3. Discarded after build completes (stats extracted first)

Thread Safety:
- get_lock() provides named locks for parallel operations
- Per-build isolation prevents cross-build interference
- DevServer creates new BuildState for each rebuild

Related Packages:
bengal.orchestration.build: Build coordinator that creates/uses state
bengal.core.site.core: Site with _current_build_state bridge property
bengal.rendering.template_engine: Template engine using state caches

See Also:
plan/drafted/rfc-site-responsibility-separation.md

"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass
class BuildState:
    """
    Mutable state for a single build execution.

    Created fresh for each build. Passed through orchestration phases.
    Never stored on Site—Site remains the stable data container.

    Lifecycle:
        1. Created at start of BuildOrchestrator.build()
        2. Passed through all 21 build phases
        3. Discarded after build completes (stats extracted first)

    Thread Safety:
        - get_lock() provides named locks for parallel operations
        - Per-build isolation prevents cross-build interference
        - DevServer creates new BuildState for each rebuild

    Attributes:
        build_time: Timestamp when build started
        incremental: Whether this is an incremental build
        dev_mode: Whether running in dev server mode
        current_language: Language code for current page (during rendering)
        current_version: Version ID for current page (during rendering)
        features_detected: CSS features detected during discovery
        discovery_timing_ms: Timing breakdown from discovery phase
        template_cache: Per-build template compilation cache
        asset_manifest_cache: Per-build asset manifest cache
        theme_chain_cache: Cached theme chain for template resolution
        template_dirs_cache: Cached template directories
        template_metadata_cache: Cached template metadata
        asset_manifest_previous: Previous manifest for incremental comparison
        asset_manifest_fallbacks: Set of fallback warnings already emitted

    """

    # Build context
    build_time: datetime = field(default_factory=datetime.now)
    incremental: bool = False
    dev_mode: bool = False

    # Current render context (set per-page during rendering)
    current_language: str | None = None
    current_version: str | None = None

    # Discovery results
    features_detected: set[str] = field(default_factory=set)
    discovery_timing_ms: dict[str, float] = field(default_factory=dict)

    # Caches (cleared per-build)
    template_cache: dict[str, Any] = field(default_factory=dict)
    asset_manifest_cache: dict[str, Any] = field(default_factory=dict)
    theme_chain_cache: list[str] | None = None

    # Template directory caches
    template_dirs_cache: dict[str, Any] | None = None
    template_metadata_cache: dict[str, Any] | None = None

    # Asset manifest state
    asset_manifest_previous: Any = None
    asset_manifest_fallbacks: set[str] = field(default_factory=set)

    # Thread-safe locks - guarded by _locks_guard for atomic creation
    _locks: dict[str, Lock] = field(default_factory=dict)
    _locks_guard: Lock = field(default_factory=Lock)

    def get_lock(self, name: str) -> Lock:
        """
        Get or create a named lock for thread-safe operations.

        Thread-safe: Uses _locks_guard to ensure atomic lock creation
        even when multiple threads request the same lock simultaneously.

        Args:
            name: Lock identifier (e.g., "asset_write", "template_compile")

        Returns:
            Lock instance for the given name

        Example:
            with state.get_lock("asset_manifest"):
                # Thread-safe manifest updates
                manifest[key] = value
        """
        # Fast path: lock already exists (no guard needed for read)
        if name in self._locks:
            return self._locks[name]

        # Slow path: need to create lock with guard
        with self._locks_guard:
            # Double-check after acquiring guard
            if name not in self._locks:
                self._locks[name] = Lock()
            return self._locks[name]

    def reset_caches(self) -> None:
        """
        Reset all caches for fresh build.

        Called at start of build or when config changes require
        full cache invalidation.
        """
        self.template_cache.clear()
        self.asset_manifest_cache.clear()
        self.theme_chain_cache = None
        self.template_dirs_cache = None
        self.template_metadata_cache = None
        self.features_detected.clear()
        self.asset_manifest_fallbacks.clear()

    def set_render_context(self, language: str | None, version: str | None) -> None:
        """
        Set current render context (called per-page during rendering).

        Args:
            language: Current language code (e.g., "en", "es") or None
            version: Current version ID (e.g., "v2", "latest") or None
        """
        self.current_language = language
        self.current_version = version

    def clear_render_context(self) -> None:
        """Clear render context after page rendering."""
        self.current_language = None
        self.current_version = None

    def __repr__(self) -> str:
        mode = "incremental" if self.incremental else "full"
        dev = " (dev)" if self.dev_mode else ""
        return f"BuildState({mode}{dev}, features={len(self.features_detected)})"
