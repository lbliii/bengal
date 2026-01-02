"""Exceptions for Kida template system.

Exception Hierarchy:
    TemplateError (base)
    ├── TemplateNotFoundError     # Template not found by loader
    ├── TemplateSyntaxError       # Parse-time syntax error
    ├── TemplateRuntimeError      # Render-time error with context
    │   ├── RequiredValueError    # Required value was None/missing
    │   └── NoneComparisonError   # Attempted None comparison (sorting)
    └── UndefinedError            # Undefined variable access

Error Messages:
    All exceptions provide rich error messages with:
    - Source location (template name, line number)
    - Expression context where error occurred
    - Actual values and their types
    - Actionable suggestions for fixing

Example:
    ```
    UndefinedError: Undefined variable 'titl' in article.html:5
    Suggestion: Did you mean 'title'? Or use {{ titl | default('') }}
    ```
"""

from __future__ import annotations

from typing import Any


class TemplateError(Exception):
    """Base exception for all Kida template errors.

    All template-related exceptions inherit from this class, enabling
    broad exception handling:

    >>> try:
    ...     template.render()
    ... except TemplateError as e:
    ...     log.error(f"Template error: {e}")
    """

    pass


class TemplateNotFoundError(TemplateError):
    """Template not found by any configured loader.

    Raised when `Environment.get_template(name)` cannot locate the template
    in any of the loader's search paths.

    Example:
        >>> env.get_template("nonexistent.html")
        TemplateNotFoundError: Template 'nonexistent.html' not found in: templates/
    """

    pass


class TemplateSyntaxError(TemplateError):
    """Parse-time syntax error in template source.

    Raised by the Parser when template syntax is invalid. Includes source
    location for error reporting."""

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
    """Render-time error with rich debugging context.

    Raised during template rendering when an operation fails. Provides
    detailed information to help diagnose the issue:

    - Template name and line number
    - The expression that caused the error
    - Actual values and their types
    - Actionable suggestion for fixing

    Output Format:
        ```
        Runtime Error: 'NoneType' object has no attribute 'title'
          Location: article.html:15
          Expression: {{ post.title }}
          Values:
            post = None (NoneType)
          Suggestion: Check if 'post' is defined, or use {{ post.title | default('') }}
        ```

    Attributes:
        message: Error description
        expression: Template expression that failed
        values: Dict of variable names → values for context
        template_name: Name of the template
        lineno: Line number in template source
        suggestion: Actionable fix suggestion
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
    """A required value was None or missing.

    Raised by the `| require` filter when a value that must be present is
    None or missing. Useful for validating required context variables.

    Example:
        >>> {{ user.email | require('Email is required for notifications') }}
        RequiredValueError: Email is required for notifications
          Suggestion: Ensure 'email' is set before this point, or use | default(fallback)
    """

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
    """Attempted to compare None values, typically during sorting.

    Raised when `| sort` or similar operations encounter None values that
    cannot be compared. Provides information about which items have None
    values for the sort attribute.

    Example:
        >>> {{ posts | sort(attribute='weight') }}
        NoneComparisonError: Cannot compare NoneType with int when sorting by 'weight'

        Items with None/empty values:
          - "Draft Post": weight = None/empty
          - "Untitled": weight = None/empty

        Suggestion: Ensure all items have 'weight' set, or filter out None values first
    """

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


class UndefinedError(TemplateError):
    """Raised when accessing an undefined variable.

    Strict mode is enabled by default in Kida. When a template references
    a variable that doesn't exist in the context, this error is raised
    instead of silently returning None.

    Example:
        >>> env = Environment()
        >>> env.from_string("{{ undefined_var }}").render()
        UndefinedError: Undefined variable 'undefined_var' in <template>:1

    To fix:
        - Pass the variable in render(): template.render(undefined_var="value")
        - Use the default filter: {{ undefined_var | default("fallback") }}
    """

    def __init__(
        self,
        name: str,
        template: str | None = None,
        lineno: int | None = None,
    ):
        self.name = name
        self.template = template or "<template>"
        self.lineno = lineno
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        location = self.template
        if self.lineno:
            location += f":{self.lineno}"
        return f"Undefined variable '{self.name}' in {location}"
