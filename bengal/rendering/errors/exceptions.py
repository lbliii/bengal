"""
Template rendering exception classes.

This module contains the TemplateRenderError exception which provides rich
error information for template rendering failures, including source context,
suggestions, and IDE-friendly formatting.

Classes:
    TemplateRenderError: Rich exception with template context, line numbers,
        source snippets, and actionable suggestions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kida.environment.exceptions import TemplateSyntaxError

from bengal.errors import BengalRenderingError
from bengal.errors.suggestions import (
    find_filter_alternatives as _find_filter_alternatives_impl,
)
from bengal.errors.suggestions import (
    find_variable_alternatives as _find_variable_alternatives_impl,
)
from bengal.errors.suggestions import (
    generate_template_suggestion as _generate_template_suggestion_impl,
)
from bengal.errors.suggestions import (
    identify_none_callable as _identify_none_callable_impl,
)
from bengal.errors.suggestions import (
    suggest_type_comparison as _suggest_type_comparison_impl,
)
from bengal.utils.observability.logger import truncate_error

from .classifier import ErrorClassifier as _ErrorClassifier
from .classifier import (
    build_inclusion_chain as _build_inclusion_chain_impl,
)
from .classifier import (
    classify_legacy as _classify_legacy_impl,
)
from .classifier import (
    find_first_code_line as _find_first_code_line_impl,
)
from .context_extractor import (
    SourceContextExtractor as _SourceContextExtractor,
)
from .context_extractor import (
    scan_template_for_callables as _scan_template_for_callables_impl,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.errors.codes import ErrorCode

    from .context import InclusionChain, TemplateErrorContext

# Kida does not have TemplateAssertionError; use TemplateSyntaxError as equivalent
# (filter-unknown errors are compile-time syntax errors under Kida)
TemplateAssertionError = TemplateSyntaxError


class TemplateRenderError(BengalRenderingError):
    """
    Rich template error with all debugging information.

    This replaces the simple string error messages with structured data
    that can be displayed beautifully and used for IDE integration.

    Extends BengalRenderingError to provide consistent error handling
    while maintaining rich context for template debugging.

    """

    _show_traceback: bool
    _original_exception: Exception | None

    def __init__(
        self,
        error_type: str,
        message: str,
        template_context: TemplateErrorContext,
        inclusion_chain: InclusionChain | None = None,
        page_source: Path | None = None,
        suggestion: str | None = None,
        available_alternatives: list[str] | None = None,
        search_paths: list[Path] | None = None,
        *,
        code: ErrorCode | None = None,
        file_path: Path | None = None,
        line_number: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """
        Initialize template render error.

        Args:
            error_type: Type of error ('syntax', 'undefined', 'filter', 'runtime')
            message: Error message
            template_context: Template error context
            inclusion_chain: Template inclusion chain (if applicable)
            page_source: Source page path (if applicable)
            suggestion: Helpful suggestion for fixing
            available_alternatives: List of alternative filters/variables
            search_paths: Template search paths
            code: Canonical ErrorCode (R002/R003/R004/R010/R014-R019). When
                set, the rendered message gets the standard ``[R0XX]`` prefix
                applied by the base class.
            file_path: File path (defaults to template_context.template_path)
            line_number: Line number (defaults to template_context.line_number)
            original_error: Original exception that caused this error
        """
        # Set base class fields (use template context if not provided)
        super().__init__(
            message=message,
            code=code,
            file_path=file_path or template_context.template_path,
            line_number=line_number or template_context.line_number,
            suggestion=suggestion,
            original_error=original_error,
        )

        # Set rich context fields
        self.error_type = error_type
        self.template_context = template_context
        self.inclusion_chain = inclusion_chain
        self.page_source = page_source
        self.available_alternatives = available_alternatives or []
        self.search_paths = search_paths

    @classmethod
    def from_jinja2_error(
        cls, error: Exception, template_name: str, page_source: Path | None, template_engine: Any
    ) -> TemplateRenderError:
        """
        Extract rich error information from Jinja2 exception.

        Args:
            error: Jinja2 exception
            template_name: Template being rendered
            page_source: Source content file (if applicable)
            template_engine: Template engine instance

        Returns:
            Rich error object
        """
        # Determine error type (legacy string) + canonical ErrorCode
        error_type = cls._classify_error(error)
        code = _ErrorClassifier().classify(error)

        # Extract context
        context = cls._extract_context(error, template_name, template_engine)

        # Build inclusion chain
        inclusion_chain = cls._build_inclusion_chain(error, template_engine)

        # Generate suggestion (pass template path for better callable identification)
        suggestion = cls._generate_suggestion(
            error, error_type, template_engine, context.template_path
        )

        # Find alternatives (for unknown filters/variables)
        alternatives = cls._find_alternatives(error, error_type, template_engine)

        # Extract search paths from template engine
        search_paths: list[Path] | None = None
        if hasattr(template_engine, "template_dirs"):
            try:
                dirs = template_engine.template_dirs
                if dirs and hasattr(dirs, "__iter__"):
                    search_paths = list(dirs)
            except TypeError, AttributeError:
                # Handle mock objects or other non-iterable cases
                pass

        return cls(
            error_type=error_type,
            message=truncate_error(error),
            template_context=context,
            inclusion_chain=inclusion_chain,
            page_source=page_source,
            suggestion=suggestion,
            available_alternatives=alternatives,
            search_paths=search_paths,
            code=code,
            original_error=error,
        )

    @staticmethod
    def _classify_error(error: Exception) -> str:
        """Legacy classifier — delegates to bengal.rendering.errors.classifier.

        Returns the historical string constant. New code should call
        ``ErrorClassifier().classify(exc)`` directly to get an
        :class:`ErrorCode`.
        """
        return _classify_legacy_impl(error)

    @staticmethod
    def _extract_context(
        error: Exception, template_name: str, template_engine: Any
    ) -> TemplateErrorContext:
        """Delegates to ``bengal.rendering.errors.context_extractor.SourceContextExtractor``."""
        return _SourceContextExtractor().extract(error, template_name, template_engine)

    @staticmethod
    def _find_first_code_line(lines: list[str], error: Exception) -> int:
        """Delegates to bengal.rendering.errors.classifier.find_first_code_line."""
        return _find_first_code_line_impl(lines, error)

    @staticmethod
    def _build_inclusion_chain(error: Exception, template_engine: Any) -> InclusionChain | None:
        """Delegates to bengal.rendering.errors.classifier.build_inclusion_chain."""
        del template_engine  # unused — kept for back-compat signature
        return _build_inclusion_chain_impl(error)

    @staticmethod
    def _generate_suggestion(
        error: Exception,
        error_type: str,
        template_engine: Any,
        template_path: Path | None = None,
    ) -> str | None:
        """Delegates to ``bengal.errors.suggestions.generate_template_suggestion``."""
        del template_engine  # unused — kept for back-compat signature
        return _generate_template_suggestion_impl(error, error_type, template_path)

    @staticmethod
    def _identify_none_callable(error: Exception, template_path: Path | None = None) -> str | None:
        """Delegates to ``bengal.errors.suggestions.identify_none_callable``."""
        return _identify_none_callable_impl(error, template_path)

    @staticmethod
    def _scan_template_for_callables(template_path: Path) -> list[str]:
        """Delegates to ``bengal.rendering.errors.context_extractor.scan_template_for_callables``."""
        return _scan_template_for_callables_impl(template_path)

    @staticmethod
    def _suggest_type_comparison(error: Exception) -> str:
        """Delegates to ``bengal.errors.suggestions.suggest_type_comparison``."""
        return _suggest_type_comparison_impl(error)

    @staticmethod
    def _find_alternatives(error: Exception, error_type: str, template_engine: Any) -> list[str]:
        """Find Levenshtein-near names to suggest as ``Did you mean?``.

        Filters route through ``find_filter_alternatives`` over the
        registered filter names. Undefined-variable errors route through
        ``find_variable_alternatives``, which prefers the candidate set
        Kida already attached to the exception (``_available_names``)
        and falls back to the engine's globals when missing.
        """
        if error_type == "filter":
            available = sorted(template_engine.env.filters.keys())
            return _find_filter_alternatives_impl(error, available)
        if error_type == "undefined":
            globals_iter: list[str] | None = None
            env = getattr(template_engine, "env", None)
            if env is not None:
                raw_globals = getattr(env, "globals", None)
                if raw_globals is not None:
                    try:
                        globals_iter = list(raw_globals)
                    except TypeError:
                        # Tests sometimes pass bare Mock() engines; treat
                        # an unusable globals dict as "no fallback set"
                        # rather than crashing the error path.
                        globals_iter = None
            return _find_variable_alternatives_impl(error, available_names=globals_iter)
        return []
