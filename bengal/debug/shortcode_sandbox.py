"""
Shortcode/directive sandbox for isolated testing.

Provides validation, rendering, and batch testing of MyST directives
without requiring a full site context. Useful for quick iteration
on directive syntax.

Example:
    >>> sandbox = ShortcodeSandbox()
    >>> result = sandbox.render('```{note}\nTest note.\n```')
    >>> print(result.html)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bengal.debug.base import DebugReport, DebugTool, Severity
from bengal.debug.utils import find_similar_strings

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result of validating directive syntax."""

    content: str
    valid: bool
    directive_name: str | None = None
    errors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class RenderResult:
    """Result of rendering a directive."""

    input_content: str
    html: str
    success: bool
    directive_name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    render_time_ms: float = 0.0

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        lines: list[str] = []
        if self.success:
            name_part = f" ({self.directive_name})" if self.directive_name else ""
            lines.append(f"Success{name_part}")
            lines.append(f"  Parse: {self.parse_time_ms:.2f}ms")
            lines.append(f"  Render: {self.render_time_ms:.2f}ms")
        else:
            lines.append("Failed")
            lines.extend(f"  Error: {err}" for err in self.errors)
            lines.extend(f"  Warning: {warn}" for warn in self.warnings)
        return "\n".join(lines)


# Regex to detect ``` {name} directive fences
_DIRECTIVE_PATTERN = re.compile(r"^```\{(\w[\w-]*)\}", re.MULTILINE)
_CLOSING_FENCE = re.compile(r"^```\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Sandbox implementation
# ---------------------------------------------------------------------------


class ShortcodeSandbox(DebugTool):
    """Test directives in isolation without a full site context.

    Supports:
    - Syntax validation with typo detection
    - Rendering via the Patitas markdown parser
    - Batch testing of multiple snippets
    - Listing available directives with metadata
    """

    name = "sandbox"
    description = "Test directives in isolation"

    def __init__(
        self,
        site: Any = None,
        cache: Any = None,
        root_path: Path | None = None,
        mock_context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(site=site, cache=cache, root_path=root_path)
        self._mock_context = mock_context or {
            "page": {"title": "Test Page", "url": "/test/"},
            "site": {"title": "Test Site", "baseurl": "http://localhost:8000"},
        }
        self._registry = None  # lazy

    # -- Registry access ----------------------------------------------------

    def _get_registry(self):
        """Lazy-load the directive registry."""
        if self._registry is None:
            from bengal.parsing.backends.patitas.directives.registry import (
                create_default_registry,
            )

            self._registry = create_default_registry()
        return self._registry

    def _get_known_directives(self) -> frozenset[str]:
        """Return all registered directive names."""
        return self._get_registry().names

    # -- Public API ---------------------------------------------------------

    def list_directives(self) -> list[dict[str, Any]]:
        """List available directives with metadata.

        Returns:
            List of dicts with keys: names, description, class.
        """
        registry = self._get_registry()
        result: list[dict[str, Any]] = []
        seen: set[int] = set()
        for handler in registry.handlers:
            hid = id(handler)
            if hid in seen:
                continue
            seen.add(hid)
            result.append(
                {
                    "names": list(handler.names),
                    "description": getattr(handler, "description", None)
                    or handler.__class__.__doc__
                    or "",
                    "class": handler.__class__.__name__,
                }
            )
        return result

    def get_directive_help(self, name: str) -> str | None:
        """Get detailed help text for a directive.

        Args:
            name: Directive name (e.g. "note", "tabs").

        Returns:
            Help string or None if directive not found.
        """
        handler = self._get_registry().get(name)
        if handler is None:
            return None

        lines: list[str] = []
        lines.append(f"Directive: {name}")
        lines.append(f"  Aliases: {', '.join(handler.names)}")
        doc = getattr(handler, "description", None) or handler.__class__.__doc__
        if doc:
            lines.append(f"  Description: {doc.strip()}")
        lines.append(f"  Token type: {handler.token_type}")
        lines.append(f"  Class: {handler.__class__.__name__}")
        return "\n".join(lines)

    def validate(self, content: str) -> ValidationResult:
        """Validate directive syntax without rendering.

        Checks:
        - Directive fence is present
        - Directive name is known (with typo suggestions)
        - Closing fence exists
        """
        known = self._get_known_directives()

        m = _DIRECTIVE_PATTERN.search(content)
        if m is None:
            return ValidationResult(
                content=content,
                valid=True,
                directive_name=None,
                suggestions=["Content does not contain a directive. Use ```{name} syntax."],
            )

        name = m.group(1)
        errors: list[str] = []
        suggestions: list[str] = []

        # Check name
        if name not in known:
            errors.append(f"Unknown directive: {name}")
            similar = find_similar_strings(name, known)
            if similar:
                suggestions.append(f"Did you mean: {', '.join(similar)}?")

        # Check closing fence
        after_open = content[m.end() :]
        if not _CLOSING_FENCE.search(after_open):
            errors.append("Missing closing fence (```)")

        return ValidationResult(
            content=content,
            valid=len(errors) == 0,
            directive_name=name,
            errors=errors,
            suggestions=suggestions,
        )

    def render(self, content: str) -> RenderResult:
        """Render a directive and return the HTML.

        Uses the Patitas markdown parser for rendering.
        """
        # Detect directive name
        m = _DIRECTIVE_PATTERN.search(content)
        directive_name = m.group(1) if m else None

        # Validate first
        validation = self.validate(content)
        if not validation.valid:
            return RenderResult(
                input_content=content,
                html="",
                success=False,
                directive_name=directive_name,
                errors=validation.errors,
            )

        # Parse + render (PatitasParser.parse returns HTML directly)
        parse_start = time.perf_counter()
        try:
            from bengal.parsing.backends.patitas import PatitasParser

            parser = PatitasParser()
            html = parser.parse(content, metadata=self._mock_context)
            parse_ms = (time.perf_counter() - parse_start) * 1000
        except Exception as e:
            parse_ms = (time.perf_counter() - parse_start) * 1000
            return RenderResult(
                input_content=content,
                html="",
                success=False,
                directive_name=directive_name,
                errors=[f"Parse error: {e}"],
                parse_time_ms=parse_ms,
            )
        render_ms = 0.0

        return RenderResult(
            input_content=content,
            html=html,
            success=True,
            directive_name=directive_name,
            parse_time_ms=parse_ms,
            render_time_ms=render_ms,
        )

    def batch_test(self, test_cases: list[dict[str, Any]]) -> list[RenderResult]:
        """Run multiple render tests.

        Args:
            test_cases: List of dicts, each with at least a "content" key.
                Optional "expected" key for output substring matching.

        Returns:
            List of RenderResult, one per test case.
        """
        results: list[RenderResult] = []
        for case in test_cases:
            content = case.get("content", "")
            result = self.render(content)
            expected = case.get("expected")
            if expected and result.success and expected not in result.html:
                result.warnings.append(f"Expected '{expected}' not found in output")
            results.append(result)
        return results

    # -- DebugTool interface ------------------------------------------------

    def analyze(self) -> DebugReport:
        """Not typically used directly — use run() with content/file_path."""
        return self.create_report()

    def run(
        self,
        content: str | None = None,
        file_path: Path | None = None,
        validate_only: bool = False,
        **kwargs: Any,
    ) -> DebugReport:
        """Run sandbox analysis on content or file.

        Args:
            content: Directive content string.
            file_path: Path to file containing directive.
            validate_only: If True, only validate syntax (no render).
        """
        report = self.create_report()

        # Load content from file if needed
        if file_path is not None:
            if not file_path.exists():
                report.add_finding(
                    title="File not found",
                    description=f"File not found: {file_path}",
                    severity=Severity.ERROR,
                )
                return report
            content = file_path.read_text(encoding="utf-8")

        if content is None:
            report.add_finding(
                title="No content",
                description="No content or file provided",
                severity=Severity.WARNING,
            )
            return report

        # Handle escaped newlines from CLI
        content = content.replace("\\n", "\n")

        if validate_only:
            validation = self.validate(content)
            if validation.valid:
                report.add_finding(
                    title="Valid syntax",
                    description=f"Directive '{validation.directive_name}' has valid syntax",
                    severity=Severity.INFO,
                    category="validation",
                )
            else:
                for err in validation.errors:
                    report.add_finding(
                        title="Validation error",
                        description=err,
                        severity=Severity.ERROR,
                        category="validation",
                    )
                for sug in validation.suggestions:
                    report.add_finding(
                        title="Suggestion",
                        description=sug,
                        severity=Severity.INFO,
                        category="suggestion",
                    )
        else:
            result = self.render(content)
            if result.success:
                report.add_finding(
                    title="Render successful",
                    description=f"Directive '{result.directive_name}' rendered ({result.parse_time_ms:.1f}ms parse, {result.render_time_ms:.1f}ms render)",
                    severity=Severity.INFO,
                    category="render",
                    metadata={"html": result.html},
                )
            else:
                for err in result.errors:
                    report.add_finding(
                        title="Render failed",
                        description=err,
                        severity=Severity.ERROR,
                        category="render",
                    )

        report.summary = f"Analyzed {len(report.findings)} finding(s)"
        return report
