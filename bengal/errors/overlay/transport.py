"""
Wire-format converters for build-error overlay messages (Sprint A3.2).

Pure converters that translate :class:`TemplateRenderError` instances into
the JSON-serializable envelopes specified in
``plan/rfc-template-error-codes.md`` (A0.2). The SSE notifier in
``bengal/server/live_reload/notification.py`` consumes the dicts produced
here and ``json.dumps`` them onto the wire.

Two envelopes are defined:

- ``build_error`` — non-empty list of rendering errors after a build.
- ``build_ok`` — overlay-dismiss signal after a successful rebuild.

Both carry ``schema_version: 1`` and a UTC ``timestamp`` so future client
revisions can negotiate compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bengal.rendering.errors import TemplateRenderError


__all__ = [
    "build_error_payload",
    "build_ok_payload",
    "error_to_dict",
]


SCHEMA_VERSION = 1


_ERROR_TYPE_TITLES: dict[str, str] = {
    "syntax": "Template Syntax Error",
    "filter": "Unknown Filter",
    "undefined": "Undefined Variable",
    "runtime": "Template Runtime Error",
    "callable": "None Is Not Callable",
    "none_access": "None Is Not Iterable",
    "type_comparison": "Type Comparison Error",
    "include_missing": "Include Not Found",
    "circular_include": "Circular Include",
    "other": "Template Error",
}


def build_error_payload(
    errors: Iterable[TemplateRenderError],
    *,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Construct a ``build_error`` envelope from one or more rendering errors.

    Args:
        errors: Errors to include. Order is preserved; the client renders
            ``errors[0]`` and exposes the rest via a carousel control.
        timestamp: Optional override (used by tests for stable snapshots).

    Returns:
        A JSON-serializable dict matching the A0.2 ``build_error`` schema.
    """
    return {
        "type": "build_error",
        "schema_version": SCHEMA_VERSION,
        "timestamp": _format_timestamp(timestamp),
        "errors": [error_to_dict(err) for err in errors],
    }


def build_ok_payload(
    *,
    build_ms: int | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Construct a ``build_ok`` envelope signalling overlay dismiss.

    Args:
        build_ms: Build duration in milliseconds (purely informational).
        timestamp: Optional override (used by tests for stable snapshots).
    """
    payload: dict[str, Any] = {
        "type": "build_ok",
        "schema_version": SCHEMA_VERSION,
        "timestamp": _format_timestamp(timestamp),
    }
    if build_ms is not None:
        payload["build_ms"] = int(build_ms)
    return payload


def error_to_dict(error: TemplateRenderError) -> dict[str, Any]:
    """Project a :class:`TemplateRenderError` into the wire-schema dict."""
    code_obj = getattr(error, "code", None)
    code_name = code_obj.name if code_obj else None
    docs_url = code_obj.docs_url if code_obj else None
    title = _ERROR_TYPE_TITLES.get(error.error_type, "Template Error")

    return {
        "code": code_name,
        "code_name": code_obj.value if code_obj else None,
        "error_type": error.error_type,
        "docs_url": docs_url,
        "title": title,
        "message": str(error.message),
        "hint": _stringify_optional(getattr(error, "suggestion", None)),
        "suggestions": _suggestions(error),
        "frame": _frame(error),
        "inclusion_chain": _inclusion_chain(error),
        "page_source": _stringify_optional(getattr(error, "page_source", None)),
        "search_paths": [str(p) for p in (getattr(error, "search_paths", None) or [])],
    }


def _format_timestamp(ts: datetime | None) -> str:
    """Format ``ts`` (or now) as ISO-8601 UTC with a trailing ``Z``."""
    moment = ts if ts is not None else datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stringify_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _suggestions(error: TemplateRenderError) -> list[dict[str, Any]]:
    """Return the ranked "did you mean?" alternatives.

    Order matches what ``available_alternatives`` already provides — the
    underlying scorer is :func:`difflib.get_close_matches`, which does not
    expose a numeric distance, so the wire schema's optional ``distance``
    field is omitted.
    """
    alternatives = getattr(error, "available_alternatives", None) or []
    if not alternatives:
        return []
    return [{"label": "Did you mean?", "value": str(alt)} for alt in alternatives]


def _frame(error: TemplateRenderError) -> dict[str, Any] | None:
    ctx = error.template_context
    if not ctx:
        return None

    file_rel = ctx.template_name or (str(ctx.template_path) if ctx.template_path else None)
    if file_rel is None and not ctx.surrounding_lines:
        return None

    lines = []
    error_line = ctx.line_number
    for line_num, content in ctx.surrounding_lines:
        entry: dict[str, Any] = {"n": line_num, "text": content}
        if line_num == error_line:
            entry["is_error"] = True
        lines.append(entry)

    return {
        "file": file_rel,
        "file_abs": str(ctx.template_path) if ctx.template_path else None,
        "line": ctx.line_number,
        "column": ctx.column,
        "lines": lines,
    }


def _inclusion_chain(error: TemplateRenderError) -> list[dict[str, Any]]:
    chain = getattr(error, "inclusion_chain", None)
    if not chain:
        return []
    return [{"template": name, "line": line} for name, line in chain.entries]
