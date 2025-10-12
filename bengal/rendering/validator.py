"""
Template validation before rendering.
"""

from pathlib import Path
from typing import Any

import click
from jinja2 import TemplateSyntaxError


class TemplateValidator:
    """
    Validates templates for syntax errors and missing dependencies.
    """

    def __init__(self, template_engine: Any):
        """
        Initialize validator.

        Args:
            template_engine: TemplateEngine instance
        """
        self.template_engine = template_engine
        self.env = template_engine.env

    def validate_all(self) -> list[Any]:
        """
        Validate all templates in the theme.

        Returns:
            List of errors found
        """

        errors = []

        for template_dir in self.template_engine.template_dirs:
            if not template_dir.exists():
                continue

            # Find all template files
            for template_file in template_dir.rglob("*.html"):
                template_name = str(template_file.relative_to(template_dir))

                # Validate syntax
                syntax_errors = self._validate_syntax(template_name, template_file)
                errors.extend(syntax_errors)

                # Validate includes (check if included templates exist)
                include_errors = self._validate_includes(template_name, template_file)
                errors.extend(include_errors)

        return errors

    def _validate_syntax(self, template_name: str, template_path: Path) -> list[Any]:
        """Validate template syntax."""
        from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError

        try:
            # Try to compile the template
            with open(template_path, encoding="utf-8") as f:
                source = f.read()

            self.env.parse(source, template_name, str(template_path))
            return []

        except TemplateSyntaxError as e:
            # Create error object
            error = TemplateRenderError.from_jinja2_error(
                e, template_name, None, self.template_engine
            )
            return [error]

        except Exception as e:
            # Other parsing errors
            error = TemplateRenderError(
                error_type="other",
                message=str(e),
                template_context=TemplateErrorContext(
                    template_name=template_name,
                    line_number=None,
                    column=None,
                    source_line=None,
                    surrounding_lines=[],
                    template_path=template_path,
                ),
                inclusion_chain=None,
                page_source=None,
                suggestion=None,
                available_alternatives=[],
            )
            return [error]

    def _validate_includes(self, template_name: str, template_path: Path) -> list[Any]:
        """Check if all included templates exist."""
        from bengal.rendering.errors import TemplateErrorContext, TemplateRenderError

        errors = []

        # Parse template to find includes
        with open(template_path, encoding="utf-8") as f:
            source = f.read()

        # Simple regex to find includes (not perfect but good enough)
        import re

        includes = re.findall(r"{%\s*include\s+['\"]([^'\"]+)['\"]", source)

        for include_name in includes:
            try:
                self.env.get_template(include_name)
            except Exception:
                # Include not found
                error = TemplateRenderError(
                    error_type="other",
                    message=f"Included template not found: {include_name}",
                    template_context=TemplateErrorContext(
                        template_name=template_name,
                        line_number=None,
                        column=None,
                        source_line=None,
                        surrounding_lines=[],
                        template_path=template_path,
                    ),
                    inclusion_chain=None,
                    page_source=None,
                    suggestion=f"Create {include_name} or fix the include path",
                    available_alternatives=[],
                )
                errors.append(error)

        return errors


def validate_templates(template_engine: Any) -> int:
    """
    Validate all templates and display results.

    Args:
        template_engine: TemplateEngine instance

    Returns:
        Number of errors found
    """
    click.echo(click.style("\n🔍 Validating templates...\n", fg="cyan", bold=True))

    validator = TemplateValidator(template_engine)
    errors = validator.validate_all()

    if not errors:
        click.echo(click.style("✓ All templates valid!", fg="green", bold=True))
        click.echo()
        return 0

    # Display errors
    from bengal.rendering.errors import display_template_error

    click.echo(click.style(f"❌ Found {len(errors)} template error(s):\n", fg="red", bold=True))

    for i, error in enumerate(errors, 1):
        click.echo(click.style(f"Error {i}/{len(errors)}:", fg="red", bold=True))
        display_template_error(error)

        if i < len(errors):
            click.echo(click.style("─" * 80, fg="cyan"))

    return len(errors)
