"""Output tracking types and protocol for build coordination.

This package provides typed output tracking for the build system,
enabling reliable hot reload decisions in the dev server.

Key Components:
    - OutputType: Enum classifying output files (HTML, CSS, JS, etc.)
    - OutputRecord: Immutable record of a written output file
    - OutputCollector: Protocol for output tracking
    - BuildOutputCollector: Thread-safe implementation

Example:
    >>> from bengal.core.output import BuildOutputCollector, OutputType
    >>> collector = BuildOutputCollector(output_dir=site.output_dir)
    >>> collector.record(page.output_path, OutputType.HTML, phase="render")
    >>> collector.css_only()  # Check if only CSS changed
    False
"""

from bengal.core.output.collector import BuildOutputCollector, OutputCollector
from bengal.core.output.types import OutputRecord, OutputType

__all__ = ["BuildOutputCollector", "OutputCollector", "OutputRecord", "OutputType"]
