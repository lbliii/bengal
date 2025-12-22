"""
Session-level error tracking for pattern detection across builds.

This module provides error session tracking to detect patterns, identify
systemic issues, and provide investigation hints across builds.

Key Features
============

- **Pattern Detection**: Groups similar errors by signature to identify
  recurring patterns.
- **Systemic Issue Detection**: Identifies errors affecting multiple files
  (likely template or config issues).
- **Investigation Hints**: Generates actionable hints based on error patterns.
- **Session Statistics**: Provides comprehensive summary with error rates,
  phase distribution, and most affected files.
- **Dev Server Support**: Persists across hot reloads for continuous tracking.

Components
==========

**ErrorOccurrence**
    Record of a single error occurrence with timestamp and context.

**ErrorPattern**
    Aggregated pattern for similar errors with occurrence count and
    affected files.

**ErrorSession**
    Thread-safe session tracking with indexing by file, code, and phase.

Module Functions
================

- ``get_session()`` - Get the current session singleton
- ``reset_session()`` - Reset to a fresh session
- ``record_error()`` - Convenience function to record an error

Usage
=====

Record errors and detect patterns::

    from bengal.errors.session import get_session, record_error

    # Record an error
    pattern_info = record_error(error, file_path="content/post.md")

    # Check if error is recurring
    if pattern_info["is_recurring"]:
        print(f"This error has occurred {pattern_info['occurrence_number']} times")

Get session summary and hints::

    session = get_session()
    summary = session.get_summary()
    hints = session.get_investigation_hints()

    for hint in hints:
        print(hint)

See Also
========

- ``bengal/orchestration/build.py`` - Session usage in builds
- ``bengal/errors/aggregation.py`` - Error aggregation (different scope)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.errors.codes import ErrorCode


@dataclass
class ErrorOccurrence:
    """
    Record of a single error occurrence.

    Attributes:
        error_type: Type name of the exception
        error_message: Error message
        error_code: Bengal error code if available
        file_path: File where error occurred
        timestamp: When the error occurred
        build_phase: Build phase where error occurred
    """

    error_type: str
    error_message: str
    error_code: str | None = None
    file_path: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    build_phase: str | None = None


@dataclass
class ErrorPattern:
    """
    Aggregated pattern for similar errors.

    Attributes:
        signature: Unique signature for this error pattern
        occurrences: List of all occurrences
        first_file: File where error first occurred
        affected_files: Set of all affected files
    """

    signature: str
    occurrences: list[ErrorOccurrence] = field(default_factory=list)
    first_file: str | None = None
    affected_files: set[str] = field(default_factory=set)

    @property
    def count(self) -> int:
        """Number of occurrences of this pattern."""
        return len(self.occurrences)

    @property
    def is_recurring(self) -> bool:
        """Whether this pattern has occurred more than once."""
        return self.count > 1

    @property
    def is_systemic(self) -> bool:
        """Whether this pattern affects multiple files (systemic issue)."""
        return len(self.affected_files) > 2


class ErrorSession:
    """
    Track errors across a build session for pattern detection.

    Thread-safe error tracking that persists across incremental builds
    and dev server hot reloads. Errors are indexed by:

    - **Pattern signature**: Groups similar errors for recurrence detection
    - **File path**: Find all errors for a specific file
    - **Error code**: Find all errors with a specific Bengal error code
    - **Build phase**: Find all errors in a specific phase

    The session is a singleton accessed via ``get_session()``. Use
    ``reset_session()`` to start fresh (e.g., at start of new build).

    Attributes:
        _patterns: Map of error signatures to ErrorPattern objects.
        _errors_by_file: Index of errors by file path.
        _errors_by_code: Index of errors by error code.
        _errors_by_phase: Index of errors by build phase.
        _start_time: Session start timestamp.
        _total_errors: Total error count.

    Example:
        >>> session = get_session()
        >>> info = session.record(error, file_path="content/post.md")
        >>> print(f"Occurrence #{info['occurrence_number']}")
        >>> summary = session.get_summary()
        >>> hints = session.get_investigation_hints()
    """

    def __init__(self) -> None:
        """Initialize a new error session with empty indexes."""
        self._patterns: dict[str, ErrorPattern] = {}
        self._errors_by_file: dict[str, list[ErrorOccurrence]] = defaultdict(list)
        self._errors_by_code: dict[str, list[ErrorOccurrence]] = defaultdict(list)
        self._errors_by_phase: dict[str, list[ErrorOccurrence]] = defaultdict(list)
        self._lock = Lock()
        self._start_time = datetime.now()
        self._total_errors = 0

    def record(
        self,
        error: Exception,
        *,
        file_path: str | None = None,
        build_phase: str | None = None,
    ) -> dict[str, Any]:
        """
        Record an error and return pattern information.

        Args:
            error: Exception that occurred
            file_path: File where error occurred
            build_phase: Build phase where error occurred

        Returns:
            Pattern info dict with:
            - occurrence_number: How many times this pattern has occurred
            - is_recurring: Whether this is a repeat occurrence
            - is_systemic: Whether pattern affects multiple files
            - first_file: Where the error first occurred
            - affected_files_count: Number of files affected
        """
        with self._lock:
            # Extract error info
            error_type = type(error).__name__
            error_message = str(error)
            error_code: str | None = None

            if hasattr(error, "code") and error.code:
                error_code = str(error.code)

            if hasattr(error, "build_phase") and error.build_phase:
                build_phase = error.build_phase.value

            # Create occurrence record
            occurrence = ErrorOccurrence(
                error_type=error_type,
                error_message=error_message,
                error_code=error_code,
                file_path=file_path,
                build_phase=build_phase,
            )

            # Generate pattern signature
            signature = self._generate_signature(error)

            # Get or create pattern
            if signature not in self._patterns:
                self._patterns[signature] = ErrorPattern(
                    signature=signature,
                    first_file=file_path,
                )

            pattern = self._patterns[signature]
            pattern.occurrences.append(occurrence)
            if file_path:
                pattern.affected_files.add(file_path)

            # Index by file
            if file_path:
                self._errors_by_file[file_path].append(occurrence)

            # Index by code
            if error_code:
                self._errors_by_code[error_code].append(occurrence)

            # Index by phase
            if build_phase:
                self._errors_by_phase[build_phase].append(occurrence)

            self._total_errors += 1

            return {
                "occurrence_number": pattern.count,
                "is_recurring": pattern.is_recurring,
                "is_systemic": pattern.is_systemic,
                "first_file": pattern.first_file,
                "affected_files_count": len(pattern.affected_files),
                "signature": signature,
            }

    def _generate_signature(self, error: Exception) -> str:
        """
        Generate a unique signature for error pattern grouping.

        Args:
            error: Exception to generate signature for

        Returns:
            Signature string for pattern grouping
        """
        parts = [type(error).__name__]

        # Add error code if available
        if hasattr(error, "code") and error.code:
            parts.insert(0, str(error.code))

        # Normalize error message (remove file-specific parts)
        message = str(error)
        # Remove file paths from message
        import re

        message = re.sub(r"[/\\][^\s]+\.(md|html|yaml|py)", "<file>", message)
        # Remove line numbers
        message = re.sub(r"line \d+", "line <N>", message)
        # Truncate long messages
        if len(message) > 100:
            message = message[:100]

        parts.append(message)

        return "::".join(parts)

    def get_pattern_for_error(self, error: Exception) -> ErrorPattern | None:
        """
        Get the pattern for a specific error.

        Args:
            error: Exception to look up

        Returns:
            ErrorPattern if found, None otherwise
        """
        signature = self._generate_signature(error)
        return self._patterns.get(signature)

    def get_errors_for_file(self, file_path: str) -> list[ErrorOccurrence]:
        """
        Get all errors for a specific file.

        Args:
            file_path: Path to file

        Returns:
            List of ErrorOccurrence for that file
        """
        return self._errors_by_file.get(file_path, [])

    def get_errors_by_code(self, code: str | ErrorCode) -> list[ErrorOccurrence]:
        """
        Get all errors with a specific error code.

        Args:
            code: Error code to look up

        Returns:
            List of ErrorOccurrence with that code
        """
        code_str = str(code)
        return self._errors_by_code.get(code_str, [])

    def get_systemic_issues(self) -> list[ErrorPattern]:
        """
        Get patterns that appear to be systemic (affect multiple files).

        Returns:
            List of ErrorPattern that are systemic
        """
        return [p for p in self._patterns.values() if p.is_systemic]

    def get_most_common_errors(self, limit: int = 5) -> list[tuple[str, int]]:
        """
        Get the most common error patterns.

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of (signature, count) tuples, sorted by count
        """
        sorted_patterns = sorted(
            self._patterns.items(),
            key=lambda x: x[1].count,
            reverse=True,
        )
        return [(sig, pattern.count) for sig, pattern in sorted_patterns[:limit]]

    def get_summary(self) -> dict[str, Any]:
        """
        Get comprehensive session error summary.

        Returns:
            Dictionary with session statistics
        """
        duration = (datetime.now() - self._start_time).total_seconds()

        # Get phase distribution
        phase_counts = {phase: len(errors) for phase, errors in self._errors_by_phase.items()}

        # Get code distribution
        code_counts = {code: len(errors) for code, errors in self._errors_by_code.items()}

        # Get most affected files
        file_counts = sorted(
            [(f, len(e)) for f, e in self._errors_by_file.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        return {
            "total_errors": self._total_errors,
            "unique_patterns": len(self._patterns),
            "affected_files": len(self._errors_by_file),
            "session_duration_seconds": duration,
            "errors_per_minute": (self._total_errors / duration * 60) if duration > 0 else 0,
            "systemic_issues": len(self.get_systemic_issues()),
            "most_common_errors": self.get_most_common_errors(),
            "errors_by_phase": phase_counts,
            "errors_by_code": code_counts,
            "most_affected_files": file_counts,
            "recurring_errors": sum(1 for p in self._patterns.values() if p.is_recurring),
        }

    def get_investigation_hints(self) -> list[str]:
        """
        Generate investigation hints based on error patterns.

        Returns:
            List of actionable investigation hints
        """
        hints: list[str] = []

        # Check for systemic issues
        systemic = self.get_systemic_issues()
        if systemic:
            hints.append(
                f"🔍 Found {len(systemic)} systemic issue(s) affecting multiple files. "
                "Consider checking shared templates or configuration."
            )

        # Check for phase concentration
        phase_counts = {p: len(e) for p, e in self._errors_by_phase.items()}
        if phase_counts:
            max_phase = max(phase_counts, key=lambda k: phase_counts[k])
            if phase_counts[max_phase] > self._total_errors * 0.5:
                hints.append(
                    f"🎯 {phase_counts[max_phase]}/{self._total_errors} errors occurred in "
                    f"{max_phase} phase. Focus investigation there."
                )

        # Check for high recurrence
        recurring = [p for p in self._patterns.values() if p.count >= 3]
        if recurring:
            top = recurring[0]
            hints.append(
                f"⚠️ Error pattern '{top.signature[:50]}...' occurred {top.count} times. "
                f"First in: {top.first_file}"
            )

        # Check for code concentration
        code_counts = {c: len(e) for c, e in self._errors_by_code.items()}
        if code_counts:
            max_code = max(code_counts, key=lambda k: code_counts[k])
            if code_counts[max_code] >= 3:
                hints.append(
                    f"📋 Error code {max_code} occurred {code_counts[max_code]} times. "
                    "Check documentation for this error code."
                )

        return hints

    def clear(self) -> None:
        """Clear all recorded errors and reset session."""
        with self._lock:
            self._patterns.clear()
            self._errors_by_file.clear()
            self._errors_by_code.clear()
            self._errors_by_phase.clear()
            self._total_errors = 0
            self._start_time = datetime.now()


# Global session instance
_current_session: ErrorSession | None = None
_session_lock = Lock()


def get_session() -> ErrorSession:
    """
    Get the current error session (singleton).

    Returns:
        Current ErrorSession instance
    """
    global _current_session
    with _session_lock:
        if _current_session is None:
            _current_session = ErrorSession()
        return _current_session


def reset_session() -> ErrorSession:
    """
    Reset the error session (start fresh).

    Returns:
        New ErrorSession instance
    """
    global _current_session
    with _session_lock:
        _current_session = ErrorSession()
        return _current_session


def record_error(
    error: Exception,
    *,
    file_path: str | None = None,
    build_phase: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to record an error in the current session.

    Args:
        error: Exception that occurred
        file_path: File where error occurred
        build_phase: Build phase where error occurred

    Returns:
        Pattern info dict (see ErrorSession.record)
    """
    return get_session().record(error, file_path=file_path, build_phase=build_phase)
