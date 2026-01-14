"""Base class for output format generators.

Provides shared functionality for all output format generators:
- Atomic file writes (crash-safe)
- Progress reporting integration
- Error handling with recovery
- BuildContext integration for accumulated data

All output generators should inherit from BaseOutputGenerator to ensure
consistent behavior across the codebase.

Example:
    >>> class MyGenerator(BaseOutputGenerator):
    ...     def generate(self) -> int:
    ...         # Generate files using self.write_text() or self.write_bytes()
    ...         self.write_text(output_path, content)
    ...         return 1  # Return count of files generated
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.utils.io.atomic_write import atomic_write_bytes, atomic_write_text
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext


class BaseOutputGenerator(ABC):
    """
    Base class for output format generators.
    
    Provides:
    - Atomic file writes (crash-safe)
    - Progress reporting integration
    - Error handling with recovery
    - BuildContext integration for accumulated data
    
    Subclasses must implement:
    - generate(): Generate output files and return count
    
    Attributes:
        site: Site instance with pages and configuration
        build_context: Optional BuildContext with cached data
        logger: Logger instance for this generator
        
    """

    def __init__(
        self,
        site: Site,
        build_context: BuildContext | None = None,
    ) -> None:
        """
        Initialize the output generator.

        Args:
            site: Site instance with pages and configuration
            build_context: Optional BuildContext with cached data (e.g., knowledge graph)
        """
        self.site = site
        self.build_context = build_context
        self.logger = get_logger(self.__class__.__module__)

    @abstractmethod
    def generate(self) -> int:
        """
        Generate output files.

        Subclasses should implement this method to generate their specific
        output format(s). Use self.write_text() or self.write_bytes() for
        atomic file writes.

        Returns:
            Number of files generated
        """
        ...

    def write_text(self, path: Path, content: str) -> None:
        """
        Write text file atomically.

        Creates parent directories if needed and writes content atomically
        to prevent partial writes on crash.

        Args:
            path: Destination file path
            content: Text content to write
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, content)

    def write_bytes(self, path: Path, content: bytes) -> None:
        """
        Write binary file atomically.

        Creates parent directories if needed and writes content atomically
        to prevent partial writes on crash.

        Args:
            path: Destination file path
            content: Binary content to write
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, content)

    def get_accumulated_data(self) -> list | None:
        """
        Get accumulated page data from build context.

        Returns accumulated JSON data collected during page rendering,
        useful for generating aggregate outputs like search indexes.

        Returns:
            List of accumulated page data, or None if not available
        """
        if self.build_context:
            return getattr(self.build_context, "_accumulated_page_json", None)
        return None

    @property
    def output_dir(self) -> Path:
        """Get the site's output directory."""
        return self.site.output_dir
