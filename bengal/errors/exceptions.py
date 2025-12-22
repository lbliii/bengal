"""
Base exception hierarchy for Bengal.

All Bengal-specific exceptions extend from ``BengalError`` or one of its
domain-specific subclasses. This provides consistent error context, codes,
and formatting throughout the Bengal codebase.

Exception Hierarchy
===================

::

    BengalError (base)
    ├── BengalConfigError      # C001-C008: Configuration errors
    ├── BengalContentError     # N001-N010: Content/frontmatter errors
    ├── BengalRenderingError   # R001-R010: Template rendering errors
    ├── BengalDiscoveryError   # D001-D007: Content discovery errors
    ├── BengalCacheError       # A001-A006: Cache errors
    ├── BengalServerError      # S001-S005: Dev server errors
    └── BengalAssetError       # X001-X006: Asset processing errors

Key Features
============

- **Error Codes**: Unique codes (e.g., ``ErrorCode.R001``) for searchability
  and documentation linking.
- **Build Phase**: Tracks which build phase the error occurred in for
  targeted investigation.
- **Related Files**: Lists files involved in the error (template, page, config).
- **Debug Payloads**: Machine-readable context for AI troubleshooting.
- **Investigation Helpers**: Generates grep patterns and test file suggestions.
- **Suggestions**: Actionable hints for fixing the error.

Usage
=====

Raise a basic Bengal error::

    from bengal.errors import BengalRenderingError, ErrorCode

    raise BengalRenderingError(
        "Template not found: single.html",
        code=ErrorCode.R001,
        file_path=template_path,
        suggestion="Check templates/ directory",
    )

Use investigation helpers::

    try:
        render_page(page)
    except BengalError as e:
        for cmd in e.get_investigation_commands():
            print(cmd)
        for test in e.get_related_test_files():
            print(test)

See Also
========

- ``bengal/errors/codes.py`` - Error code definitions
- ``bengal/errors/context.py`` - Context enrichment utilities
- ``bengal/errors/suggestions.py`` - Actionable suggestions
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.errors.codes import ErrorCode
    from bengal.errors.context import (
        BuildPhase,
        ErrorDebugPayload,
        ErrorSeverity,
        RelatedFile,
    )


class BengalError(Exception):
    """
    Base exception for all Bengal errors.

    Provides consistent context support including:
    - Error codes for searchability
    - File paths and line numbers
    - Build phase for investigation
    - Suggestions for fixes
    - Related files for debugging
    - Debug payloads for AI troubleshooting
    - Investigation helpers

    Example:
        from bengal.errors import BengalError, ErrorCode

        raise BengalError(
            "Invalid configuration",
            code=ErrorCode.C002,
            file_path=config_path,
            line_number=12,
            suggestion="Check the configuration documentation"
        )
    """

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode | None = None,
        file_path: Path | str | None = None,
        line_number: int | None = None,
        suggestion: str | None = None,
        original_error: Exception | None = None,
        build_phase: BuildPhase | None = None,
        severity: ErrorSeverity | None = None,
        related_files: list[RelatedFile] | None = None,
        debug_payload: ErrorDebugPayload | None = None,
    ) -> None:
        """
        Initialize Bengal error.

        Args:
            message: Human-readable error message
            code: Unique error code for searchability (e.g., ErrorCode.R001)
            file_path: Path to file where error occurred (Path or str)
            line_number: Line number where error occurred
            suggestion: Helpful suggestion for fixing the error
            original_error: Original exception that caused this error (for chaining)
            build_phase: Build phase where error occurred (for investigation)
            severity: Error severity classification
            related_files: Files related to this error for debugging
            debug_payload: Machine-readable debug context for AI troubleshooting
        """
        self.message = message
        self.code = code
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self.line_number = line_number
        self.suggestion = suggestion
        self.original_error = original_error
        self.build_phase = build_phase
        self.severity = severity
        self.related_files = related_files or []
        self.debug_payload = debug_payload
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context."""
        parts = []

        # Add error code prefix if available
        if self.code:
            parts.append(f"[{self.code.name}] {self.message}")
        else:
            parts.append(self.message)

        # Add location info
        if self.file_path:
            location = f"File: {self.file_path}"
            if self.line_number:
                location += f":{self.line_number}"
            parts.append(location)

        # Add build phase
        if self.build_phase:
            parts.append(f"Phase: {self.build_phase.value}")

        # Add suggestion
        if self.suggestion:
            parts.append(f"Tip: {self.suggestion}")

        # Add related files summary
        if self.related_files:
            related_summary = ", ".join(str(rf) for rf in self.related_files[:3])
            if len(self.related_files) > 3:
                related_summary += f" (+{len(self.related_files) - 3} more)"
            parts.append(f"Related: {related_summary}")

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the error
        """
        result: dict[str, Any] = {
            "type": self.__class__.__name__,
            "message": self.message,
            "code": str(self.code) if self.code else None,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
            "build_phase": self.build_phase.value if self.build_phase else None,
            "severity": self.severity.value if self.severity else None,
            "related_files": [str(rf) for rf in self.related_files],
        }
        if self.debug_payload:
            result["debug_payload"] = self.debug_payload.to_dict()
        return result

    def get_investigation_commands(self) -> list[str]:
        """
        Generate grep/search commands for investigating this error.

        Returns:
            List of shell commands that could help investigate the error
        """
        commands: list[str] = []

        # Search for error code usage
        if self.code:
            commands.append("# Search for error code handling")
            commands.append(f"grep -rn '{self.code.name}' bengal/")

        # Search for error type
        commands.append("# Search for exception type")
        commands.append(f"grep -rn '{self.__class__.__name__}' bengal/")

        # AttributeError specific suggestions
        if self.original_error and isinstance(self.original_error, AttributeError):
            msg = str(self.original_error)
            if "'dict'" in msg:
                commands.append("# Dict accessed as object - check template context")
                commands.append("grep -rn 'template_context' bengal/rendering/")
            if "has no attribute" in msg:
                # Extract the attribute name
                try:
                    attr = msg.split("'")[-2]
                    commands.append(f"# Search for attribute '{attr}'")
                    commands.append(f"grep -rn '\\.{attr}' bengal/")
                except (IndexError, ValueError):
                    pass

        # Template error specific suggestions
        if self.build_phase:
            from bengal.errors.context import BuildPhase

            if self.build_phase == BuildPhase.RENDERING:
                commands.append("# Check rendering pipeline")
                commands.append("grep -rn 'render_page\\|render_template' bengal/rendering/")

        # Show the problematic file
        if self.file_path:
            commands.append("# View the problematic file")
            if self.line_number:
                start = max(1, self.line_number - 5)
                end = self.line_number + 10
                commands.append(f"sed -n '{start},{end}p' {self.file_path}")
            else:
                commands.append(f"head -50 {self.file_path}")

        # Debug payload suggestions
        if self.debug_payload and self.debug_payload.grep_patterns:
            commands.append("# Suggested search patterns from debug payload")
            for pattern in self.debug_payload.grep_patterns:
                commands.append(f"grep -rn '{pattern}' bengal/")

        return commands

    def get_related_test_files(self) -> list[str]:
        """
        Suggest test files that might cover this error case.

        Returns:
            List of test file paths to investigate
        """
        test_mapping: dict[type, list[str]] = {
            BengalConfigError: [
                "tests/unit/config/",
                "tests/integration/test_config.py",
            ],
            BengalContentError: [
                "tests/unit/core/test_page.py",
                "tests/integration/test_content.py",
            ],
            BengalRenderingError: [
                "tests/unit/rendering/",
                "tests/integration/test_render.py",
            ],
            BengalDiscoveryError: [
                "tests/unit/discovery/",
                "tests/integration/test_discovery.py",
            ],
            BengalCacheError: [
                "tests/unit/cache/",
                "tests/integration/test_cache.py",
            ],
        }

        # Check error type hierarchy
        for error_type, tests in test_mapping.items():
            if isinstance(self, error_type):
                return tests

        # Debug payload may have specific test suggestions
        if self.debug_payload and self.debug_payload.test_files:
            return self.debug_payload.test_files

        # Default: search based on build phase
        if self.build_phase:
            from bengal.errors.context import BuildPhase

            phase_tests = {
                BuildPhase.RENDERING: ["tests/unit/rendering/", "tests/integration/test_render.py"],
                BuildPhase.DISCOVERY: [
                    "tests/unit/discovery/",
                    "tests/integration/test_discovery.py",
                ],
                BuildPhase.PARSING: [
                    "tests/unit/rendering/test_markdown.py",
                    "tests/unit/core/test_page.py",
                ],
                BuildPhase.CACHE: ["tests/unit/cache/"],
                BuildPhase.ASSET_PROCESSING: [
                    "tests/unit/assets/",
                    "tests/integration/test_assets.py",
                ],
                BuildPhase.SERVER: ["tests/unit/server/"],
            }
            return phase_tests.get(self.build_phase, [])

        return ["tests/"]

    def get_docs_url(self) -> str | None:
        """
        Get documentation URL for this error.

        Returns:
            URL to error documentation, or None
        """
        if self.code:
            return self.code.docs_url
        return None

    def add_related_file(
        self,
        role: str,
        path: Path | str,
        line_number: int | None = None,
    ) -> None:
        """
        Add a related file for debugging context.

        Args:
            role: What role this file plays (e.g., "template", "page")
            path: Path to the file
            line_number: Optional line number of interest
        """
        from bengal.errors.context import RelatedFile

        self.related_files.append(RelatedFile(role=role, path=path, line_number=line_number))


class BengalConfigError(BengalError):
    """
    Configuration-related errors.

    Raised for issues with site configuration loading, validation, or access.
    Automatically sets build phase to INITIALIZATION.

    Common Error Codes:
        - C001: YAML parse error in config file
        - C002: Required config key missing
        - C003: Invalid config value
        - C004: Type mismatch in config
        - C005: Defaults directory missing
        - C006: Unknown environment
        - C007: Circular reference in config
        - C008: Deprecated config key

    Example:
        >>> raise BengalConfigError(
        ...     "Missing required key: site.title",
        ...     code=ErrorCode.C002,
        ...     file_path=Path("config/_default/site.yaml"),
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        # Set default build phase if not provided
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.INITIALIZATION
        super().__init__(message, **kwargs)


class BengalContentError(BengalError):
    """
    Content-related errors (frontmatter, markdown, taxonomy).

    Raised for issues with content files including frontmatter parsing,
    markdown processing, and content validation. Automatically sets
    build phase to PARSING.

    Common Error Codes:
        - N001: Invalid frontmatter YAML
        - N002: Invalid date format
        - N003: File encoding error
        - N004: Content file not found
        - N005: Markdown parsing error
        - N006: Shortcode error
        - N007: TOC extraction error
        - N008: Invalid taxonomy
        - N009: Invalid weight value
        - N010: Invalid slug

    Example:
        >>> raise BengalContentError(
        ...     "Invalid date format: 'yesterday'",
        ...     code=ErrorCode.N002,
        ...     file_path=Path("content/post.md"),
        ...     line_number=3,
        ...     suggestion="Use ISO format: YYYY-MM-DD",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.PARSING
        super().__init__(message, **kwargs)


class BengalRenderingError(BengalError):
    """
    Rendering-related errors (templates, shortcodes, output).

    Raised for issues during template rendering including template
    not found, syntax errors, undefined variables, and filter errors.
    Automatically sets build phase to RENDERING.

    Common Error Codes:
        - R001: Template not found
        - R002: Template syntax error
        - R003: Undefined template variable
        - R004: Filter error
        - R005: Include error
        - R006: Macro error
        - R007: Block error
        - R008: Context error
        - R009: Template inheritance error
        - R010: Output write error

    Example:
        >>> raise BengalRenderingError(
        ...     "Template not found: layouts/custom.html",
        ...     code=ErrorCode.R001,
        ...     file_path=Path("content/post.md"),
        ...     suggestion="Check templates/ and themes/*/templates/",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.RENDERING
        super().__init__(message, **kwargs)


class BengalDiscoveryError(BengalError):
    """
    Content discovery errors.

    Raised for issues finding and organizing content files and sections.
    Automatically sets build phase to DISCOVERY.

    Common Error Codes:
        - D001: Content directory not found
        - D002: Invalid content path
        - D003: Section index missing
        - D004: Circular section reference
        - D005: Duplicate page path
        - D006: Invalid file pattern
        - D007: Permission denied

    Example:
        >>> raise BengalDiscoveryError(
        ...     "Content directory not found: content/",
        ...     code=ErrorCode.D001,
        ...     suggestion="Run 'bengal init' to create site structure",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.DISCOVERY
        super().__init__(message, **kwargs)


class BengalCacheError(BengalError):
    """
    Cache-related errors.

    Raised for issues with the build cache including corruption,
    version mismatches, and I/O errors. Automatically sets build
    phase to CACHE.

    Common Error Codes:
        - A001: Cache corruption detected
        - A002: Cache version mismatch
        - A003: Cache read error
        - A004: Cache write error
        - A005: Cache invalidation error
        - A006: Cache lock timeout

    Example:
        >>> raise BengalCacheError(
        ...     "Cache corruption detected",
        ...     code=ErrorCode.A001,
        ...     suggestion="Clear cache: rm -rf .bengal/cache/",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.CACHE
        super().__init__(message, **kwargs)


class BengalServerError(BengalError):
    """
    Development server errors.

    Raised for issues with the Bengal development server including
    port conflicts, binding errors, and WebSocket issues. Automatically
    sets build phase to SERVER.

    Common Error Codes:
        - S001: Port already in use
        - S002: Server bind error
        - S003: Hot reload error
        - S004: WebSocket error
        - S005: Static file serving error

    Example:
        >>> raise BengalServerError(
        ...     "Port 1313 already in use",
        ...     code=ErrorCode.S001,
        ...     suggestion="Use --port 8080 or kill the existing process",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.SERVER
        super().__init__(message, **kwargs)


class BengalAssetError(BengalError):
    """
    Asset processing errors.

    Raised for issues with static asset processing including missing
    files, invalid paths, and processing failures. Automatically sets
    build phase to ASSET_PROCESSING.

    Common Error Codes:
        - X001: Asset not found
        - X002: Invalid asset path
        - X003: Asset processing failed
        - X004: Asset copy error
        - X005: Asset fingerprint error
        - X006: Asset minification error

    Example:
        >>> raise BengalAssetError(
        ...     "Asset not found: images/logo.png",
        ...     code=ErrorCode.X001,
        ...     suggestion="Check assets/ and static/ directories",
        ... )
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.ASSET_PROCESSING
        super().__init__(message, **kwargs)
