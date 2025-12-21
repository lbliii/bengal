"""
Base exception hierarchy for Bengal.

All Bengal-specific exceptions should extend from BengalError or one of its
subclasses to provide consistent error context, codes, and formatting.

Key Features:
- Unique error codes (ErrorCode) for searchability
- Build phase tracking for investigation
- Related files for debugging context
- Debug payloads for AI troubleshooting
- Investigation helpers (grep patterns, test files)
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

    Common codes: C001-C008
    Build phase: INITIALIZATION
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        # Set default build phase if not provided
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.INITIALIZATION
        super().__init__(message, **kwargs)


class BengalContentError(BengalError):
    """
    Content-related errors (frontmatter, markdown, etc.).

    Common codes: N001-N010
    Build phase: PARSING
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.PARSING
        super().__init__(message, **kwargs)


class BengalRenderingError(BengalError):
    """
    Rendering-related errors (templates, shortcodes, etc.).

    Common codes: R001-R010
    Build phase: RENDERING
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.RENDERING
        super().__init__(message, **kwargs)


class BengalDiscoveryError(BengalError):
    """
    Content discovery errors.

    Common codes: D001-D007
    Build phase: DISCOVERY
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.DISCOVERY
        super().__init__(message, **kwargs)


class BengalCacheError(BengalError):
    """
    Cache-related errors.

    Common codes: A001-A006
    Build phase: CACHE
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.CACHE
        super().__init__(message, **kwargs)


class BengalServerError(BengalError):
    """
    Development server errors.

    Common codes: S001-S005
    Build phase: SERVER
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.SERVER
        super().__init__(message, **kwargs)


class BengalAssetError(BengalError):
    """
    Asset processing errors.

    Common codes: X001-X006
    Build phase: ASSET_PROCESSING
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        if "build_phase" not in kwargs:
            from bengal.errors.context import BuildPhase

            kwargs["build_phase"] = BuildPhase.ASSET_PROCESSING
        super().__init__(message, **kwargs)
