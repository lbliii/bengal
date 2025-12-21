"""
Shortcode/Directive Sandbox for isolated testing.

Test directives and shortcodes in isolation without building an entire site.
Validates syntax, shows rendered output, and identifies errors before they
appear in production builds.

Example usage:

```python
sandbox = ShortcodeSandbox()
result = sandbox.render('''
```{note}
This is a test note.
```
''')
print(result.html)
```
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
    """Result of rendering a shortcode/directive."""

    input_content: str
    html: str
    success: bool
    directive_name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    render_time_ms: float = 0.0

    def format_summary(self) -> str:
        """Format a summary of the render result."""
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
    """Result of syntax validation."""

    content: str
    valid: bool
    directive_name: str | None = None
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class ShortcodeSandbox(DebugTool):
    """
    Sandbox for testing shortcodes/directives in isolation.

    Provides:
    - Isolated rendering without site context
    - Syntax validation before render
    - Error detection and suggestions
    - Batch testing from files
    - Interactive REPL mode
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
        Initialize sandbox.

        Args:
            site: Optional site instance for full context (creates mock if None)
            mock_context: Optional mock context for variable substitution
        """
        self._site = site
        self._mock_context = mock_context or self._create_default_context()
        self._markdown_parser: Any = None
        self._known_directives: frozenset[str] | None = None

    def _create_default_context(self) -> dict[str, Any]:
        """Create default mock context for rendering."""
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
        """Get set of known directive names."""
        if self._known_directives is None:
            from bengal.directives import KNOWN_DIRECTIVE_NAMES

            self._known_directives = KNOWN_DIRECTIVE_NAMES
        return self._known_directives

    def _get_parser(self) -> Any:
        """Get or create markdown parser."""
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
        Run sandbox testing.

        Args:
            content: Markdown content to test
            file_path: Path to file containing content
            validate_only: Only validate syntax, don't render
            **kwargs: Additional arguments

        Returns:
            DebugReport with findings
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

        This is the abstract method required by DebugTool.
        For parameterized analysis, use run() instead.
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
        Validate directive/shortcode syntax.

        Args:
            content: Markdown content with directive

        Returns:
            ValidationResult with errors and suggestions
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
        """Find directives with similar names (typo detection)."""
        similar = []
        for known_name in known:
            distance = self._levenshtein_distance(name.lower(), known_name.lower())
            if distance <= max_distance:
                similar.append(known_name)
        return sorted(similar)[:3]  # Return top 3

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
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

        Args:
            content: Markdown content with directive

        Returns:
            RenderResult with HTML and timing info
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
        Test multiple shortcodes in batch.

        Args:
            test_cases: List of test cases with 'content' and optional 'expected'

        Returns:
            List of RenderResults
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

        Returns:
            List of directive info dicts
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

        Args:
            name: Directive name

        Returns:
            Help text or None if not found
        """
        from bengal.directives import DIRECTIVE_CLASSES

        for cls in DIRECTIVE_CLASSES:
            names = getattr(cls, "DIRECTIVE_NAMES", [])
            if name in names:
                return cls.__doc__

        return None
