"""
Notification helpers for Bengal dashboards.

Provides toast notification helpers for common events:
- Build complete/failed
- File changed (during serve)
- Health issues found

Uses Textual's built-in notify() system with Bengal theming.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.themes.tokens import BENGAL_MASCOT

if TYPE_CHECKING:
    from bengal.cli.dashboard.base import BengalDashboard


def notify_build_complete(
    app: BengalDashboard,
    duration_ms: float,
    pages: int,
    success: bool = True,
) -> None:
    """
    Show build complete notification.

    Args:
        app: The Textual app instance
        duration_ms: Build duration in milliseconds
        pages: Number of pages built
        success: Whether build succeeded
    """
    duration_s = duration_ms / 1000
    mascot = BENGAL_MASCOT.cat if success else BENGAL_MASCOT.mouse

    if success:
        app.notify(
            f"{mascot}  Built {pages} pages in {duration_s:.2f}s",
            title="Build Complete",
            severity="information",
        )
    else:
        app.notify(
            f"{mascot}  Build failed after {duration_s:.2f}s",
            title="Build Failed",
            severity="error",
        )


def notify_file_changed(
    app: BengalDashboard,
    path: str,
    change_type: str,
) -> None:
    """
    Show file changed notification.

    Args:
        app: The Textual app instance
        path: Path to the changed file
        change_type: Type of change (created, modified, deleted)
    """
    # Shorten path for display
    from pathlib import Path

    short_path = Path(path).name

    icons = {
        "created": "+",
        "modified": "~",
        "deleted": "-",
    }
    icon = icons.get(change_type, "?")

    app.notify(
        f"{icon} {short_path}",
        title="File Changed",
        severity="information",
        timeout=2,  # Quick notification
    )


def notify_rebuild_triggered(
    app: BengalDashboard,
    changed_files: int,
) -> None:
    """
    Show rebuild triggered notification.

    Args:
        app: The Textual app instance
        changed_files: Number of files that changed
    """
    plural = "s" if changed_files != 1 else ""
    app.notify(
        f"Rebuilding ({changed_files} file{plural} changed)...",
        title="Rebuild",
        severity="information",
        timeout=3,
    )


def notify_health_issues(
    app: BengalDashboard,
    errors: int,
    warnings: int,
) -> None:
    """
    Show health issues notification.

    Args:
        app: The Textual app instance
        errors: Number of errors found
        warnings: Number of warnings found
    """
    total = errors + warnings

    if total == 0:
        app.notify(
            f"{BENGAL_MASCOT.cat}  No issues found!",
            title="Health Check",
            severity="information",
        )
    elif errors > 0:
        app.notify(
            f"{BENGAL_MASCOT.mouse}  {errors} errors, {warnings} warnings",
            title="Health Issues",
            severity="error",
        )
    else:
        app.notify(
            f"{BENGAL_MASCOT.cat}  {warnings} warnings (no errors)",
            title="Health Check",
            severity="warning",
        )


def notify_server_started(
    app: BengalDashboard,
    url: str,
) -> None:
    """
    Show server started notification.

    Args:
        app: The Textual app instance
        url: Server URL
    """
    app.notify(
        f"{BENGAL_MASCOT.cat}  Server running at {url}",
        title="Dev Server",
        severity="information",
    )


def notify_error(
    app: BengalDashboard,
    message: str,
    title: str = "Error",
) -> None:
    """
    Show a generic error notification.

    Args:
        app: The Textual app instance
        message: Error message
        title: Notification title
    """
    app.notify(
        f"{BENGAL_MASCOT.mouse}  {message}",
        title=title,
        severity="error",
    )
