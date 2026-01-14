"""
Rich template error handling with contextual debugging information.

This module provides structured error objects for template rendering failures,
enabling clear error messages with source context, suggestions, and IDE-friendly
formatting.

Key Classes:
    TemplateRenderError:
        Rich exception with template context, line numbers, source snippets,
        and actionable suggestions. Extends BengalRenderingError for
        consistent error handling across the codebase.

    TemplateErrorContext:
        Captures error location (file, line, column) and surrounding source
        code for display.

    InclusionChain:
        Tracks template include/extend hierarchy to show how the error
        location was reached.

    ErrorDeduplicator:
        Tracks and deduplicates similar errors across multiple pages to
        reduce noise in build output. Attached to BuildStats (not global).

Error Types:
    - syntax: Invalid Jinja2 syntax (missing tags, brackets, etc.)
    - filter: Unknown filter name (e.g., ``| nonexistent``)
    - undefined: Undefined variable access (e.g., ``{{ missing_var }}``)
    - callable: NoneType is not callable (e.g., missing filter/function registration)
    - none_access: NoneType is not iterable (e.g., using 'in' on None)
    - runtime: Runtime errors during template execution
    - other: Unclassified template errors

Display Functions:
    display_template_error():
        Renders error to terminal with syntax highlighting (via Rich if
        available) or plain text fallback. Shows source context, suggestions,
        and documentation links.

Usage:
    Typically created automatically by the rendering pipeline:

        >>> try:
        ...     template.render(context)
        ... except Exception as e:
        ...     error = TemplateRenderError.from_jinja2_error(
        ...         e, template_name, page_source, template_engine
        ...     )
        ...     display_template_error(error)

    Error deduplication for batch rendering (via BuildStats):

        >>> dedup = build_stats.get_error_deduplicator()
        >>> for page in pages:
        ...     try:
        ...         render(page)
        ...     except Exception as e:
        ...         error = TemplateRenderError.from_jinja2_error(...)
        ...         if dedup.should_display(error):
        ...             display_template_error(error)
        >>> dedup.display_summary()  # Show counts of suppressed errors

Error Message Enhancement:
    The module includes smart suggestion generation:
    - Typo detection for variable/filter names
    - Safe access patterns for undefined errors
    - Callable identification from template source
    - Documentation links for common issues

Related Modules:
    - bengal.rendering.engines.errors: Low-level engine exceptions
    - bengal.errors: Base error classes (BengalRenderingError)
    - bengal.orchestration.stats: BuildStats with error deduplicator
    - bengal.utils.rich_console: Rich terminal output utilities

"""

from .context import InclusionChain, TemplateErrorContext
from .deduplication import ErrorDeduplicator
from .display import (
    _extract_dict_attribute,
    _extract_filter_name,
    _extract_variable_name,
    _generate_enhanced_suggestions,
    display_template_error,
)
from .exceptions import TemplateRenderError

__all__ = [
    "TemplateErrorContext",
    "InclusionChain",
    "ErrorDeduplicator",
    "TemplateRenderError",
    "display_template_error",
    # Helper functions (exported for testing)
    "_extract_variable_name",
    "_extract_filter_name",
    "_extract_dict_attribute",
    "_generate_enhanced_suggestions",
]
