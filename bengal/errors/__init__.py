"""
Centralized error handling package for Bengal.

This package consolidates all error-related utilities:

- **exceptions**: Base exception classes (BengalError and subclasses)
- **context**: ErrorContext dataclass and enrichment utilities
- **aggregation**: Batch error processing to reduce log noise
- **suggestions**: Actionable suggestions for common errors
- **handlers**: Runtime introspection for Python errors
- **recovery**: Graceful degradation patterns
- **reporter**: CLI error report formatting
- **traceback**: Traceback rendering and configuration

Usage:
    from bengal.errors import BengalError, BengalConfigError
    from bengal.errors import ErrorAggregator, extract_error_context
    from bengal.errors import get_suggestion, format_suggestion
"""

from __future__ import annotations

# Error aggregation
from bengal.errors.aggregation import (
    ErrorAggregator,
    extract_error_context,
)

# Context enrichment
from bengal.errors.context import (
    ErrorContext,
    enrich_error,
    get_context_from_exception,
)

# Exception classes
from bengal.errors.exceptions import (
    BengalCacheError,
    BengalConfigError,
    BengalContentError,
    BengalDiscoveryError,
    BengalError,
    BengalRenderingError,
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

# Actionable suggestions
from bengal.errors.suggestions import (
    enhance_error_context,
    format_suggestion,
    get_attribute_error_suggestion,
    get_suggestion,
)

__all__ = [
    # Exceptions
    "BengalError",
    "BengalConfigError",
    "BengalContentError",
    "BengalRenderingError",
    "BengalDiscoveryError",
    "BengalCacheError",
    # Context
    "ErrorContext",
    "enrich_error",
    "get_context_from_exception",
    # Aggregation
    "ErrorAggregator",
    "extract_error_context",
    # Suggestions
    "get_suggestion",
    "format_suggestion",
    "enhance_error_context",
    "get_attribute_error_suggestion",
    # Handlers
    "ContextAwareHelp",
    "get_context_aware_help",
    # Recovery
    "with_error_recovery",
    "error_recovery_context",
    "recover_file_processing",
    # Reporter
    "format_error_report",
    "format_error_summary",
]
