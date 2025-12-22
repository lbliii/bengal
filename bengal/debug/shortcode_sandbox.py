"""
Shortcode/Directive Sandbox for isolated testing.

Test MyST directives and shortcodes in isolation without building an entire
site. Validates syntax, renders to HTML, detects errors, and suggests fixes
before issues appear in production builds.

This module provides a safe environment to experiment with directive syntax,
verify rendering output, and debug directive issues without the overhead of
a full site build.

Key Components:
    - ShortcodeSandbox: Main tool for isolated directive testing.
    - RenderResult: Output from rendering a directive.
    - ValidationResult: Syntax validation feedback.

Example usage:
    >>> from bengal.debug.shortcode_sandbox import ShortcodeSandbox
    >>> sandbox = ShortcodeSandbox()
    >>> result = sandbox.render('''
    ... ```{note}
    ... This is a test note.
    ... ```
    ... ''')
    >>> if result.success:
    ...     print(result.html)
    ... else:
    ...     for error in result.errors:
    ...         print(f"Error: {error}")

See Also:
    - bengal.directives: Directive implementations.
    - bengal.rendering.parsers: Markdown parser configuration.
    - bengal.cli.commands.debug: CLI interface for sandbox.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bengal.debug.base import DebugReport, DebugTool, Severity
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RenderResult:
    """
    Result of rendering a shortcode/directive to HTML.

    Contains the rendered output, timing information, and any errors
    or warnings encountered during parsing and rendering.

    Attributes:
        input_content: Original Markdown content that was rendered.
        html: Rendered HTML output (empty string if failed).
        success: Whether rendering completed without errors.
        directive_name: Detected directive name (e.g., "note", "warning").
        errors: List of error messages from parsing/rendering.
        warnings: List of warning messages (non-fatal issues).
        parse_time_ms: Time spent parsing markdown (milliseconds).
        render_time_ms: Time spent rendering to HTML (milliseconds).

    Example:
        >>> result = sandbox.render("```{note}\nHello\n```")
        >>> if result.success:
        ...     print(f"Rendered in {result.render_time_ms:.1f}ms")
        ...     print(result.html)
        ... else:
        ...     for err in result.errors:
        ...         print(f"Error: {err}")
    """

    input_content: str
    html: str
    success: bool
    directive_name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    render_time_ms: float = 0.0

    def format_summary(self) -> str:
        """
        Format human-readable summary of the render result.

        Returns:
            Multi-line summary with status, timing, and any issues.
        """
        lines = []
        status = "✅ Success" if self.success else "❌ Failed"
        lines.append(f"Status: {status}")

        if self.directive_name:
            lines.append(f"Directive: {self.directive_name}")

        lines.append(f"Parse time: {self.parse_time_ms:.2f}ms")
        lines.append(f"Render time: {self.render_time_ms:.2f}ms")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  - {err}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  - {warn}")

        return "\n".join(lines)


@dataclass
class ValidationResult:
    """
    Result of directive/shortcode syntax validation.

    Provides feedback on whether the syntax is valid, identifies the
    directive being used, and offers suggestions for fixing issues.

    Attributes:
        content: Original content that was validated.
        valid: Whether the syntax is valid.
        directive_name: Detected directive name, or None if unrecognized.
        errors: Specific syntax errors found.
        suggestions: Helpful suggestions for fixing issues or typos.

    Example:
        >>> result = sandbox.validate("```{notee}\nText\n```")
        >>> if not result.valid:
        ...     print(f"Invalid: {result.errors}")
        ...     print(f"Did you mean: {result.suggestions}")
    """

    content: str
    valid: bool
    directive_name: str | None = None
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ShortcodeSandbox(DebugTool):
    """
    Sandbox for testing shortcodes/directives in isolation.

    Provides a safe environment to test MyST directive syntax and rendering
    without requiring a full site context. Useful for debugging directive
    issues, experimenting with syntax, and validating custom directives.

    Capabilities:
        - **Isolated Rendering**: Render directives without building a site.
        - **Syntax Validation**: Check directive syntax before rendering.
        - **Error Detection**: Identify parse/render errors with suggestions.
        - **Typo Detection**: Suggest similar directives for misspellings.
        - **Batch Testing**: Test multiple directives from a list.
        - **Directive Discovery**: List and document available directives.

    The sandbox uses a mock context for template variables, allowing
    directives that reference page/site data to render correctly.

    Attributes:
        name: Tool identifier ("sandbox").
        description: Brief tool description.
        DIRECTIVE_PATTERN_COLON: Regex for block directives (```{name}).
        DIRECTIVE_PATTERN_BRACE: Regex for inline directives ({name}).

    Example:
        >>> sandbox = ShortcodeSandbox()
        >>>
        >>> # Validate syntax first
        >>> validation = sandbox.validate("```{note}\nHello\n```")
        >>> if validation.valid:
        ...     result = sandbox.render(validation.content)
        ...     print(result.html)
        >>>
        >>> # List available directives
        >>> for d in sandbox.list_directives():
        ...     print(f"{d['names']}: {d['description']}")
        >>>
        >>> # Get help for specific directive
        >>> help_text = sandbox.get_directive_help("note")

    See Also:
        - :class:`RenderResult`: Rendering output structure.
        - :class:`ValidationResult`: Validation feedback structure.
        - :meth:`batch_test`: Test multiple directives at once.
    """

    name: str = "sandbox"
    description: str = "Test shortcodes/directives in isolation without building the site."

    # Known directive patterns for validation
    DIRECTIVE_PATTERN_COLON = r"^```\{(\w+[-\w]*)\}"  # ```{note}
    DIRECTIVE_PATTERN_BRACE = r"^\{(\w+[-\w]*)\}"  # {note} (inline)

    def __init__(
        self,
        site: Any = None,
        mock_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize sandbox environment.

        Creates a sandbox with optional site context or mock variables.
        If no site is provided, a default mock context is created for
        template variable substitution.

        Args:
            site: Optional Site instance for full context. If None, uses
                mock context for template variables.
            mock_context: Optional dictionary to use as mock context.
                Keys should include 'page' and 'site' with appropriate
                nested structures. Defaults to a sensible mock context.
        """
        self._site = site
        self._mock_context = mock_context or self._create_default_context()
        self._markdown_parser: Any = None
        self._known_directives: frozenset[str] | None = None

    def _create_default_context(self) -> dict[str, Any]:
        """
        Create default mock context for rendering.

        Provides sensible defaults for page and site variables that
        directives might reference during rendering.

        Returns:
            Dictionary with 'page' and 'site' mock data.
        """
        from datetime import datetime

        return {
            "page": {
                "title": "Test Page",
                "date": datetime.now().isoformat(),
                "metadata": {
                    "author": "Test Author",
                    "tags": ["test", "sandbox"],
                },
                "source_path": Path("test/page.md"),
            },
            "site": {
                "title": "Test Site",
                "baseurl": "https://example.com",
                "config": {
                    "theme": "default",
                },
            },
        }

    def _get_known_directives(self) -> frozenset[str]:
        """
        Get set of known directive names.

        Lazily loads and caches the set of all registered directive
        names from bengal.directives module.

        Returns:
            Frozen set of valid directive name strings.
        """
        if self._known_directives is None:
            from bengal.directives import KNOWN_DIRECTIVE_NAMES

            self._known_directives = KNOWN_DIRECTIVE_NAMES
        return self._known_directives

    def _get_parser(self) -> Any:
        """
        Get or create markdown parser.

        Lazily initializes the markdown parser with mistune engine
        and caches it for subsequent renders.

        Returns:
            Configured markdown parser instance.
        """
        if self._markdown_parser is None:
            from bengal.rendering.parsers import create_markdown_parser

            self._markdown_parser = create_markdown_parser(engine="mistune")
        return self._markdown_parser

    def run(
        self,
        content: str | None = None,
        file_path: Path | None = None,
        validate_only: bool = False,
        **kwargs: Any,
    ) -> DebugReport:
        """
        Run sandbox testing on directive content.

        Main entry point for testing directives. Validates syntax first,
        then optionally renders to HTML. Results are returned as a
        structured DebugReport with findings.

        Args:
            content: Markdown content containing directive to test.
            file_path: Path to file containing content (alternative to content).
            validate_only: If True, only validate syntax without rendering.
            **kwargs: Additional arguments (reserved for future use).

        Returns:
            DebugReport with validation/rendering findings. Check
            `report.metadata['html']` for rendered output on success.

        Example:
            >>> report = sandbox.run(content="```{note}\nTest\n```")
            >>> if report.has_errors:
            ...     print("Failed!")
            ... else:
            ...     print(report.metadata.get('html'))
        """
        report = DebugReport(tool_name=self.name)

        # Get content from file if path provided
        if file_path and not content:
            if not file_path.exists():
                report.add_finding(
                    title="File not found",
                    description=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                    location=str(file_path),
                )
                return report
            content = file_path.read_text()

        if not content:
            report.add_finding(
                title="No content provided",
                description="No content provided for testing",
                severity=Severity.WARNING,
            )
            return report

        # Validate first
        validation = self.validate(content)
        if not validation.valid:
            for error in validation.errors:
                report.add_finding(
                    title="Validation error",
                    description=error,
                    severity=Severity.ERROR,
                    metadata={"directive": validation.directive_name},
                )
            for suggestion in validation.suggestions:
                report.add_finding(
                    title="Suggestion",
                    description=suggestion,
                    severity=Severity.INFO,
                    metadata={"type": "suggestion"},
                )
            return report

        if validate_only:
            report.add_finding(
                title="Validation passed",
                description=f"Syntax valid for directive: {validation.directive_name or 'unknown'}",
                severity=Severity.INFO,
            )
            return report

        # Render content
        result = self.render(content)

        if result.success:
            report.add_finding(
                title="Render successful",
                description=f"Rendered successfully ({result.parse_time_ms + result.render_time_ms:.2f}ms)",
                severity=Severity.INFO,
                metadata={
                    "directive": result.directive_name,
                    "html_length": len(result.html),
                },
            )
            report.metadata["html"] = result.html
        else:
            for error in result.errors:
                report.add_finding(
                    title="Render error",
                    description=error,
                    severity=Severity.ERROR,
                )

        for warning in result.warnings:
            report.add_finding(
                title="Render warning",
                description=warning,
                severity=Severity.WARNING,
            )

        return report

    def analyze(self) -> DebugReport:
        """
        Perform analysis and return report.

        This is the abstract method required by DebugTool. For the sandbox,
        this method returns a helpful message directing users to use the
        run() method with content.

        For parameterized testing, use run(content=...) instead.

        Returns:
            DebugReport with usage guidance.
        """
        report = self.create_report()
        report.add_finding(
            title="No content provided",
            description="Use run() method with content or file_path parameter for testing",
            severity=Severity.INFO,
        )
        return report

    def validate(self, content: str) -> ValidationResult:
        """
        Validate directive/shortcode syntax without rendering.

        Checks that the directive syntax is well-formed and that the
        directive name is recognized. For unknown directives, suggests
        similar names to help fix typos.

        Args:
            content: Markdown content containing directive to validate.

        Returns:
            ValidationResult with:
            - valid: Whether syntax is correct
            - directive_name: Detected directive name
            - errors: List of syntax errors found
            - suggestions: Helpful tips for fixing issues

        Example:
            >>> validation = sandbox.validate("```{notee}\nTest\n```")
            >>> if not validation.valid:
            ...     print(f"Unknown directive: {validation.errors}")
            ...     print(f"Suggestions: {validation.suggestions}")
        """
        import re

        result = ValidationResult(content=content, valid=True)
        known = self._get_known_directives()

        # Check for directive patterns
        lines = content.strip().split("\n")
        first_line = lines[0] if lines else ""

        # Check colon-fence directive: ```{directive}
        colon_match = re.match(self.DIRECTIVE_PATTERN_COLON, first_line)
        if colon_match:
            directive_name = colon_match.group(1)
            result.directive_name = directive_name

            if directive_name not in known:
                result.valid = False
                result.errors.append(f"Unknown directive: {directive_name}")

                # Suggest similar directives
                suggestions = self._find_similar_directives(directive_name, known)
                if suggestions:
                    result.suggestions.append(f"Did you mean: {', '.join(suggestions)}?")

            # Check for closing fence
            if not content.strip().endswith("```"):
                result.valid = False
                result.errors.append("Missing closing fence (```)")
                result.suggestions.append("Add ``` at the end of the directive block")

            return result

        # Check inline directive: {directive}
        brace_match = re.match(self.DIRECTIVE_PATTERN_BRACE, first_line)
        if brace_match:
            directive_name = brace_match.group(1)
            result.directive_name = directive_name

            if directive_name not in known:
                result.valid = False
                result.errors.append(f"Unknown directive: {directive_name}")
                suggestions = self._find_similar_directives(directive_name, known)
                if suggestions:
                    result.suggestions.append(f"Did you mean: {', '.join(suggestions)}?")

            return result

        # No directive pattern found - might be regular markdown
        result.directive_name = None
        result.suggestions.append(
            "No directive pattern detected. Use ```{directive} for block directives."
        )

        return result

    def _find_similar_directives(
        self,
        name: str,
        known: frozenset[str],
        max_distance: int = 2,
    ) -> list[str]:
        """
        Find directives with similar names for typo detection.

        Uses Levenshtein distance to find directives within a certain
        edit distance of the given name.

        Args:
            name: Unknown directive name to find matches for.
            known: Set of known valid directive names.
            max_distance: Maximum Levenshtein distance (default 2).

        Returns:
            List of up to 3 similar directive names, sorted.
        """
        similar = []
        for known_name in known:
            distance = self._levenshtein_distance(name.lower(), known_name.lower())
            if distance <= max_distance:
                similar.append(known_name)
        return sorted(similar)[:3]  # Return top 3

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.

        The Levenshtein distance is the minimum number of single-character
        edits (insertions, deletions, substitutions) needed to transform
        one string into another.

        Args:
            s1: First string.
            s2: Second string.

        Returns:
            Integer edit distance (0 = identical strings).
        """
        if len(s1) < len(s2):
            return ShortcodeSandbox._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def render(self, content: str) -> RenderResult:
        """
        Render directive/shortcode content to HTML.

        Parses the markdown content, processes any directives, and
        renders to HTML. Includes timing information for profiling.

        Validates syntax first; if invalid, returns RenderResult with
        errors and success=False.

        Args:
            content: Markdown content containing directive(s) to render.

        Returns:
            RenderResult with:
            - html: Rendered HTML output (empty if failed)
            - success: Whether rendering completed successfully
            - parse_time_ms: Time spent parsing
            - render_time_ms: Time spent rendering
            - errors/warnings: Any issues encountered

        Example:
            >>> result = sandbox.render("```{warning}\nBe careful!\n```")
            >>> if result.success:
            ...     print(result.html)
            ...     print(f"Rendered in {result.render_time_ms:.1f}ms")
        """
        import time

        result = RenderResult(input_content=content, html="", success=False)

        # Validate first
        validation = self.validate(content)
        result.directive_name = validation.directive_name

        if not validation.valid:
            result.errors = validation.errors
            return result

        try:
            # Parse markdown
            start_parse = time.perf_counter()
            parser = self._get_parser()
            end_parse = time.perf_counter()
            result.parse_time_ms = (end_parse - start_parse) * 1000

            # Render to HTML
            start_render = time.perf_counter()
            html = parser.parse_with_context(
                content,
                metadata=self._mock_context.get("page", {}).get("metadata", {}),
                context=self._mock_context,
            )
            end_render = time.perf_counter()
            result.render_time_ms = (end_render - start_render) * 1000

            result.html = html
            result.success = True

        except Exception as e:
            result.errors.append(f"Render error: {e}")
            logger.error("sandbox_render_error", error=str(e), error_type=type(e).__name__)

        return result

    def batch_test(
        self,
        test_cases: list[dict[str, Any]],
    ) -> list[RenderResult]:
        """
        Test multiple shortcodes/directives in batch.

        Efficiently tests a list of directive snippets, optionally
        comparing output against expected strings.

        Args:
            test_cases: List of test case dictionaries, each containing:
                - 'content' (required): Markdown content to test
                - 'expected' (optional): String that should appear in output

        Returns:
            List of RenderResult objects, one per test case.
            If 'expected' was provided but not found in output,
            a warning is added to that result.

        Example:
            >>> cases = [
            ...     {'content': '```{note}\nA\n```'},
            ...     {'content': '```{warning}\nB\n```', 'expected': 'warning'},
            ... ]
            >>> results = sandbox.batch_test(cases)
            >>> for r in results:
            ...     print(f"{r.directive_name}: {'✓' if r.success else '✗'}")
        """
        results = []
        for case in test_cases:
            content = case.get("content", "")
            expected = case.get("expected")

            result = self.render(content)

            # Check expected output if provided
            if expected and result.success and expected not in result.html:
                result.warnings.append(f"Expected content not found in output: {expected[:50]}...")

            results.append(result)

        return results

    def list_directives(self) -> list[dict[str, str]]:
        """
        List all available directives with descriptions.

        Discovers all registered directive classes and extracts their
        names and documentation for display.

        Returns:
            List of dictionaries, each containing:
            - 'names': Comma-separated directive names
            - 'description': First line of directive docstring
            - 'class': Python class name implementing the directive

        Example:
            >>> for d in sandbox.list_directives():
            ...     print(f"{d['names']}: {d['description']}")
            note, tip: Create an admonition note.
            warning, caution: Create a warning admonition.
        """
        from bengal.directives import DIRECTIVE_CLASSES

        directives: list[dict[str, str]] = []
        for cls in DIRECTIVE_CLASSES:
            names = getattr(cls, "DIRECTIVE_NAMES", [])
            doc = cls.__doc__ or "No description"
            # Extract first line of docstring
            first_line = doc.strip().split("\n")[0]

            # Join names into a comma-separated string
            names_str = ", ".join(names) if names else "unknown"

            directives.append(
                {
                    "names": names_str,
                    "description": first_line,
                    "class": cls.__name__,
                }
            )

        return directives

    def get_directive_help(self, name: str) -> str | None:
        """
        Get detailed help for a specific directive.

        Looks up the directive class by name and returns its full
        docstring, which typically includes usage examples and
        available options.

        Args:
            name: Directive name (e.g., "note", "warning", "code-block").

        Returns:
            Full docstring of the directive class, or None if the
            directive name is not found.

        Example:
            >>> help_text = sandbox.get_directive_help("note")
            >>> if help_text:
            ...     print(help_text)
        """
        from bengal.directives import DIRECTIVE_CLASSES

        for cls in DIRECTIVE_CLASSES:
            names = getattr(cls, "DIRECTIVE_NAMES", [])
            if name in names:
                return cls.__doc__

        return None
