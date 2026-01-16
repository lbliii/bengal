"""
Infrastructure protocols for caching, progress, and I/O.

This module defines interface contracts for infrastructure components:
- Progress reporting for build feedback
- Caching for serialization/deserialization
- Output collection for build artifacts
- Content sources for multi-backend content loading
- Output targets for build output destinations

Design Philosophy:
- **Thread-safe**: All implementations must be thread-safe
- **Protocol-based**: Duck typing without inheritance requirements
- **Minimal contracts**: Only essential methods required

See Also:
- bengal.utils.progress: Progress reporter implementations
- bengal.cache: Cache infrastructure
- bengal.content.sources: Content source implementations

"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from typing import Literal

    from bengal.content.sources.entry import ContentEntry
    from bengal.core.output.types import OutputRecord, OutputType


# TypeVar for Cacheable
T = TypeVar("T", bound="Cacheable")


# =============================================================================
# Progress Reporting Protocol
# =============================================================================


@runtime_checkable
class ProgressReporter(Protocol):
    """
    Protocol for reporting build progress and user-facing messages.
    
    Defines interface for progress reporting implementations. Used throughout
    the build system for consistent progress reporting across CLI, server, and
    test contexts.
    
    Thread Safety:
        Implementations MUST be thread-safe. All methods may be called
        concurrently from multiple threads during parallel builds.
    
    Implementations:
        - NoopReporter: No-op implementation for tests
        - LiveProgressReporterAdapter: Adapter for LiveProgressManager
        - CLI implementations: Rich progress bars for CLI
    
    Example:
            >>> def report_progress(reporter: ProgressReporter):
            ...     reporter.start_phase("rendering")
            ...     reporter.update_phase("rendering", current=5, total=10)
            ...     reporter.complete_phase("rendering")
        
    """

    def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None:
        """Add a new phase to track."""
        ...

    def start_phase(self, phase_id: str) -> None:
        """Mark a phase as started."""
        ...

    def update_phase(
        self, phase_id: str, current: int | None = None, current_item: str | None = None
    ) -> None:
        """Update phase progress."""
        ...

    def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None:
        """Mark a phase as complete."""
        ...

    def log(self, message: str) -> None:
        """Log a message to the user."""
        ...


# =============================================================================
# Caching Protocol
# =============================================================================


@runtime_checkable
class Cacheable(Protocol):
    """
    Protocol for types that can be cached to disk.
    
    Types implementing this protocol can be automatically serialized to JSON
    and deserialized, with type checker validation.
    
    Contract Requirements:
        1. JSON Primitives Only: to_cache_dict() must return only JSON-serializable
           types: str, int, float, bool, None, list, dict.
    
        2. Type Conversion: Complex types must be converted:
           - datetime → ISO-8601 string (via datetime.isoformat())
           - Path → str (via str(path))
           - set → sorted list (for stability)
    
        3. No Object References: Never serialize live objects (Page, Section, Asset).
           Use stable identifiers (usually string paths) instead.
    
        4. Round-trip Invariant: T.from_cache_dict(obj.to_cache_dict()) must
           reconstruct an equivalent object (== by fields).
    
    Thread Safety:
        to_cache_dict() and from_cache_dict() MUST be thread-safe.
        They may be called concurrently during parallel cache operations.
    
    Example:
            >>> @dataclass
            ... class TagEntry(Cacheable):
            ...     tag_slug: str
            ...     page_paths: list[str]
            ...
            ...     def to_cache_dict(self) -> dict[str, Any]:
            ...         return {'tag_slug': self.tag_slug, 'page_paths': self.page_paths}
            ...
            ...     @classmethod
            ...     def from_cache_dict(cls, data: dict[str, Any]) -> 'TagEntry':
            ...         return cls(tag_slug=data['tag_slug'], page_paths=data['page_paths'])
        
    """

    def to_cache_dict(self) -> dict[str, Any]:
        """
        Serialize to cache-friendly dictionary.

        Must return JSON-serializable types only.

        Returns:
            Dictionary suitable for JSON serialization
        """
        ...

    @classmethod
    def from_cache_dict(cls: type[T], data: dict[str, Any]) -> T:
        """
        Deserialize from cache dictionary.

        Must be inverse of to_cache_dict().

        Args:
            data: Dictionary from cache (JSON-deserialized)

        Returns:
            Reconstructed instance
        """
        ...


# =============================================================================
# Output Collection Protocol
# =============================================================================


@runtime_checkable
class OutputCollector(Protocol):
    """
    Protocol for collecting output writes during build.
    
    Implementations track files written during a build, enabling
    reliable hot reload decisions and build verification.
    
    Thread Safety:
        Implementations MUST be thread-safe. All methods may be called
        concurrently from multiple threads during parallel builds.
    
    Example:
            >>> collector.record(Path("posts/hello.html"), OutputType.HTML, "render")
            >>> collector.record(Path("assets/style.css"), phase="asset")
            >>> collector.css_only()
        False
        
    """

    def record(
        self,
        path: Path,
        output_type: OutputType | None = None,
        phase: Literal["render", "asset", "postprocess"] = "render",
    ) -> None:
        """
        Record an output file write.

        Args:
            path: Path to the output file
            output_type: Type of output; auto-detected from extension if None
            phase: Build phase that produced this output
        """
        ...

    def get_outputs(
        self,
        output_type: OutputType | None = None,
    ) -> list[OutputRecord]:
        """
        Get all recorded outputs, optionally filtered by type.

        Args:
            output_type: If provided, filter to only this type

        Returns:
            List of output records
        """
        ...

    def css_only(self) -> bool:
        """
        Check if all recorded outputs are CSS files.

        Returns:
            True if all outputs are CSS, False otherwise
        """
        ...

    def clear(self) -> None:
        """Clear all recorded outputs."""
        ...


# =============================================================================
# Content Source Protocol
# =============================================================================


@runtime_checkable
class ContentSourceProtocol(Protocol):
    """
    Protocol interface for content sources.
    
    This is the Protocol version of ContentSource ABC for cases
    where duck typing is preferred over inheritance.
    
    Enables loading content from different backends:
    - Filesystem (default)
    - Git repositories (for versioned docs)
    - Remote APIs (headless CMS)
    - In-memory (testing)
    
    Note:
        The existing ContentSource ABC remains for implementations
        that prefer inheritance. Both satisfy this protocol.
    
    Thread Safety:
        Implementations MUST be thread-safe. fetch_all() and fetch_one()
        may be called concurrently during parallel builds.
    
    Example:
            >>> async for entry in source.fetch_all():
            ...     print(entry.title)
        
    """

    @property
    def name(self) -> str:
        """Source instance name (e.g., 'api-docs', 'main-content')."""
        ...

    @property
    def source_type(self) -> str:
        """Source type identifier (e.g., 'local', 'github', 'notion')."""
        ...

    async def fetch_all(self) -> AsyncIterator[ContentEntry]:
        """Fetch all content entries from this source."""
        ...

    async def fetch_one(self, id: str) -> ContentEntry | None:
        """Fetch a single content entry by ID."""
        ...


# =============================================================================
# Output Target Protocol
# =============================================================================


@runtime_checkable
class OutputTarget(Protocol):
    """
    Abstract interface for build output.
    
    Enables writing to different backends:
    - Filesystem (default)
    - In-memory (testing, preview)
    - S3/Cloud storage (deployment)
    - ZIP archive (distribution)
    
    Thread Safety:
        Implementations MUST be thread-safe. The write() and copy()
        methods will be called concurrently by multiple render threads
        when Bengal is configured with parallel=true.
    
    Example:
            >>> target.mkdir("posts")
            >>> target.write("posts/hello.html", "<h1>Hello</h1>")
            >>> target.exists("posts/hello.html")
        True
        
    """

    @property
    def name(self) -> str:
        """Target identifier (e.g., 'filesystem', 'memory', 's3')."""
        ...

    def write(self, path: str, content: str) -> None:
        """Write string content."""
        ...

    def write_bytes(self, path: str, content: bytes) -> None:
        """Write binary content."""
        ...

    def copy(self, src: str, dest: str) -> None:
        """Copy file from source path to destination."""
        ...

    def mkdir(self, path: str) -> None:
        """Ensure directory exists."""
        ...

    def exists(self, path: str) -> bool:
        """Check if path exists in output."""
        ...


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "ProgressReporter",
    "Cacheable",
    "OutputCollector",
    "ContentSourceProtocol",
    "OutputTarget",
]
