"""
Error context helpers for enriching exceptions with standardized context.

Provides utilities for capturing and propagating error context including
file paths, line numbers, operations, build phases, and suggestions.

Key Components:
- BuildPhase: Enum indicating which build phase the error occurred in
- ErrorSeverity: Enum for error severity classification
- ErrorContext: Dataclass capturing all available context
- ErrorDebugPayload: Machine-readable debug context for AI troubleshooting
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.errors.codes import ErrorCode
    from bengal.errors.exceptions import BengalError


class BuildPhase(Enum):
    """
    Build phase where an error occurred.

    Helps narrow down which part of the codebase to investigate.
    """

    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    PARSING = "parsing"
    RENDERING = "rendering"
    POSTPROCESSING = "postprocessing"
    ASSET_PROCESSING = "asset_processing"
    CACHE = "cache"
    SERVER = "server"
    OUTPUT = "output"

    @property
    def primary_modules(self) -> list[str]:
        """Get primary Bengal modules for this phase."""
        module_map = {
            BuildPhase.INITIALIZATION: ["bengal/config/", "bengal/cli/"],
            BuildPhase.DISCOVERY: ["bengal/discovery/", "bengal/content_layer/"],
            BuildPhase.PARSING: ["bengal/rendering/markdown_parser.py", "bengal/core/page/"],
            BuildPhase.RENDERING: ["bengal/rendering/", "bengal/orchestration/render.py"],
            BuildPhase.POSTPROCESSING: ["bengal/postprocess/"],
            BuildPhase.ASSET_PROCESSING: ["bengal/assets/", "bengal/orchestration/asset.py"],
            BuildPhase.CACHE: ["bengal/cache/"],
            BuildPhase.SERVER: ["bengal/server/"],
            BuildPhase.OUTPUT: ["bengal/output/"],
        }
        return module_map.get(self, [])


class ErrorSeverity(Enum):
    """
    Error severity classification.

    Helps determine how to handle the error and whether build can continue.
    """

    FATAL = "fatal"  # Build cannot continue at all
    ERROR = "error"  # This item failed, build may continue
    WARNING = "warning"  # Something off, but recoverable
    HINT = "hint"  # Suggestion for improvement

    @property
    def can_continue(self) -> bool:
        """Whether build can typically continue after this severity."""
        return self != ErrorSeverity.FATAL

    @property
    def should_aggregate(self) -> bool:
        """Whether errors of this severity should be aggregated."""
        return self in (ErrorSeverity.ERROR, ErrorSeverity.WARNING)


@dataclass
class RelatedFile:
    """
    A file related to an error for debugging context.

    Attributes:
        role: What role this file plays (e.g., "template", "page", "config")
        path: Path to the file
        line_number: Optional line number of interest
    """

    role: str
    path: Path | str
    line_number: int | None = None

    def __str__(self) -> str:
        path_str = str(self.path)
        if self.line_number:
            return f"{self.role}: {path_str}:{self.line_number}"
        return f"{self.role}: {path_str}"


@dataclass
class ErrorDebugPayload:
    """
    Machine-parseable debug context for AI troubleshooting.

    This provides structured data that can be immediately used
    to investigate errors programmatically.
    """

    # What was being processed
    processing_item: str | None = None  # e.g., "page:docs/api/index.md"
    processing_type: str | None = None  # e.g., "page", "asset", "template"

    # Template context (for rendering errors)
    template_name: str | None = None
    template_line: int | None = None
    available_context_vars: list[str] = field(default_factory=list)

    # Relevant config keys being accessed
    config_keys_accessed: list[str] = field(default_factory=list)

    # Relevant config snapshot
    relevant_config: dict[str, Any] = field(default_factory=dict)

    # Error pattern info (from session tracking)
    similar_error_count: int = 0
    first_occurrence_file: str | None = None
    is_recurring: bool = False

    # Suggested investigation paths
    files_to_check: list[str] = field(default_factory=list)
    grep_patterns: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    build_duration_so_far: float | None = None  # seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "processing_item": self.processing_item,
            "processing_type": self.processing_type,
            "template_name": self.template_name,
            "template_line": self.template_line,
            "available_context_vars": self.available_context_vars,
            "config_keys_accessed": self.config_keys_accessed,
            "relevant_config": self.relevant_config,
            "similar_error_count": self.similar_error_count,
            "first_occurrence_file": self.first_occurrence_file,
            "is_recurring": self.is_recurring,
            "files_to_check": self.files_to_check,
            "grep_patterns": self.grep_patterns,
            "test_files": self.test_files,
            "timestamp": self.timestamp.isoformat(),
            "build_duration_so_far": self.build_duration_so_far,
        }


@dataclass
class ErrorContext:
    """
    Standardized error context for enriching exceptions.

    Captures all available context about where and why an error occurred,
    including build phase, related files, and debug payload.
    """

    # Location info
    file_path: Path | None = None
    line_number: int | None = None
    column: int | None = None

    # Operation context
    operation: str | None = None  # e.g., "parsing frontmatter", "rendering template"
    suggestion: str | None = None
    original_error: Exception | None = None

    # Build phase and subsystem
    build_phase: BuildPhase | None = None
    subsystem: str | None = None  # e.g., "core", "orchestration", "rendering"

    # Error classification
    error_code: ErrorCode | None = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recoverable: bool = True
    skip_allowed: bool = True  # Can we skip this item and continue?

    # Related files for debugging
    related_files: list[RelatedFile] = field(default_factory=list)

    # Template-specific context
    template_name: str | None = None
    template_context_keys: list[str] = field(default_factory=list)

    # Config context
    config_keys_accessed: list[str] = field(default_factory=list)

    # Full debug payload (for complex errors)
    debug_payload: ErrorDebugPayload | None = None

    def add_related_file(
        self,
        role: str,
        path: Path | str,
        line_number: int | None = None,
    ) -> None:
        """Add a related file for debugging context."""
        self.related_files.append(RelatedFile(role=role, path=path, line_number=line_number))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "column": self.column,
            "operation": self.operation,
            "suggestion": self.suggestion,
            "build_phase": self.build_phase.value if self.build_phase else None,
            "subsystem": self.subsystem,
            "error_code": str(self.error_code) if self.error_code else None,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "skip_allowed": self.skip_allowed,
            "related_files": [str(rf) for rf in self.related_files],
            "template_name": self.template_name,
            "template_context_keys": self.template_context_keys,
            "config_keys_accessed": self.config_keys_accessed,
        }
        if self.debug_payload:
            result["debug_payload"] = self.debug_payload.to_dict()
        return result


def enrich_error(
    error: Exception,
    context: ErrorContext,
    error_class: type[BengalError] | None = None,
) -> BengalError:
    """
    Enrich exception with standardized context.

    If error is already a BengalError, adds missing context fields.
    Otherwise, wraps error in a new BengalError instance.

    Args:
        error: Exception to enrich
        context: Error context to add
        error_class: Class to use for wrapping (defaults to BengalError)

    Returns:
        Enriched BengalError instance

    Example:
        >>> from bengal.errors import BengalError, ErrorContext, enrich_error
        >>>
        >>> try:
        ...     parse_file(path)
        ... except Exception as e:
        ...     context = ErrorContext(
        ...         file_path=path,
        ...         operation="parsing file",
        ...         build_phase=BuildPhase.PARSING,
        ...     )
        ...     enriched = enrich_error(e, context)
        ...     raise enriched
    """
    from bengal.errors.exceptions import BengalError as BaseBengalError

    # Use provided error class or default to BengalError
    if error_class is None:
        error_class = BaseBengalError

    # If already a BengalError, enrich with missing context
    if isinstance(error, BaseBengalError):
        # Add missing context fields (don't overwrite existing)
        if context.file_path and not error.file_path:
            error.file_path = context.file_path
        if context.line_number and not error.line_number:
            error.line_number = context.line_number
        if context.suggestion and not error.suggestion:
            error.suggestion = context.suggestion
        if context.original_error and not error.original_error:
            error.original_error = context.original_error
        if context.error_code and not error.code:
            error.code = context.error_code
        if context.build_phase and not error.build_phase:
            error.build_phase = context.build_phase
        if context.severity and not error.severity:
            error.severity = context.severity
        if context.related_files and not error.related_files:
            error.related_files = context.related_files
        if context.debug_payload and not error.debug_payload:
            error.debug_payload = context.debug_payload
        return error

    # Create new error with context
    return error_class(
        message=str(error) or type(error).__name__,
        code=context.error_code,
        file_path=context.file_path,
        line_number=context.line_number,
        suggestion=context.suggestion,
        original_error=context.original_error or error,
        build_phase=context.build_phase,
        severity=context.severity,
        related_files=context.related_files,
        debug_payload=context.debug_payload,
    )


def get_context_from_exception(error: Exception) -> ErrorContext:
    """
    Extract error context from an exception if available.

    Attempts to extract file_path, line_number, and other context
    from various exception types.

    Args:
        error: Exception to extract context from

    Returns:
        ErrorContext with any available information
    """
    context = ErrorContext()

    # Try to extract from BengalError
    if hasattr(error, "file_path"):
        context.file_path = getattr(error, "file_path", None)
    if hasattr(error, "line_number"):
        context.line_number = getattr(error, "line_number", None)
    if hasattr(error, "suggestion"):
        context.suggestion = getattr(error, "suggestion", None)
    if hasattr(error, "original_error"):
        context.original_error = getattr(error, "original_error", None)
    if hasattr(error, "code"):
        context.error_code = getattr(error, "code", None)
    if hasattr(error, "build_phase"):
        context.build_phase = getattr(error, "build_phase", None)
    if hasattr(error, "severity"):
        context.severity = getattr(error, "severity", ErrorSeverity.ERROR)
    if hasattr(error, "related_files"):
        context.related_files = getattr(error, "related_files", [])
    if hasattr(error, "debug_payload"):
        context.debug_payload = getattr(error, "debug_payload", None)

    # Try to extract from common exception types
    if hasattr(error, "filename"):
        # FileNotFoundError, OSError, etc.
        filename = getattr(error, "filename", None)
        if filename:
            with contextlib.suppress(TypeError, ValueError):
                context.file_path = Path(filename)

    if hasattr(error, "lineno"):
        # SyntaxError, TemplateSyntaxError, etc.
        context.line_number = getattr(error, "lineno", None)

    return context


def create_rendering_context(
    page_path: Path | str,
    template_name: str,
    *,
    template_line: int | None = None,
    context_vars: list[str] | None = None,
) -> ErrorContext:
    """
    Create an ErrorContext for rendering errors.

    Convenience function for the common case of rendering errors.

    Args:
        page_path: Path to the page being rendered
        template_name: Name of the template being used
        template_line: Line number in template where error occurred
        context_vars: Template context variable names available

    Returns:
        Pre-configured ErrorContext for rendering
    """
    context = ErrorContext(
        file_path=Path(page_path) if isinstance(page_path, str) else page_path,
        build_phase=BuildPhase.RENDERING,
        subsystem="rendering",
        template_name=template_name,
        template_context_keys=context_vars or [],
    )
    context.add_related_file("template", template_name, template_line)

    # Add debug payload
    context.debug_payload = ErrorDebugPayload(
        processing_item=f"page:{page_path}",
        processing_type="page",
        template_name=template_name,
        template_line=template_line,
        available_context_vars=context_vars or [],
        files_to_check=[
            "bengal/rendering/template_context.py",
            "bengal/orchestration/render.py",
        ],
    )

    return context


def create_discovery_context(
    file_path: Path | str,
    operation: str,
) -> ErrorContext:
    """
    Create an ErrorContext for discovery errors.

    Args:
        file_path: Path to file being discovered
        operation: Operation being performed

    Returns:
        Pre-configured ErrorContext for discovery
    """
    return ErrorContext(
        file_path=Path(file_path) if isinstance(file_path, str) else file_path,
        operation=operation,
        build_phase=BuildPhase.DISCOVERY,
        subsystem="discovery",
        debug_payload=ErrorDebugPayload(
            processing_item=f"file:{file_path}",
            processing_type="file",
            files_to_check=[
                "bengal/discovery/",
                "bengal/content_layer/",
            ],
        ),
    )


def create_config_context(
    config_file: Path | str | None = None,
    config_key: str | None = None,
) -> ErrorContext:
    """
    Create an ErrorContext for config errors.

    Args:
        config_file: Path to config file
        config_key: Config key being accessed

    Returns:
        Pre-configured ErrorContext for config
    """
    context = ErrorContext(
        file_path=Path(config_file) if isinstance(config_file, str) else config_file,
        build_phase=BuildPhase.INITIALIZATION,
        subsystem="config",
    )
    if config_key:
        context.config_keys_accessed = [config_key]
    return context
