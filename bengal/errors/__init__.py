"""
Centralized error handling package for Bengal.

This package consolidates all error-related utilities for consistent,
actionable, and AI-friendly error handling. Every error in Bengal carries
structured context for debugging, investigation, and user guidance.

Architecture Overview
=====================

The error handling system is organized into layers:

1. **Foundation Layer** - Core error types and codes
2. **Context Layer** - Rich context capture and enrichment
3. **Recovery Layer** - Graceful degradation and recovery patterns
4. **Reporting Layer** - User-facing error presentation

Module Reference
================

**Error Codes** (``codes.py``):
Unique error codes (e.g., R001, C002) for quick identification and
documentation linking. Codes are categorized by subsystem (Config,
Content, Rendering, Discovery, Cache, Server, Template, Parsing, Asset).

**Exception Classes** (``exceptions.py``):
Base ``BengalError`` and domain-specific subclasses with rich context
support including error codes, build phases, related files, debug
payloads, and investigation helpers. All Bengal exceptions inherit
from ``BengalError``.

**Error Context** (``context.py``):
``ErrorContext`` and ``ErrorDebugPayload`` for capturing comprehensive
error context. ``BuildPhase`` and ``ErrorSeverity`` enums classify
errors by location and severity.

**Suggestions** (``suggestions.py``):
``ActionableSuggestion`` with fix descriptions, before/after code
snippets, documentation links, files to check, and grep patterns
for investigation.

**Session Tracking** (``session.py``):
``ErrorSession`` for tracking errors across builds, detecting recurring
patterns, identifying systemic issues, and providing investigation hints.

**Dev Server** (``dev_server.py``):
``DevServerErrorContext`` for hot-reload aware error handling with
file change tracking, auto-fix suggestions, and rollback commands.

**Aggregation** (``aggregation.py``):
``ErrorAggregator`` for batch processing to reduce log noise when
processing many items. Groups similar errors and provides summaries.

**Handlers** (``handlers.py``):
Context-aware help for common Python errors (``ImportError``,
``AttributeError``, ``TypeError``) with suggestions and close matches.

**Recovery** (``recovery.py``):
Graceful degradation patterns including ``with_error_recovery()``,
``error_recovery_context()``, and ``recover_file_processing()``.

**Reporter** (``reporter.py``):
CLI error report formatting with ``format_error_report()`` and
``format_error_summary()`` for build output.

**Traceback** (``traceback/``):
Configurable traceback rendering with four verbosity levels:
full, compact, minimal, and off.

Quick Start
===========

Raise a Bengal error with context::

from bengal.errors import BengalRenderingError, ErrorCode

raise BengalRenderingError(
    "Template not found: single.html",
    code=ErrorCode.R001,
    file_path=Path("content/post.md"),
    suggestion="Check templates/ directory",
)

Get actionable suggestion for an error pattern::

from bengal.errors import get_suggestion

    suggestion = get_suggestion("template", "not_found")
print(suggestion.fix)
print(suggestion.after_snippet)

Track errors across a build session::

from bengal.errors import record_error, get_session

    pattern_info = record_error(error, file_path="content/post.md")
if pattern_info["is_recurring"]:
    print("This error has occurred before")

    summary = get_session().get_summary()

Create dev server error context::

from bengal.errors import create_dev_error

    context = create_dev_error(
    error,
    changed_files=[changed_file],
    last_successful_build=last_build_time,
)
print(context.get_likely_cause())
print(context.quick_actions)

Use investigation helpers::

    try:
    render_page(page)
except BengalError as e:
    print("Investigation commands:")
    for cmd in e.get_investigation_commands():
        print(f"  {cmd}")
    print("Related test files:")
    for path in e.get_related_test_files():
        print(f"  {path}")

Performance Note
================

This module uses lazy imports to avoid loading heavy dependencies (Rich,
output formatting, etc.) until they are actually needed. The core error
types (ErrorCode, BengalError, exception subclasses) load instantly.

See Also
========

- ``bengal/orchestration/render.py`` - Error handling in rendering
- ``bengal/orchestration/build.py`` - Build-level error aggregation
- ``architecture/error-handling.md`` - Architecture documentation

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# =============================================================================
# EAGERLY LOADED - Core error types used everywhere (~2ms total)
# =============================================================================
# Error codes - lightweight enum, no dependencies
from bengal.errors.codes import (
    ErrorCode,
    get_codes_by_category,
    get_error_code_by_name,
)

# Exception classes - lightweight, only depends on codes
from bengal.errors.exceptions import (
    BengalAssetError,
    BengalAutodocError,
    BengalBuildError,
    BengalCacheError,
    BengalConfigError,
    BengalContentError,
    BengalDiscoveryError,
    BengalError,
    BengalGraphError,
    BengalParsingError,
    BengalRenderingError,
    BengalServerError,
    BengalTemplateFunctionError,
    BengalValidatorError,
    DirectiveContractError,
)

# =============================================================================
# TYPE_CHECKING - For static analysis without runtime cost
# =============================================================================

if TYPE_CHECKING:
    # Context enrichment
    # Error aggregation
    from bengal.errors.aggregation import (
        ErrorAggregator,
        extract_error_context,
    )
    from bengal.errors.context import (
        BuildPhase,
        ErrorContext,
        ErrorDebugPayload,
        ErrorSeverity,
        RelatedFile,
        create_config_context,
        create_discovery_context,
        create_rendering_context,
        enrich_error,
        get_context_from_exception,
    )

    # Dev server context
    from bengal.errors.dev_server import (
        DevServerErrorContext,
        DevServerState,
        FileChange,
        create_dev_error,
        get_dev_server_state,
        reset_dev_server_state,
    )

    # Display (moved from cli.helpers.error_display)
    from bengal.errors.display import (
        beautify_common_exception,
        display_bengal_error,
    )

    # Runtime handlers
    from bengal.errors.handlers import (
        ContextAwareHelp,
        get_context_aware_help,
    )

    # Recovery patterns
    from bengal.errors.recovery import (
        error_recovery_context,
        recover_file_processing,
        with_error_recovery,
    )

    # Reporter
    from bengal.errors.reporter import (
        format_error_report,
        format_error_summary,
    )

    # Session tracking
    from bengal.errors.session import (
        ErrorOccurrence,
        ErrorPattern,
        ErrorSession,
        get_session,
        record_error,
        reset_session,
    )

    # Actionable suggestions
    from bengal.errors.suggestions import (
        ActionableSuggestion,
        enhance_error_context,
        format_suggestion,
        format_suggestion_full,
        get_all_suggestions_for_category,
        get_attribute_error_suggestion,
        get_suggestion,
        get_suggestion_dict,
        search_suggestions,
    )

    # Utilities
    from bengal.errors.utils import (
        ThreadSafeSingleton,
        dataclass_to_dict,
        extract_between,
        extract_error_attributes,
        find_close_matches,
        generate_error_signature,
        get_error_message,
        safe_list_module_exports,
        serialize_value,
    )


__all__ = [
    # ============================================================
    # Suggestions (lazy)
    # ============================================================
    "ActionableSuggestion",
    "BengalAssetError",
    "BengalAutodocError",
    "BengalBuildError",
    "BengalCacheError",
    "BengalConfigError",
    "BengalContentError",
    "BengalDiscoveryError",
    # ============================================================
    # Exceptions (eager)
    # ============================================================
    "BengalError",
    "BengalGraphError",
    "BengalParsingError",
    "BengalRenderingError",
    "BengalServerError",
    "BengalTemplateFunctionError",
    "BengalValidatorError",
    # ============================================================
    # Context (lazy)
    # ============================================================
    "BuildPhase",
    # ============================================================
    # Handlers (lazy)
    # ============================================================
    "ContextAwareHelp",
    # ============================================================
    # Dev Server (lazy)
    # ============================================================
    "DevServerErrorContext",
    "DevServerState",
    "DirectiveContractError",
    # ============================================================
    # Aggregation (lazy)
    # ============================================================
    "ErrorAggregator",
    # ============================================================
    # Error Codes (eager)
    # ============================================================
    "ErrorCode",
    "ErrorContext",
    "ErrorDebugPayload",
    "ErrorOccurrence",
    "ErrorPattern",
    # ============================================================
    # Session Tracking (lazy)
    # ============================================================
    "ErrorSession",
    "ErrorSeverity",
    "FileChange",
    "RelatedFile",
    # ============================================================
    # Utils (lazy)
    # ============================================================
    "ThreadSafeSingleton",
    "beautify_common_exception",
    "create_config_context",
    "create_dev_error",
    "create_discovery_context",
    "create_rendering_context",
    "dataclass_to_dict",
    # ============================================================
    # Display (lazy, moved from cli.helpers.error_display)
    # ============================================================
    "display_bengal_error",
    "enhance_error_context",
    "enrich_error",
    "error_recovery_context",
    "extract_between",
    "extract_error_attributes",
    "extract_error_context",
    "find_close_matches",
    # ============================================================
    # Reporter (lazy)
    # ============================================================
    "format_error_report",
    "format_error_summary",
    "format_suggestion",
    "format_suggestion_full",
    "generate_error_signature",
    "get_all_suggestions_for_category",
    "get_attribute_error_suggestion",
    "get_codes_by_category",
    "get_context_aware_help",
    "get_context_from_exception",
    "get_dev_server_state",
    "get_error_code_by_name",
    "get_error_message",
    "get_session",
    "get_suggestion",
    "get_suggestion_dict",
    "record_error",
    "recover_file_processing",
    "reset_dev_server_state",
    "reset_session",
    "safe_list_module_exports",
    "search_suggestions",
    "serialize_value",
    # ============================================================
    # Recovery (lazy)
    # ============================================================
    "with_error_recovery",
]


# =============================================================================
# LAZY IMPORTS - Heavy modules loaded on first access
# =============================================================================

# Mapping of attribute name to (module_path, attribute_name)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Context
    "BuildPhase": ("bengal.errors.context", "BuildPhase"),
    "ErrorSeverity": ("bengal.errors.context", "ErrorSeverity"),
    "ErrorContext": ("bengal.errors.context", "ErrorContext"),
    "ErrorDebugPayload": ("bengal.errors.context", "ErrorDebugPayload"),
    "RelatedFile": ("bengal.errors.context", "RelatedFile"),
    "enrich_error": ("bengal.errors.context", "enrich_error"),
    "get_context_from_exception": ("bengal.errors.context", "get_context_from_exception"),
    "create_rendering_context": ("bengal.errors.context", "create_rendering_context"),
    "create_discovery_context": ("bengal.errors.context", "create_discovery_context"),
    "create_config_context": ("bengal.errors.context", "create_config_context"),
    # Dev server
    "DevServerErrorContext": ("bengal.errors.dev_server", "DevServerErrorContext"),
    "DevServerState": ("bengal.errors.dev_server", "DevServerState"),
    "FileChange": ("bengal.errors.dev_server", "FileChange"),
    "create_dev_error": ("bengal.errors.dev_server", "create_dev_error"),
    "get_dev_server_state": ("bengal.errors.dev_server", "get_dev_server_state"),
    "reset_dev_server_state": ("bengal.errors.dev_server", "reset_dev_server_state"),
    # Session
    "ErrorSession": ("bengal.errors.session", "ErrorSession"),
    "ErrorPattern": ("bengal.errors.session", "ErrorPattern"),
    "ErrorOccurrence": ("bengal.errors.session", "ErrorOccurrence"),
    "get_session": ("bengal.errors.session", "get_session"),
    "reset_session": ("bengal.errors.session", "reset_session"),
    "record_error": ("bengal.errors.session", "record_error"),
    # Suggestions
    "ActionableSuggestion": ("bengal.errors.suggestions", "ActionableSuggestion"),
    "get_suggestion": ("bengal.errors.suggestions", "get_suggestion"),
    "get_suggestion_dict": ("bengal.errors.suggestions", "get_suggestion_dict"),
    "format_suggestion": ("bengal.errors.suggestions", "format_suggestion"),
    "format_suggestion_full": ("bengal.errors.suggestions", "format_suggestion_full"),
    "enhance_error_context": ("bengal.errors.suggestions", "enhance_error_context"),
    "get_attribute_error_suggestion": (
        "bengal.errors.suggestions",
        "get_attribute_error_suggestion",
    ),
    "get_all_suggestions_for_category": (
        "bengal.errors.suggestions",
        "get_all_suggestions_for_category",
    ),
    "search_suggestions": ("bengal.errors.suggestions", "search_suggestions"),
    # Aggregation
    "ErrorAggregator": ("bengal.errors.aggregation", "ErrorAggregator"),
    "extract_error_context": ("bengal.errors.aggregation", "extract_error_context"),
    # Handlers
    "ContextAwareHelp": ("bengal.errors.handlers", "ContextAwareHelp"),
    "get_context_aware_help": ("bengal.errors.handlers", "get_context_aware_help"),
    # Recovery
    "with_error_recovery": ("bengal.errors.recovery", "with_error_recovery"),
    "error_recovery_context": ("bengal.errors.recovery", "error_recovery_context"),
    "recover_file_processing": ("bengal.errors.recovery", "recover_file_processing"),
    # Reporter
    "format_error_report": ("bengal.errors.reporter", "format_error_report"),
    "format_error_summary": ("bengal.errors.reporter", "format_error_summary"),
    # Display (moved from cli.helpers.error_display)
    "display_bengal_error": ("bengal.errors.display", "display_bengal_error"),
    "beautify_common_exception": ("bengal.errors.display", "beautify_common_exception"),
    # Utils
    "generate_error_signature": ("bengal.errors.utils", "generate_error_signature"),
    "extract_error_attributes": ("bengal.errors.utils", "extract_error_attributes"),
    "get_error_message": ("bengal.errors.utils", "get_error_message"),
    "serialize_value": ("bengal.errors.utils", "serialize_value"),
    "dataclass_to_dict": ("bengal.errors.utils", "dataclass_to_dict"),
    "extract_between": ("bengal.errors.utils", "extract_between"),
    "find_close_matches": ("bengal.errors.utils", "find_close_matches"),
    "safe_list_module_exports": ("bengal.errors.utils", "safe_list_module_exports"),
    "ThreadSafeSingleton": ("bengal.errors.utils", "ThreadSafeSingleton"),
}


def __getattr__(name: str) -> Any:
    """
    Lazy import for heavy error infrastructure.

    This avoids loading context enrichment, session tracking, reporter,
    and other heavy modules until they are actually needed. Most code
    only needs ErrorCode and exception classes, which are loaded eagerly.

    """
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module 'bengal.errors' has no attribute {name!r}")
