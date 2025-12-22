"""
Process-isolated build execution for crash resilience.

Runs site builds in a separate process (or thread) to ensure the dev server
remains responsive and can recover from build failures without restarting.

Features:
    - Process isolation via ProcessPoolExecutor (default)
    - GIL-aware: Uses ThreadPoolExecutor on Python 3.14+ with free-threading
    - Configurable executor type via BENGAL_BUILD_EXECUTOR environment variable
    - Serializable BuildRequest/BuildResult for cross-process communication
    - Timeout support to recover from hanging builds
    - Graceful executor lifecycle management

Classes:
    BuildRequest: Serializable build parameters for cross-process communication
    BuildResult: Serializable build outcome with success/error status
    BuildExecutor: Manages executor pool and submits build jobs

Environment Variables:
    BENGAL_BUILD_EXECUTOR: Force executor type ('thread' or 'process')
    BENGAL_BUILD_TIMEOUT: Timeout in seconds for build operations

Architecture:
    BuildExecutor creates a single-worker executor pool at initialization.
    Builds are submitted as BuildRequest objects and executed in the worker.
    Results are returned as BuildResult objects with timing and error info.

    Worker Selection:
    1. If BENGAL_BUILD_EXECUTOR='thread' → ThreadPoolExecutor
    2. If BENGAL_BUILD_EXECUTOR='process' → ProcessPoolExecutor
    3. If Python 3.14+ with GIL disabled → ThreadPoolExecutor (free-threading)
    4. Default → ProcessPoolExecutor (crash isolation)

Related:
    - bengal/server/build_trigger.py: Uses BuildExecutor for safe builds
    - bengal/server/dev_server.py: Manages executor lifecycle
    - bengal/orchestration/build_orchestrator.py: Actual build logic
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)

# Use spawn context to avoid fork issues with threads
# spawn starts a fresh Python interpreter, avoiding shared state issues
mp_context = multiprocessing.get_context("spawn")


@dataclass(frozen=True, slots=True)
class BuildRequest:
    """
    Serializable build request for cross-process execution.

    All fields must be picklable for use with ProcessPoolExecutor.
    Uses strings instead of Path objects for serialization.

    Attributes:
        site_root: Path to site root directory (as string)
        changed_paths: Tuple of changed file paths (as strings)
        incremental: Whether to use incremental build
        profile: Build profile name (e.g., "WRITER", "PUBLISHER")
        nav_changed_paths: Paths with navigation-affecting frontmatter changes
        structural_changed: Whether structural changes (create/delete/move) occurred
        parallel: Whether to use parallel rendering
        version_scope: RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
            Focus rebuilds on a single version (e.g., "v2", "latest").
            If None, all versions are rebuilt on changes.
    """

    site_root: str
    changed_paths: tuple[str, ...] = field(default_factory=tuple)
    incremental: bool = True
    profile: str = "WRITER"
    nav_changed_paths: tuple[str, ...] = field(default_factory=tuple)
    structural_changed: bool = False
    parallel: bool = True
    version_scope: str | None = None


@dataclass(frozen=True, slots=True)
class BuildResult:
    """
    Serializable build result from subprocess.

    All fields must be picklable for use with ProcessPoolExecutor.

    Attributes:
        success: Whether the build completed successfully
        pages_built: Number of pages rendered
        build_time_ms: Build duration in milliseconds
        error_message: Error message if build failed
        changed_outputs: Serialized output records as (path, type, phase) tuples
            for reload decision. Type is the OutputType.value string.
    """

    success: bool
    pages_built: int
    build_time_ms: float
    error_message: str | None = None
    # Serialized OutputRecords as (path_str, type_value, phase) tuples
    changed_outputs: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)


def _execute_build(request: BuildRequest) -> BuildResult:
    """
    Execute build in subprocess (picklable function).

    This function runs in a separate process and must be self-contained.
    It imports Bengal modules lazily to avoid import issues in the subprocess.

    Args:
        request: Build request with site configuration

    Returns:
        BuildResult with success status and statistics
    """
    start_time = time.time()

    try:
        # Import lazily in subprocess
        from bengal.core.site import Site
        from bengal.utils.profile import BuildProfile

        # Load site from config
        site_root = Path(request.site_root)
        site = Site.from_config(site_root)
        site.dev_mode = True

        # Set dev-specific config flags
        cfg = site.config
        site.dev_mode = True  # Runtime flag for dev server mode
        cfg["fingerprint_assets"] = False
        cfg.setdefault("minify_assets", False)

        # RFC: rfc-versioned-docs-pipeline-integration (Phase 3)
        # Store version_scope in site config for incremental build filtering
        if request.version_scope:
            cfg["_version_scope"] = request.version_scope

        # Get build profile
        profile = getattr(BuildProfile, request.profile, BuildProfile.WRITER)

        # Convert changed paths to Path objects
        changed_sources = (
            {Path(p) for p in request.changed_paths} if request.changed_paths else None
        )
        nav_changed_sources = (
            {Path(p) for p in request.nav_changed_paths} if request.nav_changed_paths else set()
        )

        # Execute build
        stats = site.build(
            profile=profile,
            incremental=request.incremental,
            parallel=request.parallel,
            changed_sources=changed_sources,
            nav_changed_sources=nav_changed_sources,
            structural_changed=request.structural_changed,
        )

        build_time_ms = (time.time() - start_time) * 1000

        # Serialize changed outputs to picklable tuples
        changed_outputs: tuple[tuple[str, str, str], ...] = ()
        if hasattr(stats, "changed_outputs") and stats.changed_outputs:
            changed_outputs = tuple(
                (str(record.path), record.output_type.value, record.phase)
                for record in stats.changed_outputs
            )

        return BuildResult(
            success=True,
            pages_built=stats.total_pages,
            build_time_ms=build_time_ms,
            changed_outputs=changed_outputs,
        )

    except Exception as e:
        build_time_ms = (time.time() - start_time) * 1000

        return BuildResult(
            success=False,
            pages_built=0,
            build_time_ms=build_time_ms,
            error_message=str(e),
        )


def is_free_threaded() -> bool:
    """
    Check if running on free-threaded Python (GIL disabled).

    Python 3.14+ with PEP 703 can disable the GIL, making threads
    truly parallel. In this mode, ThreadPoolExecutor is as good as
    ProcessPoolExecutor without the serialization overhead.

    Returns:
        True if running on free-threaded Python, False otherwise
    """
    if hasattr(sys, "_is_gil_enabled"):
        return not sys._is_gil_enabled()
    return False


def get_executor_type() -> str:
    """
    Determine which executor type to use.

    Order of precedence:
    1. BENGAL_BUILD_EXECUTOR env var ("thread", "process", or "auto")
    2. Auto-detection based on GIL status

    Returns:
        "thread" or "process"
    """
    env_override = os.environ.get("BENGAL_BUILD_EXECUTOR", "auto").lower()

    if env_override == "thread":
        return "thread"
    elif env_override == "process":
        return "process"
    else:  # auto
        if is_free_threaded():
            logger.debug("executor_auto_select", choice="thread", reason="free_threaded_python")
            return "thread"
        else:
            logger.debug("executor_auto_select", choice="process", reason="gil_enabled")
            return "process"


class BuildExecutor:
    """
    Manages process-isolated or thread-isolated build execution.

    Features:
        - Automatic executor type selection based on GIL status
        - Graceful shutdown
        - Timeout support for hanging builds
        - Error capture and reporting

    Example:
        >>> executor = BuildExecutor(max_workers=1)
        >>> request = BuildRequest(site_root="/path/to/site")
        >>> result = executor.submit(request, timeout=60.0)
        >>> if result.success:
        ...     print(f"Built {result.pages_built} pages")
        >>> executor.shutdown()
    """

    def __init__(self, max_workers: int = 1) -> None:
        """
        Initialize build executor.

        Args:
            max_workers: Maximum concurrent builds (default: 1 for dev server)
        """
        self.max_workers = max_workers
        self._executor: Executor | None = None
        self._executor_type: str | None = None

    def _get_executor(self) -> Executor:
        """
        Get or create the executor.

        Lazily creates the executor on first use to allow configuration
        changes before first build.

        Returns:
            Configured Executor instance
        """
        if self._executor is None:
            executor_type = get_executor_type()
            self._executor_type = executor_type

            if executor_type == "thread":
                self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
                logger.info("build_executor_created", type="thread", workers=self.max_workers)
            else:
                self._executor = ProcessPoolExecutor(
                    max_workers=self.max_workers,
                    mp_context=mp_context,
                )
                logger.info("build_executor_created", type="process", workers=self.max_workers)

        return self._executor

    def submit(
        self,
        request: BuildRequest,
        *,
        timeout: float | None = None,
    ) -> BuildResult:
        """
        Submit build request and wait for result.

        Args:
            request: Build request to execute
            timeout: Maximum time to wait for result (None = no timeout)

        Returns:
            BuildResult with success status and statistics

        Raises:
            TimeoutError: If build exceeds timeout
            Exception: If executor fails unexpectedly
        """
        executor = self._get_executor()

        logger.debug(
            "build_submitted",
            site_root=request.site_root,
            incremental=request.incremental,
            changed_files=len(request.changed_paths),
        )

        future = executor.submit(_execute_build, request)

        try:
            result = future.result(timeout=timeout)

            logger.debug(
                "build_complete",
                success=result.success,
                pages_built=result.pages_built,
                build_time_ms=round(result.build_time_ms, 2),
            )

            return result

        except TimeoutError:
            logger.error(
                "build_timeout",
                timeout=timeout,
                site_root=request.site_root,
            )

            return BuildResult(
                success=False,
                pages_built=0,
                build_time_ms=timeout * 1000 if timeout else 0,
                error_message=f"Build timed out after {timeout}s",
            )

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown executor gracefully.

        Args:
            wait: Whether to wait for pending builds to complete
        """
        if self._executor is not None:
            logger.debug("build_executor_shutdown", wait=wait)
            self._executor.shutdown(wait=wait)
            self._executor = None

    @property
    def executor_type(self) -> str | None:
        """
        Get the executor type currently in use.

        Returns:
            "thread", "process", or None if not yet initialized
        """
        return self._executor_type


def create_build_executor(max_workers: int = 1) -> BuildExecutor:
    """
    Create a build executor with default settings.

    Factory function for convenient executor creation.

    Args:
        max_workers: Maximum concurrent builds

    Returns:
        Configured BuildExecutor instance
    """
    return BuildExecutor(max_workers=max_workers)
