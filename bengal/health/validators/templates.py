"""
Template validation for catching syntax errors before rendering.

This module provides the single source of truth for template validation in Bengal.
It validates template syntax and checks for missing includes/dependencies.
Works with any template engine implementing TemplateEngineProtocol.

Key features:
- Validates template syntax before rendering (engine-agnostic)
- Checks that included templates exist
- Provides detailed error context
- CLI integration for validation commands

Architecture:
This module consolidates template validation that was previously in
rendering/validator.py. The TemplateValidator class contains the core logic,
while validate_templates() provides CLI integration.

Related:
- bengal/health/validators/__init__.py: Validator exports
- bengal/rendering/engines/jinja.py: JinjaTemplateEngine.validate()
- bengal/rendering/engines/kida.py: KidaTemplateEngine.validate()
- bengal/protocols/rendering.py: TemplateValidator protocol

"""

from __future__ import annotations

from typing import Any

from bengal.utils.observability.logger import get_logger

logger = get_logger(__name__)


class TemplateValidator:
    """
    Validates templates for syntax errors and missing dependencies.

    This validator uses the template engine's built-in validation to check:
    - Syntax errors (unclosed tags, invalid expressions)
    - Missing included templates
    - Invalid extends references

    Works with any engine implementing TemplateEngineProtocol (Jinja2, Kida, etc.).

    Attributes:
        template_engine: TemplateEngine instance to validate

    """

    def __init__(self, template_engine: Any) -> None:
        """
        Initialize validator.

        Args:
            template_engine: TemplateEngine instance implementing validate() method
        """
        self.template_engine = template_engine

    def validate_all(self) -> list[Any]:
        """
        Validate all templates in the theme.

        Uses the engine's built-in validate() method which is engine-agnostic.
        Works with Jinja2, Kida, and any other engine implementing the protocol.

        Returns:
            List of TemplateRenderError objects for display
        """
        from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError
        from bengal.rendering.errors.classifier import code_for_legacy_string

        # Use the engine's validate() method - works with all engines
        # This returns list[TemplateError] (simple dataclass)
        template_errors = self.template_engine.validate()

        # Convert TemplateError to TemplateRenderError for rich display
        errors: list[Any] = []
        for err in template_errors:
            template_path = self.template_engine.get_template_path(err.template)
            error_type = err.error_type or "syntax"
            error = TemplateRenderError(
                error_type=error_type,
                message=err.message,
                template_context=TemplateErrorContext(
                    template_name=err.template,
                    line_number=err.line,
                    column=None,
                    source_line=None,
                    surrounding_lines=[],
                    template_path=template_path,
                ),
                inclusion_chain=None,
                page_source=None,
                suggestion=None,
                available_alternatives=[],
                code=code_for_legacy_string(error_type),
            )
            errors.append(error)

        return errors


def validate_templates(template_engine: Any) -> int:
    """
    Validate all templates and display results.

    This is the main entry point for CLI template validation.

    Args:
        template_engine: TemplateEngine instance

    Returns:
        Number of errors found

    """
    from bengal.cli.utils.output import get_cli_output

    cli = get_cli_output()
    cli.blank()
    cli.info("Validating templates...")
    cli.blank()

    validator = TemplateValidator(template_engine)
    errors = validator.validate_all()

    if not errors:
        cli.success("All templates valid!")
        cli.blank()
        return 0

    # Display errors
    from bengal.errors.display import display_template_render_error

    cli.error(f"Found {len(errors)} template error(s):")
    cli.blank()

    for i, error in enumerate(errors, 1):
        cli.error(f"Error {i}/{len(errors)}:")
        display_template_render_error(error, cli)

        if i < len(errors):
            cli.info("─" * 80)

    return len(errors)
