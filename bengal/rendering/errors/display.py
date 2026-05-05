"""
Display functions for template errors.

Functions:
    display_template_error: Back-compat shim — delegates to
        ``bengal.errors.display.display_template_render_error`` (Sprint A2.2).

Helper Functions:
    _generate_enhanced_suggestions: Back-compat shim — delegates to
        ``bengal.errors.suggestions.enhance_template_suggestions`` (Sprint A1.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.errors.display import (
    display_template_render_error as _display_template_render_error_impl,
)
from bengal.errors.suggestions import (
    _extract_dict_attribute,
    _extract_filter_name,
    _extract_variable_name,
)
from bengal.errors.suggestions import (
    enhance_template_suggestions as _enhance_template_suggestions_impl,
)

if TYPE_CHECKING:
    from bengal.output import CLIOutput

    from .exceptions import TemplateRenderError

__all__ = [
    "_extract_dict_attribute",
    "_extract_filter_name",
    "_extract_variable_name",
    "_generate_enhanced_suggestions",
    "display_template_error",
]


def display_template_error(
    error: TemplateRenderError,
    use_color: bool = True,
    cli: CLIOutput | None = None,
) -> None:
    """Display a template error in the terminal.

    Routes through :func:`bengal.errors.display.display_template_render_error`
    (CLIOutput-aware). When ``cli`` is omitted a default :class:`CLIOutput`
    is constructed; ``use_color`` is ignored — TTY detection is delegated
    to CLIOutput. The parameter is retained for back-compat only and will
    be removed in v0.5.0.
    """
    del use_color  # CLIOutput handles TTY/color detection.

    if cli is None:
        from bengal.output import get_cli_output

        cli = get_cli_output()

    _display_template_render_error_impl(error, cli)


def _generate_enhanced_suggestions(error: TemplateRenderError) -> list[str]:
    """Delegates to ``bengal.errors.suggestions.enhance_template_suggestions``.

    Kept as a back-compat entry point for tests and the plain-text
    display fallback below. New code should call the unified helper
    directly.
    """
    primary = getattr(error, "suggestion", None)
    source_line = None
    ctx = getattr(error, "template_context", None)
    if ctx is not None:
        source_line = getattr(ctx, "source_line", None)
    return _enhance_template_suggestions_impl(
        error.error_type,
        str(error.message),
        primary_suggestion=primary,
        source_line=source_line,
    )
