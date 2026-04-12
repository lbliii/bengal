"""
Error deduplication for template rendering.

This module provides the ErrorDeduplicator class that tracks and deduplicates
similar template errors across multiple pages to reduce noise in build output.

Classes:
    ErrorDeduplicator: Tracks errors by (template, line, type, message_prefix)
        and suppresses duplicates after a configurable threshold.

Usage:
    >>> dedup = ErrorDeduplicator()
    >>> if dedup.should_display(error):
    ...     display_template_error(error)
    >>> dedup.display_summary()
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .exceptions import TemplateRenderError


@dataclass(frozen=True, slots=True)
class ErrorDedupKey:
    """Key for error deduplication: (template, line, error_type, message_prefix)."""

    file_path: str
    line: int | None
    message: str
    category: str


@dataclass
class ErrorDeduplicator:
    """
    Tracks and deduplicates similar template errors across multiple pages.

    When the same error (same template, line, error type) occurs on multiple
    pages, only the first occurrence is displayed in full. Subsequent occurrences
    are counted and summarized at the end.

    Usage:
            >>> dedup = get_error_deduplicator()
            >>> if dedup.should_display(error):
            ...     display_template_error(error)
            >>> dedup.display_summary()

    """

    # Key: ErrorDedupKey (template, line, error_type, message_prefix)
    # Value: list of page sources that had this error
    seen_errors: dict[ErrorDedupKey, list[str]] = field(default_factory=dict)
    # Maximum errors to show per unique error signature
    max_display_per_error: int = 2
    # Thread-safety lock — protects seen_errors dict read+write in should_display
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def _get_error_key(self, error: TemplateRenderError) -> ErrorDedupKey:
        """Generate a key for error deduplication."""
        # Use first 50 chars of message to group similar errors
        msg_prefix = str(error.message)[:50] if error.message else ""
        return ErrorDedupKey(
            file_path=error.template_context.template_name,
            line=error.template_context.line_number,
            message=msg_prefix,
            category=error.error_type,
        )

    def should_display(self, error: TemplateRenderError) -> bool:
        """
        Check if this error should be displayed or suppressed.

        Returns True for the first N occurrences of each unique error,
        False for subsequent ones.
        """
        key = self._get_error_key(error)
        page_source = str(error.page_source) if error.page_source else "unknown"

        with self._lock:
            if key not in self.seen_errors:
                self.seen_errors[key] = []

            self.seen_errors[key].append(page_source)

            # Display if we haven't hit the limit yet
            return len(self.seen_errors[key]) <= self.max_display_per_error

    def get_suppressed_count(self) -> int:
        """Get total count of suppressed (not displayed) errors."""
        total = 0
        for pages in self.seen_errors.values():
            if len(pages) > self.max_display_per_error:
                total += len(pages) - self.max_display_per_error
        return total

    def display_summary(self) -> None:
        """Display summary of suppressed errors."""
        suppressed = self.get_suppressed_count()
        if suppressed == 0:
            return

        try:
            from bengal.utils.observability.rich_console import get_console, should_use_rich

            if should_use_rich():
                console = get_console()
                console.print()
                console.print(
                    f"[yellow bold]⚠️  {suppressed} similar error(s) suppressed[/yellow bold]"
                )

                # Show summary of each unique error
                for key, pages in self.seen_errors.items():
                    if len(pages) > self.max_display_per_error:
                        template, line, error_type = key.file_path, key.line, key.category
                        extra = len(pages) - self.max_display_per_error
                        console.print(
                            f"   • [dim]{template}:{line}[/dim] ({error_type}): "
                            f"[yellow]+{extra} more page(s)[/yellow]"
                        )
                console.print()
                return
        except ImportError:
            pass

        # Plain text fallback
        print()
        print(f"  {suppressed} similar error(s) suppressed")
        for key, pages in self.seen_errors.items():
            if len(pages) > self.max_display_per_error:
                template, line, error_type = key.file_path, key.line, key.category
                extra = len(pages) - self.max_display_per_error
                print(f"   • {template}:{line} ({error_type}): +{extra} more page(s)")
        print()

    def reset(self) -> None:
        """Reset the deduplicator for a new build."""
        self.seen_errors.clear()
