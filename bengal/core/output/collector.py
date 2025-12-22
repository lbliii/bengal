"""Output collection protocol and implementation.

This module provides a thread-safe collector for tracking output files
written during a build. The collector enables reliable hot reload decisions
by providing typed output information to the dev server.
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bengal.core.output.types import OutputRecord, OutputType
from bengal.utils.logger import get_logger

if TYPE_CHECKING:
    from typing import Literal


@runtime_checkable
class OutputCollector(Protocol):
    """Protocol for collecting output writes during build.

    Implementations must be thread-safe for parallel builds.
    """

    def record(
        self,
        path: Path,
        output_type: OutputType | None = None,
        phase: Literal["render", "asset", "postprocess"] = "render",
    ) -> None:
        """Record an output file write.

        Args:
            path: Path to the output file (absolute or relative to output_dir)
            output_type: Type of output; auto-detected from extension if None
            phase: Build phase that produced this output
        """
        ...

    def get_outputs(
        self,
        output_type: OutputType | None = None,
    ) -> list[OutputRecord]:
        """Get all recorded outputs, optionally filtered by type.

        Args:
            output_type: If provided, filter to only this type

        Returns:
            List of output records
        """
        ...

    def css_only(self) -> bool:
        """Check if all recorded outputs are CSS files.

        Returns:
            True if all outputs are CSS, False otherwise
        """
        ...

    def clear(self) -> None:
        """Clear all recorded outputs."""
        ...


class BuildOutputCollector:
    """Thread-safe implementation of OutputCollector for builds.

    This collector tracks all output files written during a build,
    enabling reliable hot reload decisions in the dev server.

    Attributes:
        output_dir: Base output directory for relative path calculation

    Example:
        >>> collector = BuildOutputCollector(Path("/site/public"))
        >>> collector.record(Path("posts/hello.html"), OutputType.HTML, "render")
        >>> collector.record(Path("assets/style.css"), phase="asset")
        >>> collector.css_only()
        False
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        """Initialize the output collector.

        Args:
            output_dir: Base output directory for relative path calculation.
                       If None, paths are stored as-is.
        """
        self._output_dir = output_dir
        self._outputs: list[OutputRecord] = []
        self._lock = Lock()
        self._logger = get_logger(__name__)

    def record(
        self,
        path: Path,
        output_type: OutputType | None = None,
        phase: Literal["render", "asset", "postprocess"] = "render",
    ) -> None:
        """Record an output file write.

        Thread-safe: uses lock for concurrent access during parallel builds.

        Args:
            path: Path to the output file (absolute or relative to output_dir)
            output_type: Type of output; auto-detected from extension if None
            phase: Build phase that produced this output
        """
        # Make path relative to output_dir if absolute
        if self._output_dir and path.is_absolute():
            with suppress(ValueError):
                path = path.relative_to(self._output_dir)

        # Create record, auto-detecting type if not provided
        if output_type is None:
            record = OutputRecord.from_path(path, phase=phase)
        else:
            record = OutputRecord(path=path, output_type=output_type, phase=phase)

        with self._lock:
            self._outputs.append(record)

    def get_outputs(
        self,
        output_type: OutputType | None = None,
    ) -> list[OutputRecord]:
        """Get all recorded outputs, optionally filtered by type.

        Thread-safe: returns a copy of the outputs list.

        Args:
            output_type: If provided, filter to only this type

        Returns:
            List of output records
        """
        with self._lock:
            if output_type is None:
                return list(self._outputs)
            return [o for o in self._outputs if o.output_type == output_type]

    def get_relative_paths(
        self,
        output_type: OutputType | None = None,
    ) -> list[str]:
        """Get output paths as strings, optionally filtered by type.

        Useful for passing to ReloadController.

        Args:
            output_type: If provided, filter to only this type

        Returns:
            List of relative path strings
        """
        return [str(o.path) for o in self.get_outputs(output_type)]

    def css_only(self) -> bool:
        """Check if all recorded outputs are CSS files.

        Returns:
            True if all outputs are CSS and at least one output exists,
            False otherwise
        """
        with self._lock:
            if not self._outputs:
                return False
            return all(o.output_type == OutputType.CSS for o in self._outputs)

    def clear(self) -> None:
        """Clear all recorded outputs.

        Thread-safe: uses lock for concurrent access.
        """
        with self._lock:
            self._outputs.clear()

    def validate(self, changed_sources: list[str] | None = None) -> None:
        """Validate tracking integrity and log warnings.

        Logs a warning if sources were changed but no outputs recorded,
        which may indicate missing record() calls in writers.

        Args:
            changed_sources: List of source files that changed (for comparison)
        """
        with self._lock:
            if changed_sources and not self._outputs:
                self._logger.warning(
                    "output_tracking_empty",
                    changed_source_count=len(changed_sources),
                )

    def __len__(self) -> int:
        """Return number of recorded outputs."""
        with self._lock:
            return len(self._outputs)

    def __bool__(self) -> bool:
        """Return True if any outputs recorded."""
        with self._lock:
            return bool(self._outputs)
