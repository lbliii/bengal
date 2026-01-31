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
├── BengalAssetError       # X001-X006: Asset processing errors
└── BengalGraphError       # G001-G005: Graph analysis errors

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
                "tests/unit/collections/",
                "tests/unit/core/test_page.py",
                "tests/integration/test_content.py",
            ],
            BengalRenderingError: [
                "tests/unit/rendering/",
                "tests/integration/test_render.py",
            ],
            BengalDiscoveryError: [
                "tests/unit/discovery/",
                "tests/unit/content_layer/",
                "tests/integration/test_discovery.py",
            ],
            BengalCacheError: [
                "tests/unit/cache/",
                "tests/integration/test_cache.py",
            ],
            BengalAssetError: [
                "tests/unit/assets/",
                "tests/unit/health/validators/test_fonts.py",
                "tests/integration/test_assets.py",
            ],
            BengalGraphError: [
                "tests/unit/analysis/",
            ],
            BengalParsingError: [
                "tests/unit/rendering/test_markdown.py",
                "tests/unit/core/test_page.py",
                "tests/unit/config/",
            ],
            BengalAutodocError: [
                "tests/unit/autodoc/",
                "tests/integration/test_autodoc.py",
            ],
            BengalValidatorError: [
                "tests/unit/health/",
                "tests/integration/test_health.py",
            ],
            BengalBuildError: [
                "tests/unit/orchestration/",
                "tests/integration/test_build.py",
            ],
            BengalTemplateFunctionError: [
                "tests/unit/rendering/",
                "tests/unit/rendering/test_shortcodes.py",
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


class DirectiveContractError(BengalContentError):
    """
    Directive nesting contract violation error.

    Raised when a directive nesting contract is violated in strict mode.
    This is a subclass of BengalContentError since it occurs during parsing.

    Example:
            >>> raise DirectiveContractError(
            ...     "'step' must be inside 'steps'",
            ...     file_path=Path("content/guide.md"),
            ...     line_number=45,
            ... )

    """

    def __init__(
        self,
        message: str,
        *,
        location=None,
        **kwargs: Any,
    ) -> None:
        """Initialize directive contract error.

        Args:
            message: Human-readable error message
            location: Optional SourceLocation for error context
            **kwargs: Additional arguments passed to BengalContentError
        """
        # Convert location to file_path/line_number if provided
        if location and hasattr(location, "file_path"):
            if "file_path" not in kwargs:
                kwargs["file_path"] = location.file_path
            if "line_number" not in kwargs and hasattr(location, "line_number"):
                kwargs["line_number"] = location.line_number

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


class BengalGraphError(BengalError):
    """
    Graph analysis errors.

    Raised for issues with knowledge graph construction and analysis
    including unbuilt graphs, invalid parameters, and analysis failures.
    Automatically sets build phase to ANALYSIS.

    Common Error Codes:
        - G001: Graph not built yet
        - G002: Invalid parameter for analysis
        - G003: Cycle detected in graph
        - G004: Disconnected component found
        - G005: Analysis operation failed

    Example:
            >>> raise BengalGraphError(
            ...     "Graph not built. Call build() first.",
            ...     code=ErrorCode.G001,
            ...     suggestion="Call build() before accessing graph data",
            ... )

    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.ANALYSIS
        super().__init__(message, **kwargs)


class BengalParsingError(BengalError):
    """
    Parsing errors for YAML, JSON, TOML, or Markdown.

    Raised for issues during file parsing operations. Automatically sets
    build phase to PARSING.

    Common Error Codes:
        - P001: YAML parse error
        - P002: JSON parse error
        - P003: TOML parse error
        - P004: Markdown parse error
        - P005: Frontmatter delimiter missing
        - P006: Glossary parse error

    Example:
            >>> raise BengalParsingError(
            ...     "Invalid YAML syntax at line 5",
            ...     code=ErrorCode.P001,
            ...     file_path=Path("config/site.yaml"),
            ...     line_number=5,
            ...     suggestion="Check for missing colons or invalid indentation",
            ... )

    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.PARSING
        super().__init__(message, **kwargs)


class BengalAutodocError(BengalError):
    """
    Autodoc extraction errors.

    Raised for issues during autodoc extraction and generation.
    Automatically sets build phase to DISCOVERY.

    Common Error Codes:
        - O001: Autodoc extraction failed
        - O002: Python syntax error in source
        - O003: OpenAPI YAML/JSON parse failure
        - O004: CLI app import/load failure
        - O005: Invalid source path/location
        - O006: Extraction produced no elements

    Example:
            >>> raise BengalAutodocError(
            ...     "Failed to extract docstrings from module",
            ...     code=ErrorCode.O001,
            ...     file_path=Path("src/mymodule.py"),
            ...     suggestion="Check if the source module is importable",
            ... )

    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.DISCOVERY
        super().__init__(message, **kwargs)


class BengalValidatorError(BengalError):
    """
    Validator and health check errors.

    Raised for issues during health checks and validation operations.
    Automatically sets build phase to ANALYSIS.

    Common Error Codes:
        - V001: Validator crashed
        - V002: Health check failed
        - V003: Autofix failed
        - V004: Linkcheck timeout
        - V005: Linkcheck network error
        - V006: Graph analysis failed in health

    Example:
            >>> raise BengalValidatorError(
            ...     "Link check timed out after 30 seconds",
            ...     code=ErrorCode.V004,
            ...     suggestion="Increase timeout or check network connectivity",
            ... )

    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.ANALYSIS
        super().__init__(message, **kwargs)


class BengalBuildError(BengalError):
    """
    Build orchestration errors.

    Raised for issues during build orchestration and post-processing.
    Automatically sets build phase to POSTPROCESSING.

    Common Error Codes:
        - B001: Build phase failed
        - B002: Parallel processing failure
        - B003: Incremental build detection/cache failure
        - B004: Menu building failure
        - B005: Taxonomy collection failure
        - B006: Taxonomy page generation failure
        - B007: Asset processing failure
        - B008: Post-processing task failure
        - B009: Section finalization failure
        - B010: Cache/tracker initialization failure

    Example:
            >>> raise BengalBuildError(
            ...     "Post-processing task 'minify' failed",
            ...     code=ErrorCode.B008,
            ...     suggestion="Check post-processor configuration",
            ... )

    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.POSTPROCESSING
        super().__init__(message, **kwargs)


class BengalTemplateFunctionError(BengalRenderingError):
    """
    Template function, shortcode, and directive errors.

    Raised for issues with shortcodes, directives, and other template
    functions. Inherits from BengalRenderingError (BuildPhase.RENDERING).

    Common Error Codes:
        - T001: Shortcode not found
        - T002: Shortcode argument error
        - T003: Shortcode render error
        - T004: Directive not found
        - T005: Directive argument error
        - T006: Directive since empty
        - T007: Directive deprecated empty
        - T008: Directive changed empty
        - T009: Directive include not found
        - T010: Icon not found

    Example:
            >>> raise BengalTemplateFunctionError(
            ...     "Directive 'since' requires version argument",
            ...     code=ErrorCode.T006,
            ...     file_path=Path("content/docs/api.md"),
            ...     line_number=45,
            ...     suggestion="Add version: ```{since} 1.0.0```",
            ... )

    """
