"""Exceptions for Kida template system."""

from __future__ import annotations

from typing import Any


class TemplateError(Exception):
    """Base exception for template errors."""

    pass


class TemplateNotFoundError(TemplateError):
    """Template not found."""

    pass


class TemplateSyntaxError(TemplateError):
    """Template syntax error."""

    def __init__(
        self,
        message: str,
        lineno: int | None = None,
        name: str | None = None,
        filename: str | None = None,
    ):
        self.message = message
        self.lineno = lineno
        self.name = name
        self.filename = filename
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        location = ""
        if self.filename:
            location = f" in {self.filename}"
        if self.lineno:
            location += f" at line {self.lineno}"
        return f"{self.message}{location}"


class TemplateRuntimeError(TemplateError):
    """Runtime error during template rendering with rich context.

    Provides detailed information about what went wrong, including:
    - The expression being evaluated
    - The actual values involved
    - Type information for debugging
    """

    def __init__(
        self,
        message: str,
        *,
        expression: str | None = None,
        values: dict[str, Any] | None = None,
        template_name: str | None = None,
        lineno: int | None = None,
        suggestion: str | None = None,
    ):
        self.message = message
        self.expression = expression
        self.values = values or {}
        self.template_name = template_name
        self.lineno = lineno
        self.suggestion = suggestion
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [f"Runtime Error: {self.message}"]

        # Location info
        if self.template_name or self.lineno:
            loc = self.template_name or "<template>"
            if self.lineno:
                loc += f":{self.lineno}"
            parts.append(f"  Location: {loc}")

        # Expression info
        if self.expression:
            parts.append(f"  Expression: {self.expression}")

        # Values with types
        if self.values:
            parts.append("  Values:")
            for name, value in self.values.items():
                type_name = type(value).__name__
                # Truncate long values
                value_repr = repr(value)
                if len(value_repr) > 80:
                    value_repr = value_repr[:77] + "..."
                parts.append(f"    {name} = {value_repr} ({type_name})")

        # Suggestion
        if self.suggestion:
            parts.append(f"\n  Suggestion: {self.suggestion}")

        return "\n".join(parts)


class RequiredValueError(TemplateRuntimeError):
    """A required value was None or missing."""

    def __init__(
        self,
        field_name: str,
        message: str | None = None,
        **kwargs: Any,
    ):
        self.field_name = field_name
        msg = message or f"Required value '{field_name}' is None or missing"
        super().__init__(
            msg,
            suggestion=f"Ensure '{field_name}' is set before this point, or use | default(fallback)",
            **kwargs,
        )


class NoneComparisonError(TemplateRuntimeError):
    """Attempted to compare None values (e.g., during sorting)."""

    def __init__(
        self,
        left_value: Any,
        right_value: Any,
        attribute: str | None = None,
        **kwargs: Any,
    ):
        left_type = type(left_value).__name__
        right_type = type(right_value).__name__

        msg = f"Cannot compare {left_type} with {right_type}"
        if attribute:
            msg += f" when sorting by '{attribute}'"

        values = {
            "left": left_value,
            "right": right_value,
        }

        suggestion = "Use | default(fallback) to provide a fallback for None values before sorting"
        if attribute:
            suggestion = (
                f"Ensure all items have '{attribute}' set, or filter out items with None values"
            )

        super().__init__(
            msg,
            values=values,
            suggestion=suggestion,
            **kwargs,
        )
