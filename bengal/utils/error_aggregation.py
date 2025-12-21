"""
Error aggregation utilities for reducing noise in batch processing.

When processing many items (pages, assets, files) in loops, similar errors
can create overwhelming noise. This module provides utilities to aggregate
similar errors and provide concise summaries.

Usage:
    from bengal.utils.error_aggregation import ErrorAggregator
    
    aggregator = ErrorAggregator(total_items=len(pages))
    
    for page in pages:
        try:
            process(page)
        except Exception as e:
            aggregator.add_error(e, context={"page": page})
    
    aggregator.log_summary(threshold=5)  # Only aggregate if 5+ errors
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
        Log error summary if threshold is exceeded.
        
        Args:
            logger: Logger instance for logging
            threshold: Minimum number of errors before aggregating
            error_type: Type of error for logging context (e.g., "rendering", "assets")
        """
        total_errors = sum(self.error_counts.values())
        
        if total_errors == 0:
            return
        
        # If below threshold, log individually (already done by caller)
        # This method is for summary logging when threshold exceeded
        if total_errors < threshold:
            return
        
        # Sort by count (most common first)
        sorted_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        # Log summary
        logger.error(
            f"{error_type}_errors_summary",
            total_errors=total_errors,
            unique_error_types=len(self.error_counts),
            total_items=self.total_items,
            error_rate=f"{(total_errors / self.total_items * 100):.1f}%",
            top_errors=sorted_errors[:10],  # Top 10 most common errors
        )
        
        # Log details for top 3 errors with sample contexts
        for error_sig, count in sorted_errors[:3]:
            percentage = (count / self.total_items * 100)
            
            # Extract sample context if available
            sample_contexts = self.error_contexts.get(error_sig, [])
            
            logger.error(
                f"{error_type}_error_pattern",
                pattern=error_sig,
                count=count,
                percentage=f"{percentage:.1f}%",
                sample_contexts=sample_contexts[:2],  # Show 2 sample contexts
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
    Extract rich context from error for better logging.
    
    If error is a TemplateRenderError, extracts template name, line number, etc.
    Otherwise, returns basic error info.
    
    Args:
        error: Exception that occurred
        item: Item being processed (Page, Asset, etc.) for context
        
    Returns:
        Dictionary with error context for logging
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
        from bengal.utils.exceptions import BengalError
        
        if isinstance(error, BengalError):
            if hasattr(error, "file_path") and error.file_path:
                context["file_path"] = str(error.file_path)
            if hasattr(error, "line_number") and error.line_number:
                context["line_number"] = error.line_number
            if hasattr(error, "suggestion") and error.suggestion:
                context["suggestion"] = error.suggestion
    except ImportError:
        # Utils module not available, skip BengalError handling
        pass
    
    return context

