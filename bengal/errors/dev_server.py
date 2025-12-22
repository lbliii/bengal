"""
Dev server error context for hot-reload aware error handling.

This module provides enhanced error context specifically for development
server scenarios where files change frequently, errors may be transient,
and users need quick feedback on what changed and how to fix it.

Key Features
============

- **File Change Tracking**: Records which files changed before an error
- **Likely Cause Detection**: Identifies the most likely cause based on changes
- **Auto-Fix Suggestions**: Provides automated fix commands when possible
- **Rollback Commands**: Generates git commands to undo recent changes
- **Quick Actions**: Lists actionable steps for common error patterns
- **Error History**: Tracks whether errors are new or recurring

Components
==========

**FileChange**
    Record of a file change with path, type (modified/created/deleted),
    timestamp, and relevant line numbers.

**DevServerErrorContext**
    Extended ErrorContext with dev server-specific fields for file changes,
    error history, hot-reload state, and auto-fix information.

**DevServerState**
    Singleton tracking dev server state across hot reloads for richer
    error context and pattern detection.

Usage
=====

Create dev server error context::

    from bengal.errors.dev_server import create_dev_error

    context = create_dev_error(
        error,
        changed_files=[changed_file],
        last_successful_build=last_build_time,
    )
    print(context.get_likely_cause())
    print(context.quick_actions)

Track dev server state::

    from bengal.errors.dev_server import get_dev_server_state

    state = get_dev_server_state()
    state.record_success()  # After successful build
    is_new = state.record_failure(error_signature)

See Also
========

- ``bengal/server/`` - Dev server implementation
- ``bengal/errors/context.py`` - Base ErrorContext class
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors.context import BuildPhase, ErrorContext

if TYPE_CHECKING:
    pass


@dataclass
class FileChange:
    """
    Record of a file change that may have caused an error.

    Attributes:
        path: Path to the changed file
        change_type: Type of change (modified, created, deleted)
        timestamp: When the change was detected
        relevant_lines: Line numbers that changed (if available)
    """

    path: Path
    change_type: str = "modified"  # modified, created, deleted, renamed
    timestamp: datetime = field(default_factory=datetime.now)
    relevant_lines: list[int] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.change_type}: {self.path}"


@dataclass
class DevServerErrorContext(ErrorContext):
    """
    Enhanced error context for dev server errors.

    Extends ErrorContext with information about:
    - Recent file changes that may have caused the error
    - Whether this is a new or recurring error
    - Auto-fix availability
    - Hot-reload state
    """

    # File change tracking
    changed_files: list[FileChange] = field(default_factory=list)
    trigger_file: Path | None = None  # File change that triggered rebuild

    # Error history
    is_new_error: bool = True
    error_first_seen: datetime | None = None
    last_successful_build: datetime | None = None
    builds_since_success: int = 0

    # Hot-reload state
    is_hot_reload: bool = True
    reload_count: int = 0

    # Auto-fix info
    auto_fixable: bool = False
    auto_fix_description: str | None = None
    auto_fix_command: str | None = None

    # Quick actions
    quick_actions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Set dev server specific defaults."""
        if self.build_phase is None:
            self.build_phase = BuildPhase.SERVER
        if self.subsystem is None:
            self.subsystem = "server"

    def add_changed_file(
        self,
        path: Path | str,
        change_type: str = "modified",
        relevant_lines: list[int] | None = None,
    ) -> None:
        """
        Add a file change that may have caused the error.

        Args:
            path: Path to the changed file
            change_type: Type of change
            relevant_lines: Specific lines that changed
        """
        self.changed_files.append(
            FileChange(
                path=Path(path) if isinstance(path, str) else path,
                change_type=change_type,
                relevant_lines=relevant_lines or [],
            )
        )

    def get_likely_cause(self) -> str | None:
        """
        Determine the most likely cause of the error based on changes.

        Returns:
            Description of likely cause, or None
        """
        if not self.changed_files:
            return None

        # If only one file changed, it's likely the cause
        if len(self.changed_files) == 1:
            change = self.changed_files[0]
            return f"Recent {change.change_type} of {change.path}"

        # If error file is in changed files, that's the cause
        if self.file_path:
            for change in self.changed_files:
                if change.path == self.file_path:
                    return f"Recent {change.change_type} of {change.path}"

        # Multiple changes - summarize
        types = set(c.change_type for c in self.changed_files)
        return f"Recent changes to {len(self.changed_files)} files ({', '.join(types)})"

    def get_rollback_suggestion(self) -> str | None:
        """
        Generate rollback suggestion based on changes.

        Returns:
            Git command to undo changes, or None
        """
        if not self.changed_files:
            return None

        if len(self.changed_files) == 1:
            path = self.changed_files[0].path
            return f"git checkout -- {path}"

        # Multiple files - suggest stash
        return "git stash  # Stash all changes to test if they caused the error"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        base = super().to_dict()
        base.update(
            {
                "changed_files": [str(f) for f in self.changed_files],
                "trigger_file": str(self.trigger_file) if self.trigger_file else None,
                "is_new_error": self.is_new_error,
                "error_first_seen": self.error_first_seen.isoformat()
                if self.error_first_seen
                else None,
                "last_successful_build": (
                    self.last_successful_build.isoformat() if self.last_successful_build else None
                ),
                "builds_since_success": self.builds_since_success,
                "is_hot_reload": self.is_hot_reload,
                "reload_count": self.reload_count,
                "auto_fixable": self.auto_fixable,
                "auto_fix_description": self.auto_fix_description,
                "auto_fix_command": self.auto_fix_command,
                "quick_actions": self.quick_actions,
                "likely_cause": self.get_likely_cause(),
            }
        )
        return base


def create_dev_error(
    error: Exception,
    *,
    changed_files: list[Path | str] | None = None,
    trigger_file: Path | str | None = None,
    last_successful_build: datetime | None = None,
) -> DevServerErrorContext:
    """
    Create a dev server error context from an exception.

    Convenience function for creating DevServerErrorContext from an exception
    with common dev server context.

    Args:
        error: Exception that occurred
        changed_files: Files that changed since last successful build
        trigger_file: File change that triggered the rebuild
        last_successful_build: When the last successful build completed

    Returns:
        DevServerErrorContext with extracted and provided context
    """
    # Extract basic context from error
    file_path = getattr(error, "file_path", None)
    line_number = getattr(error, "line_number", None)
    suggestion = getattr(error, "suggestion", None)
    error_code = getattr(error, "code", None)
    build_phase = getattr(error, "build_phase", None)

    # Create context
    context = DevServerErrorContext(
        file_path=file_path,
        line_number=line_number,
        suggestion=suggestion,
        error_code=error_code,
        build_phase=build_phase or BuildPhase.SERVER,
        original_error=error,
        trigger_file=Path(trigger_file) if isinstance(trigger_file, str) else trigger_file,
        last_successful_build=last_successful_build,
    )

    # Add changed files
    if changed_files:
        for f in changed_files:
            context.add_changed_file(f)

    # Generate quick actions
    context.quick_actions = _generate_quick_actions(error, context)

    # Check for auto-fixable errors
    _check_auto_fixable(error, context)

    return context


def _generate_quick_actions(error: Exception, context: DevServerErrorContext) -> list[str]:
    """
    Generate quick action suggestions for dev server errors.

    Args:
        error: The exception
        context: Dev server error context

    Returns:
        List of quick action strings
    """
    actions: list[str] = []

    # Template not found
    if "TemplateNotFound" in type(error).__name__ or "template" in str(error).lower():
        actions.append("Check templates/ and themes/*/templates/ directories")

    # YAML parse error
    if "YAML" in str(error) or "yaml" in str(error).lower():
        actions.append(
            "Validate YAML with: python -c \"import yaml; yaml.safe_load(open('<file>'))\""
        )

    # Undefined variable
    if "UndefinedError" in type(error).__name__:
        actions.append("Add | default('') filter to make variable optional")

    # Rollback suggestion
    rollback = context.get_rollback_suggestion()
    if rollback:
        actions.append(f"Rollback changes: {rollback}")

    # Clear cache suggestion for recurring errors
    if not context.is_new_error:
        actions.append("Clear cache: rm -rf .bengal/cache/")

    return actions


def _check_auto_fixable(error: Exception, context: DevServerErrorContext) -> None:
    """
    Check if error is auto-fixable and set context fields.

    Args:
        error: The exception
        context: Dev server error context to update
    """
    error_msg = str(error).lower()

    # Missing optional variable - can suggest default filter
    if "undefined" in error_msg and "variable" in error_msg:
        context.auto_fixable = True
        context.auto_fix_description = "Add default filter to template variable"
        # Extract variable name if possible
        import re

        match = re.search(r"'(\w+)'", str(error))
        if match:
            var = match.group(1)
            context.auto_fix_command = (
                f"# In template, change: {{{{ {var} }}}} to: {{{{ {var} | default('') }}}}"
            )

    # Cache corruption
    if "cache" in error_msg and ("corrupt" in error_msg or "invalid" in error_msg):
        context.auto_fixable = True
        context.auto_fix_description = "Clear corrupted cache"
        context.auto_fix_command = "rm -rf .bengal/cache/"

    # Port in use
    if "port" in error_msg and ("in use" in error_msg or "already" in error_msg):
        context.auto_fixable = True
        context.auto_fix_description = "Use different port"
        context.auto_fix_command = "bengal serve --port 8080"


@dataclass
class DevServerState:
    """
    Track dev server state for error context enrichment.

    Maintains state across hot reloads to provide richer error context
    and detect recurring error patterns. This is a singleton managed
    via ``get_dev_server_state()`` and ``reset_dev_server_state()``.

    Attributes:
        last_successful_build: Timestamp of last successful build.
        builds_since_success: Count of failed builds since last success.
        reload_count: Total number of hot reloads in this session.
        error_history: Map of error signatures to first occurrence time.

    Example:
        >>> state = get_dev_server_state()
        >>> state.record_success()  # After successful build
        >>> is_new = state.record_failure("R001::template not found")
        >>> print(f"New error: {is_new}")
    """

    last_successful_build: datetime | None = None
    builds_since_success: int = 0
    reload_count: int = 0
    error_history: dict[str, datetime] = field(default_factory=dict)

    def record_success(self) -> None:
        """
        Record a successful build.

        Updates ``last_successful_build`` timestamp and resets
        ``builds_since_success`` counter to zero.
        """
        self.last_successful_build = datetime.now()
        self.builds_since_success = 0

    def record_failure(self, error_signature: str) -> bool:
        """
        Record a failed build.

        Increments ``builds_since_success`` and tracks the error
        signature for recurring error detection.

        Args:
            error_signature: Unique signature identifying the error pattern
                (e.g., "R001::template not found").

        Returns:
            True if this is a new error (first occurrence),
            False if this error has occurred before.
        """
        self.builds_since_success += 1
        is_new = error_signature not in self.error_history
        self.error_history[error_signature] = datetime.now()
        return is_new

    def record_reload(self) -> None:
        """
        Record a hot reload event.

        Increments the ``reload_count`` counter.
        """
        self.reload_count += 1

    def get_context_for_error(self, error: Exception) -> dict[str, Any]:
        """
        Get dev server context information for an error.

        Generates an error signature and checks if the error has
        occurred before in this session.

        Args:
            error: The exception to get context for.

        Returns:
            Dictionary with dev server state:

            - ``is_new_error``: Whether this is a new error
            - ``last_successful_build``: Timestamp of last success
            - ``builds_since_success``: Failed build count
            - ``reload_count``: Total reload count
            - ``error_first_seen``: When error was first seen (if recurring)
        """
        # Generate signature
        signature = f"{type(error).__name__}:{str(error)[:50]}"
        is_new = signature not in self.error_history

        return {
            "is_new_error": is_new,
            "last_successful_build": self.last_successful_build,
            "builds_since_success": self.builds_since_success,
            "reload_count": self.reload_count,
            "error_first_seen": self.error_history.get(signature),
        }


# Global dev server state
_dev_server_state: DevServerState | None = None


def get_dev_server_state() -> DevServerState:
    """Get the current dev server state (singleton)."""
    global _dev_server_state
    if _dev_server_state is None:
        _dev_server_state = DevServerState()
    return _dev_server_state


def reset_dev_server_state() -> DevServerState:
    """Reset the dev server state."""
    global _dev_server_state
    _dev_server_state = DevServerState()
    return _dev_server_state
