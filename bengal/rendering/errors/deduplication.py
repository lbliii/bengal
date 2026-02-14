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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .exceptions import TemplateRenderError


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

    # Key: (template_name, line_number, error_type, message_prefix)
    # Value: list of page sources that had this error
    seen_errors: dict[tuple[str, int | None, str, str], list[str]] = field(default_factory=dict)
    # Maximum errors to show per unique error signature
    max_display_per_error: int = 2

    def _get_error_key(self, error: TemplateRenderError) -> tuple[str, int | None, str, str]:
        """Generate a key for error deduplication."""
        # Use first 50 chars of message to group similar errors
        msg_prefix = str(error.message)[:50] if error.message else ""
        return (
            error.template_context.template_name,
            error.template_context.line_number,
            error.error_type,
            msg_prefix,
        )

    def should_display(self, error: TemplateRenderError) -> bool:
        """
        Check if this error should be displayed or suppressed.

        Returns True for the first N occurrences of each unique error,
        False for subsequent ones.
        """
        key = self._get_error_key(error)
        page_source = str(error.page_source) if error.page_source else "unknown"

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
                        template, line, error_type, _msg = key
                        extra = len(pages) - self.max_display_per_error
                        console.print(
                            f"   • [dim]{template}:{line}[/dim] ({error_type}): "
                            f"[yellow]+{extra} more page(s)[/yellow]"
                        )
                console.print()
                return
        except ImportError:
            pass

        # Fallback to click
        import click

        click.echo()
        click.secho(f"⚠️  {suppressed} similar error(s) suppressed", fg="yellow", bold=True)
        for key, pages in self.seen_errors.items():
            if len(pages) > self.max_display_per_error:
                template, line, error_type, _msg = key
                extra = len(pages) - self.max_display_per_error
                click.echo(f"   • {template}:{line} ({error_type}): +{extra} more page(s)")
        click.echo()

    def reset(self) -> None:
        """Reset the deduplicator for a new build."""
        self.seen_errors.clear()
