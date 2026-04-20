"""
ErrorClassifier — map a template exception to a canonical ErrorCode.

Extracted from ``TemplateRenderError._classify_error`` (Sprint A1.1) per
``plan/rfc-template-error-codes.md``. The classifier is pure: no I/O, no
file reads, no dependence on the template engine.

The :class:`ErrorClassifier` collapses the previous string-constant
classification into the canonical :class:`bengal.errors.codes.ErrorCode`
enum (R002, R003, R004, R010, R014-R019).

Related Modules:
- bengal.errors.codes:                 ErrorCode enum (R0xx range)
- bengal.rendering.errors.exceptions:  Legacy TemplateRenderError (deprecated)
- bengal.rendering.errors.context_extractor:  SourceContextExtractor (A1.2)

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kida.environment.exceptions import TemplateRuntimeError, TemplateSyntaxError, UndefinedError
from kida.environment.exceptions import TemplateRuntimeError as KidaRuntimeError
from kida.environment.exceptions import TemplateSyntaxError as KidaSyntaxError
from kida.environment.exceptions import UndefinedError as KidaUndefinedError

from bengal.errors.codes import ErrorCode

from .context import InclusionChain

# Kida does not have TemplateAssertionError; use TemplateSyntaxError as equivalent
# (filter-unknown errors are compile-time syntax errors under Kida).
TemplateAssertionError = TemplateSyntaxError


class ErrorClassifier:
    """Map a template exception to a canonical :class:`ErrorCode`.

    Pure: no I/O, no engine state. Idempotent. Safe to call from any
    thread. The classifier examines exception type and message — it
    never reads template source. For source extraction see
    :class:`SourceContextExtractor`.
    """

    def classify(self, exc: BaseException) -> ErrorCode:
        """Return the ErrorCode that best describes ``exc``.

        Branch order matters: more specific TypeError subcategories
        (callable / type-comparison / none-access) are checked before
        the generic Jinja/Kida exception-type fallbacks. Unknown
        exceptions fall back to :attr:`ErrorCode.R010`.
        """
        error_str = str(exc).lower()

        if isinstance(exc, TypeError):
            if self._is_callable_error(error_str):
                return ErrorCode.R015
            if self._is_type_comparison(error_str):
                return ErrorCode.R017
            if self._is_none_access(error_str):
                return ErrorCode.R016

        if self._is_filter_error(exc, error_str):
            return ErrorCode.R004

        if isinstance(exc, (TemplateSyntaxError, KidaSyntaxError)):
            return ErrorCode.R002
        if isinstance(exc, TemplateAssertionError):
            return ErrorCode.R002
        if isinstance(exc, (UndefinedError, KidaUndefinedError)):
            return ErrorCode.R003
        if isinstance(exc, (TemplateRuntimeError, KidaRuntimeError)):
            return ErrorCode.R014

        # Some embeddings raise generic exceptions for unknown filters.
        if "unknown filter" in error_str:
            return ErrorCode.R004

        return ErrorCode.R010

    @staticmethod
    def _is_callable_error(error_str: str) -> bool:
        """True for ``TypeError: 'NoneType' object is not callable``."""
        return (
            "'nonetype' object is not callable" in error_str
            or "nonetype object is not callable" in error_str
        )

    @staticmethod
    def _is_type_comparison(error_str: str) -> bool:
        """True for ``TypeError: ... not supported between instances of ...``."""
        return "not supported between instances of" in error_str

    @staticmethod
    def _is_none_access(error_str: str) -> bool:
        """True for ``TypeError`` accessing/iterating ``NoneType``."""
        return (
            "argument of type 'nonetype' is not" in error_str
            or "'nonetype' object is not iterable" in error_str
            or "'nonetype' object is not subscriptable" in error_str
            or "'nonetype' has no" in error_str
        )

    @staticmethod
    def _is_filter_error(exc: BaseException, error_str: str) -> bool:
        """True for unknown/missing template filter errors."""
        if "no filter named" in error_str:
            return True
        if "filter" in error_str and ("unknown" in error_str or "not found" in error_str):
            return True
        return isinstance(exc, TemplateAssertionError) and "unknown filter" in error_str


def build_inclusion_chain(exc: BaseException) -> InclusionChain | None:
    """Build a template inclusion chain from a Python traceback.

    Walks ``exc.__traceback__`` for frames whose filename contains
    ``templates/`` and emits ``(template_name, line)`` tuples. Returns
    ``None`` when no template frames are present.

    Free function rather than a classifier method because the chain
    answers "what included what" — independent of how we classified
    the error.
    """
    import traceback

    tb = traceback.extract_tb(exc.__traceback__)

    entries: list[tuple[str, int]] = []
    for frame in tb:
        if "templates/" in frame.filename:
            template_name = Path(frame.filename).name
            entries.append((template_name, frame.lineno))

    return InclusionChain(entries) if entries else None


def find_first_code_line(lines: list[str], exc: BaseException) -> int:
    """Return the 1-indexed line of the first non-comment template code.

    For ``TypeError`` exceptions, prefer lines containing function calls
    or filter applications — these are the likely failure sites when
    the engine reports line 1 because the line info wasn't preserved
    through compilation.

    Returns 1 when no code line is detectable (defensive fallback).
    """
    import re

    callable_patterns = (
        r"\{\{.*\w+\s*\(",  # {{ func(
        r"\{\%.*\w+\s*\(",  # {% func(
        r"\|s*\w+",  # | filter
    )

    in_comment = False
    first_code_line = 1
    found_first_code = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if "{#" in stripped and "#}" not in stripped:
            in_comment = True
            continue
        if "#}" in stripped:
            in_comment = False
            continue
        if in_comment:
            continue

        if not stripped or stripped.startswith("{#"):
            continue

        if not found_first_code:
            first_code_line = i
            found_first_code = True

        if isinstance(exc, TypeError):
            for pattern in callable_patterns:
                if re.search(pattern, line):
                    return i

    return first_code_line


# Public re-exports
__all__ = [
    "ErrorClassifier",
    "build_inclusion_chain",
    "code_for_legacy_string",
    "find_first_code_line",
]


# Back-compat: callers that previously imported the legacy string-constant
# classification can use this helper to round-trip ErrorCode → legacy string.
# Removed in v0.5.0 along with TemplateRenderError.
_LEGACY_CODE_TO_STRING: dict[ErrorCode, str] = {
    ErrorCode.R002: "syntax",
    ErrorCode.R003: "undefined",
    ErrorCode.R004: "filter",
    ErrorCode.R010: "other",
    ErrorCode.R014: "runtime",
    ErrorCode.R015: "callable",
    ErrorCode.R016: "none_access",
    ErrorCode.R017: "type_comparison",
    ErrorCode.R018: "include_missing",
    ErrorCode.R019: "circular_include",
}


def _legacy_string_for(code: ErrorCode) -> str:
    """Return the pre-A1.1 string constant for an ErrorCode (for back-compat callers)."""
    return _LEGACY_CODE_TO_STRING.get(code, "other")


_LEGACY_STRING_TO_CODE: dict[str, ErrorCode] = {
    string: code for code, string in _LEGACY_CODE_TO_STRING.items()
}


def code_for_legacy_string(error_type: str) -> ErrorCode:
    """Map a legacy error_type string to its canonical ErrorCode.

    Used by the health-check path in :mod:`bengal.health.validators.templates`
    where validation results carry only the legacy string and there is no
    live exception to re-classify. Defaults to :attr:`ErrorCode.R010`.
    """
    return _LEGACY_STRING_TO_CODE.get(error_type, ErrorCode.R010)


def classify_legacy(exc: BaseException) -> str:
    """Drop-in replacement for ``TemplateRenderError._classify_error``.

    Returns the legacy string constant. Prefer
    :meth:`ErrorClassifier.classify` for new code. Removed in v0.5.0.
    """
    return _legacy_string_for(ErrorClassifier().classify(exc))


# Type-only re-export for back-compat with callers that expected the
# previous TemplateAssertionError alias from exceptions.py.
_ANY: Any = TemplateAssertionError
