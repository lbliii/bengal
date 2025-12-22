"""Rich error reporting for directive parsing failures.

This module provides ``DirectiveError``, a specialized exception for directive
parsing failures that includes detailed context like file path, line number,
content snippets, and helpful suggestions.

Key Exports:
    - ``DirectiveError``: Exception class for directive parsing failures.
    - ``format_directive_error()``: Format error messages without raising.
    - ``get_suggestion()``: Get suggestions for common error types.
    - ``DIRECTIVE_SUGGESTIONS``: Dict of common error messages and fixes.

Example:
    Raise a directive error with full context::

        raise DirectiveError(
            directive_type="tabs",
            error_message="Tab markers require a space after colon",
            file_path=Path("content/guide.md"),
            line_number=42,
            content_snippet="### Tab:Python",
            suggestion="Use '### Tab: Python' (note the space)",
        )

See Also:
    - ``bengal.errors.BengalRenderingError``: Base error class.
"""

from __future__ import annotations

from pathlib import Path

from bengal.errors import BengalRenderingError


class DirectiveError(BengalRenderingError):
    """Rich error for directive parsing failures with detailed context.

    Provides enhanced error messages including:
        - Directive type that failed
        - File path and line number
        - Content snippet highlighting the problem
        - Helpful suggestions for fixing the issue

    Attributes:
        directive_type: Type of directive that failed (e.g., ``"tabs"``).
        error_message: Human-readable error description.
        content_snippet: Content snippet showing the problem area.

    Example:
        ::

            raise DirectiveError(
                directive_type="tabs",
                error_message="Tab markers require a space after colon",
                file_path=Path("content/guide.md"),
                line_number=42,
                content_snippet="### Tab:Python",
                suggestion="Use '### Tab: Python' (note the space)",
            )
    """

    def __init__(
        self,
        directive_type: str,
        error_message: str,
        file_path: Path | None = None,
        line_number: int | None = None,
        content_snippet: str | None = None,
        suggestion: str | None = None,
        *,
        original_error: Exception | None = None,
    ):
        """Initialize a directive error with context.

        Args:
            directive_type: Type of directive that failed (e.g., ``"tabs"``, ``"note"``).
            error_message: Human-readable error description.
            file_path: Path to the file containing the directive.
            line_number: Line number where the directive starts.
            content_snippet: Snippet of content showing the problem.
            suggestion: Helpful suggestion for fixing the issue.
            original_error: Original exception for chaining (keyword-only).
        """
        # Set base class fields
        super().__init__(
            message=error_message,
            file_path=file_path,
            line_number=line_number,
            suggestion=suggestion,
            original_error=original_error,
        )

        # Set directive-specific fields
        self.directive_type = directive_type
        self.error_message = error_message  # Keep for backward compatibility
        self.content_snippet = content_snippet

    def _format_error(self) -> str:
        """Format a rich error message with emoji indicators and context.

        Returns:
            Multi-line formatted error string with file location, error message,
            content snippet, and suggestion.
        """
        lines = []

        # Header with emoji
        lines.append(f"\n❌ Directive Error: {self.directive_type}")

        # Location info
        if self.file_path:
            location = str(self.file_path)
            if self.line_number:
                location += f":{self.line_number}"
            lines.append(f"   File: {location}")

        # Error message
        lines.append(f"   Error: {self.error_message}")

        # Content snippet
        if self.content_snippet:
            lines.append("\n   Context:")
            # Indent each line of the snippet
            for line in self.content_snippet.split("\n"):
                lines.append(f"   │ {line}")

        # Suggestion
        if self.suggestion:
            lines.append(f"\n   💡 Suggestion: {self.suggestion}")

        return "\n".join(lines)

    def display(self) -> str:
        """Return the formatted error message for display.

        Returns:
            Formatted error string identical to ``str(error)``.
        """
        return self._format_error()


def format_directive_error(
    directive_type: str,
    error_message: str,
    file_path: Path | None = None,
    line_number: int | None = None,
    content_lines: list[str] | None = None,
    error_line_offset: int = 0,
    suggestion: str | None = None,
) -> str:
    """Format a directive error message without raising an exception.

    Creates a rich error message string with file location, context lines,
    and optional suggestion. Use this when you want to format error output
    without raising ``DirectiveError``.

    Args:
        directive_type: Type of directive (e.g., ``"tabs"``).
        error_message: Human-readable error description.
        file_path: Path to the file containing the error.
        line_number: Line number where the directive starts.
        content_lines: Lines of content around the error for context.
        error_line_offset: Index in ``content_lines`` to mark as the error line.
        suggestion: Helpful suggestion for fixing the issue.

    Returns:
        Multi-line formatted error message with emoji indicators.

    Example:
        ::

            msg = format_directive_error(
                directive_type="tabs",
                error_message="Requires at least 2 tabs",
                file_path=Path("content/guide.md"),
                line_number=42,
                content_lines=[":::{tabs}", "### Tab: Only One", ":::"],
                error_line_offset=1,
                suggestion="Add another tab with ### Tab: Name",
            )
            print(msg)
    """
    lines = []

    # Header
    lines.append(f"\n❌ Directive Error: {{{directive_type}}}")

    # Location
    if file_path:
        location = str(file_path)
        if line_number:
            location += f":{line_number}"
        lines.append(f"   File: {location}")

    # Error message
    lines.append(f"   Error: {error_message}")

    # Content with highlighting
    if content_lines:
        lines.append("\n   Context:")
        for i, line in enumerate(content_lines):
            if i == error_line_offset:
                # Highlight error line
                lines.append(f"   │ {line}  ← ERROR")
            else:
                lines.append(f"   │ {line}")

    # Suggestion
    if suggestion:
        lines.append(f"\n   💡 Suggestion: {suggestion}")

    return "\n".join(lines)


# Common directive error messages and suggestions
DIRECTIVE_SUGGESTIONS: dict[str, str] = {
    "unknown_type": (
        "Check the directive name. Known directives: tabs, note, tip, warning, danger, "
        "error, info, example, success, caution, dropdown, details, code-tabs"
    ),
    "missing_closing": "Make sure your directive has closing colons (:::) on their own line",
    "malformed_tab_marker": "Tab markers should be: ### Tab: Title (note the space after colon)",
    "empty_tabs": "Tabs directive needs at least 2 tabs. Use ### Tab: Name to create tabs",
    "single_tab": "For single items, use an admonition (note, tip) instead of tabs",
    "empty_content": (
        "Directive content cannot be empty. Add markdown content between the opening "
        "and closing :::"
    ),
    "too_many_tabs": (
        "Consider splitting large tabs blocks into separate sections or pages. "
        "Each tab adds rendering overhead"
    ),
    "deep_nesting": (
        "Avoid nesting directives more than 3-4 levels deep. This impacts build performance"
    ),
}
"""Common directive error keys and their suggestion messages.

Keys:
    unknown_type: Unrecognized directive name.
    missing_closing: Directive not properly closed with ``:::``.
    malformed_tab_marker: Tab marker missing space after colon.
    empty_tabs: Tabs directive has no tabs.
    single_tab: Only one tab (use admonition instead).
    empty_content: Directive body is empty.
    too_many_tabs: Too many tabs may impact performance.
    deep_nesting: Directives nested too deeply.
"""


def get_suggestion(error_key: str) -> str | None:
    """Get a helpful suggestion for a common error type.

    Args:
        error_key: Key from ``DIRECTIVE_SUGGESTIONS`` (e.g., ``"empty_tabs"``).

    Returns:
        Suggestion string if key exists, ``None`` otherwise.

    Example:
        >>> get_suggestion("empty_tabs")
        'Tabs directive needs at least 2 tabs. Use ### Tab: Name to create tabs'
    """
    return DIRECTIVE_SUGGESTIONS.get(error_key)
