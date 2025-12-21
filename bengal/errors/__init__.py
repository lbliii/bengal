"""
Centralized error handling package for Bengal.

This package consolidates all error-related utilities for consistent,
actionable, and AI-friendly error handling.

Key Components:
===============

**Error Codes** (`codes.py`):
    Unique error codes (e.g., R001, C002) for quick identification
    and documentation linking.

**Exception Classes** (`exceptions.py`):
    Base BengalError and subclasses with rich context support including
    error codes, build phases, related files, and investigation helpers.

**Error Context** (`context.py`):
    ErrorContext, ErrorDebugPayload for capturing comprehensive error
    context. BuildPhase and ErrorSeverity enums for classification.

**Suggestions** (`suggestions.py`):
    ActionableSuggestion with fix descriptions, code snippets,
    documentation links, and investigation patterns.

**Session Tracking** (`session.py`):
    ErrorSession for tracking errors across builds, detecting patterns,
    and identifying systemic issues.

**Dev Server** (`dev_server.py`):
    DevServerErrorContext for hot-reload aware error handling with
    file change tracking and auto-fix suggestions.

**Aggregation** (`aggregation.py`):
    ErrorAggregator for batch processing to reduce log noise.

**Handlers** (`handlers.py`):
    Context-aware help for common Python errors (ImportError,
    AttributeError, TypeError).

**Recovery** (`recovery.py`):
    Graceful degradation patterns and error recovery utilities.

**Reporter** (`reporter.py`):
    CLI error report formatting utilities.

**Traceback** (`traceback/`):
    Configurable traceback rendering with multiple verbosity levels.

Usage Examples:
===============

Basic error with code and context:
    >>> from bengal.errors import BengalRenderingError, ErrorCode
    >>>
    >>> raise BengalRenderingError(
    ...     "Template not found: single.html",
    ...     code=ErrorCode.R001,
    ...     file_path=Path("content/post.md"),
    ...     suggestion="Check templates/ directory",
    ... )

Get actionable suggestion:
    >>> from bengal.errors import get_suggestion
    >>>
    >>> suggestion = get_suggestion("template", "not_found")
    >>> print(suggestion.fix)
    >>> print(suggestion.after_snippet)

Track errors across session:
    >>> from bengal.errors import record_error, get_session
    >>>
    >>> pattern_info = record_error(error, file_path="content/post.md")
    >>> if pattern_info["is_recurring"]:
    ...     print("This error has occurred before")
    >>>
    >>> summary = get_session().get_summary()

Dev server error with file changes:
    >>> from bengal.errors import create_dev_error
    >>>
    >>> context = create_dev_error(
    ...     error,
    ...     changed_files=[changed_file],
    ...     last_successful_build=last_build_time,
    ... )
    >>> print(context.get_likely_cause())
    >>> print(context.quick_actions)

Investigation helpers:
    >>> try:
    ...     render_page(page)
    ... except BengalError as e:
    ...     print("Investigation commands:")
    ...     for cmd in e.get_investigation_commands():
    ...         print(f"  {cmd}")
    ...     print("Related test files:")
    ...     for path in e.get_related_test_files():
    ...         print(f"  {path}")
"""

from __future__ import annotations

# Error aggregation
from bengal.errors.aggregation import (
    ErrorAggregator,
    extract_error_context,
)

# Error codes
from bengal.errors.codes import (
    ErrorCode,
    get_codes_by_category,
    get_error_code_by_name,
)

# Context enrichment
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

# Exception classes
from bengal.errors.exceptions import (
    BengalAssetError,
    BengalCacheError,
    BengalConfigError,
    BengalContentError,
    BengalDiscoveryError,
    BengalError,
    BengalRenderingError,
    BengalServerError,
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

__all__ = [
    # ============================================================
    # Error Codes
    # ============================================================
    "ErrorCode",
    "get_error_code_by_name",
    "get_codes_by_category",
    # ============================================================
    # Exceptions
    # ============================================================
    "BengalError",
    "BengalConfigError",
    "BengalContentError",
    "BengalRenderingError",
    "BengalDiscoveryError",
    "BengalCacheError",
    "BengalServerError",
    "BengalAssetError",
    # ============================================================
    # Context
    # ============================================================
    "BuildPhase",
    "ErrorSeverity",
    "ErrorContext",
    "ErrorDebugPayload",
    "RelatedFile",
    "enrich_error",
    "get_context_from_exception",
    "create_rendering_context",
    "create_discovery_context",
    "create_config_context",
    # ============================================================
    # Dev Server
    # ============================================================
    "DevServerErrorContext",
    "DevServerState",
    "FileChange",
    "create_dev_error",
    "get_dev_server_state",
    "reset_dev_server_state",
    # ============================================================
    # Session Tracking
    # ============================================================
    "ErrorSession",
    "ErrorPattern",
    "ErrorOccurrence",
    "get_session",
    "reset_session",
    "record_error",
    # ============================================================
    # Suggestions
    # ============================================================
    "ActionableSuggestion",
    "get_suggestion",
    "get_suggestion_dict",
    "format_suggestion",
    "format_suggestion_full",
    "enhance_error_context",
    "get_attribute_error_suggestion",
    "get_all_suggestions_for_category",
    "search_suggestions",
    # ============================================================
    # Aggregation
    # ============================================================
    "ErrorAggregator",
    "extract_error_context",
    # ============================================================
    # Handlers
    # ============================================================
    "ContextAwareHelp",
    "get_context_aware_help",
    # ============================================================
    # Recovery
    # ============================================================
    "with_error_recovery",
    "error_recovery_context",
    "recover_file_processing",
    # ============================================================
    # Reporter
    # ============================================================
    "format_error_report",
    "format_error_summary",
]
