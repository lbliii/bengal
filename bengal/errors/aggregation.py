"""
Error aggregation utilities for reducing noise in batch processing.

When processing many items (pages, assets, files) in loops, similar errors
can create overwhelming noise. This module provides utilities to aggregate
similar errors and provide concise summaries.

**When to Use Error Aggregation:**

✅ **DO use aggregation when:**
- Processing 10+ items in a loop
- Similar errors are likely to occur multiple times
- Individual error details are less important than patterns
- Examples: Rendering pages, processing assets, validating content

❌ **DON'T use aggregation when:**
- Processing < 10 items (individual errors are manageable)
- Each error is unique and requires individual attention
- Errors are rare (< threshold)
- Examples: Post-processing tasks (usually < 5 tasks), one-off operations

**Usage Pattern:**

```python
from bengal.errors import ErrorAggregator, extract_error_context

# Initialize aggregator
aggregator = ErrorAggregator(total_items=len(items))

# Process items and collect errors
for item in items:
    try:
        process(item)
    except Exception as e:
        # Extract rich context
        context = extract_error_context(e, item)

        # Log individual error (always log for debugging)
        logger.error("processing_error", **context)

        # Add to aggregator for summary
        aggregator.add_error(e, context=context)

# Log summary if threshold exceeded (reduces noise)
aggregator.log_summary(logger, threshold=5, error_type="processing")
```

**See Also:**
- `bengal/orchestration/render.py` - Example usage in page rendering
- `bengal/orchestration/asset.py` - Example usage in asset processing
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.utils.logger import Logger


class ErrorAggregator:
    """
    Aggregates similar errors during batch processing to reduce noise.

    Groups errors by signature (error message + context) and provides
    summary logging when threshold is exceeded.

    Attributes:
        total_items: Total number of items being processed
        error_counts: Dictionary mapping error signatures to counts
        error_contexts: Dictionary mapping error signatures to sample contexts
        max_context_samples: Maximum number of sample contexts to keep per error type

    Example:
        >>> aggregator = ErrorAggregator(total_items=100)
        >>> for item in items:
        ...     try:
        ...         process(item)
        ...     except Exception as e:
        ...         aggregator.add_error(e, context={"item": item})
        >>> aggregator.log_summary(threshold=5, logger=logger)
    """

    def __init__(
        self,
        total_items: int,
        *,
        max_context_samples: int = 3,
    ) -> None:
        """
        Initialize error aggregator.

        Args:
            total_items: Total number of items being processed
            max_context_samples: Maximum sample contexts to keep per error type
        """
        self.total_items = total_items
        self.error_counts: dict[str, int] = defaultdict(int)
        self.error_contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.max_context_samples = max_context_samples
        self._logged_samples: dict[str, int] = defaultdict(
            int
        )  # Track how many samples we've logged per error type

    def add_error(
        self,
        error: Exception,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Add an error to the aggregator.

        Args:
            error: Exception that occurred
            context: Optional context dictionary (e.g., {"page": page, "file": file})
        """
        # Generate error signature (error message + type)
        error_signature = self._generate_signature(error, context)

        # Increment count
        self.error_counts[error_signature] += 1

        # Store sample context (keep only first N samples)
        if context and len(self.error_contexts[error_signature]) < self.max_context_samples:
            self.error_contexts[error_signature].append(context)

    def should_log_individual(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
        threshold: int = 5,
        max_samples: int = 3,
    ) -> bool:
        """
        Determine if individual error should be logged.

        Returns True if we should log this individual error (below threshold or first samples).
        Returns False if we should suppress individual logging (will aggregate).

        Args:
            error: Exception that occurred
            context: Optional context dictionary
            threshold: Minimum number of errors before aggregating
            max_samples: Maximum number of individual errors to log per error type

        Returns:
            True if should log individual error, False if should suppress
        """
        total_errors = sum(self.error_counts.values())

        # If below threshold, always log individually
        if total_errors < threshold:
            return True

        # If above threshold, only log first few samples of each error type
        error_signature = self._generate_signature(error, context)
        samples_logged = self._logged_samples[error_signature]

        # Log if we haven't exceeded sample limit for this error type
        if samples_logged < max_samples:
            self._logged_samples[error_signature] += 1
            return True

        # Suppress - we've already logged enough samples of this error type
        return False

    def _generate_signature(
        self,
        error: Exception,
        context: dict[str, Any] | None,
    ) -> str:
        """
        Generate error signature for grouping similar errors.

        Args:
            error: Exception that occurred
            context: Optional context dictionary

        Returns:
            Error signature string for grouping
        """
        # Start with error type and message
        signature_parts = [type(error).__name__, str(error)]

        # Add context keys that help identify error pattern
        if context:
            # Include template name if available (common in rendering errors)
            if "template_name" in context:
                signature_parts.insert(0, context["template_name"])
            # Include operation if available
            if "operation" in context:
                signature_parts.insert(0, context["operation"])

        return ":".join(signature_parts)

    def log_summary(
        self,
        logger: Logger,
        *,
        threshold: int = 5,
        error_type: str = "processing",
    ) -> None:
        """
        Log compact error summary if threshold is exceeded.

        Produces a single consolidated log entry instead of multiple entries,
        reducing noise while preserving actionable information.

        Args:
            logger: Logger instance for logging
            threshold: Minimum number of errors before aggregating
            error_type: Type of error for logging context (e.g., "rendering", "assets")
        """
        total_errors = sum(self.error_counts.values())

        if total_errors == 0:
            return

        # If below threshold, errors were logged individually
        if total_errors < threshold:
            return

        # Sort by count (most common first)
        sorted_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Build compact top errors summary with suggestions
        top_error_details = []
        for error_sig, count in sorted_errors[:3]:
            percentage = count / self.total_items * 100
            sample_contexts = self.error_contexts.get(error_sig, [])

            # Extract suggestion if available in any sample context
            suggestion = None
            for ctx in sample_contexts[:1]:
                if "suggestion" in ctx:
                    suggestion = ctx["suggestion"]
                    break

            detail = {
                "pattern": error_sig,
                "count": count,
                "percentage": f"{percentage:.1f}%",
            }
            if suggestion:
                detail["fix"] = suggestion
            top_error_details.append(detail)

        # Single consolidated log entry
        logger.error(
            f"{error_type}_errors_summary",
            total_errors=total_errors,
            unique_error_types=len(self.error_counts),
            total_items=self.total_items,
            error_rate=f"{(total_errors / self.total_items * 100):.1f}%",
            top_errors=top_error_details,
        )

    def get_summary(self) -> dict[str, Any]:
        """
        Get error summary without logging.

        Returns:
            Dictionary with error summary statistics
        """
        total_errors = sum(self.error_counts.values())

        return {
            "total_errors": total_errors,
            "unique_error_types": len(self.error_counts),
            "total_items": self.total_items,
            "error_rate": total_errors / self.total_items if self.total_items > 0 else 0.0,
            "error_counts": dict(self.error_counts),
        }


def extract_error_context(error: Exception, item: Any | None = None) -> dict[str, Any]:
    """
    Extract rich context from an exception for logging and aggregation.

    Analyzes the exception and optional item to build a comprehensive
    context dictionary. Handles special cases for Bengal error types:

    - **TemplateRenderError**: Extracts template name, line number, path
    - **BengalError**: Extracts file path, line number, suggestion
    - **AttributeError**: Adds actionable suggestions for common patterns

    The returned context is suitable for structured logging and for
    feeding into ``ErrorAggregator`` for pattern detection.

    Args:
        error: Exception that occurred during processing.
        item: Optional item being processed (Page, Asset, etc.) for
            additional context. Looks for ``source_path``, ``path``,
            and ``name`` attributes.

    Returns:
        Dictionary with error context including:

        - ``error``: Error message string
        - ``error_type``: Exception class name
        - ``source_path``: Path to source file (if available)
        - ``template_name``: Template name (for rendering errors)
        - ``template_line``: Line number in template (if available)
        - ``suggestion``: Actionable fix suggestion (if available)

    Example:
        >>> try:
        ...     render_page(page)
        ... except Exception as e:
        ...     context = extract_error_context(e, page)
        ...     logger.error("rendering_failed", **context)
    """
    context: dict[str, Any] = {
        "error": str(error),
        "error_type": type(error).__name__,
    }

    # Add item context if available
    if item:
        # Try common attributes
        if hasattr(item, "source_path"):
            context["source_path"] = str(item.source_path)
        if hasattr(item, "path"):
            context["path"] = str(item.path)
        if hasattr(item, "name"):
            context["name"] = str(item.name)

    # Extract rich context from TemplateRenderError if available
    try:
        from bengal.rendering.errors import TemplateRenderError

        if isinstance(error, TemplateRenderError):
            ctx = error.template_context
            context["template_name"] = ctx.template_name
            if ctx.line_number:
                context["template_line"] = ctx.line_number
            if ctx.template_path:
                context["template_path"] = str(ctx.template_path)
            if error.page_source:
                context["page_source"] = str(error.page_source)
            if error.suggestion:
                context["suggestion"] = error.suggestion
            # Override error message with more specific one
            context["error"] = error.message
    except ImportError:
        # Rendering module not available, skip TemplateRenderError handling
        pass

    # Extract context from BengalError if available
    try:
        from bengal.errors.exceptions import BengalError

        if isinstance(error, BengalError):
            if hasattr(error, "file_path") and error.file_path:
                context["file_path"] = str(error.file_path)
            if hasattr(error, "line_number") and error.line_number:
                context["line_number"] = error.line_number
            if hasattr(error, "suggestion") and error.suggestion:
                context["suggestion"] = error.suggestion
    except ImportError:
        # Errors module not available, skip BengalError handling
        pass

    # Add actionable suggestions for common AttributeError patterns
    if isinstance(error, AttributeError) and "suggestion" not in context:
        from bengal.errors.suggestions import get_attribute_error_suggestion

        error_msg = str(error)
        suggestion = get_attribute_error_suggestion(error_msg)
        if suggestion:
            context["suggestion"] = suggestion

    return context
