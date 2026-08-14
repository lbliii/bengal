"""Debounce/coalesce watcher events while a rebuild is in flight.

Changes that arrive during a build are queued and flushed as one follow-up
rebuild. Lock order is unchanged: `_build_lock` is held only for the
queue/flag handshake, not for the build itself.
"""

from typing import TYPE_CHECKING, Any

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger("bengal.server.build_trigger")


def trigger_build(
    trigger: Any,
    changed_paths: set[Path],
    event_types: set[str],
) -> None:
    """
    Trigger a build for the given changed paths.

    This method:
    1. Determines build strategy (incremental vs full)
    2. Runs pre-build hooks
    3. Submits build to BuildExecutor
    4. Runs post-build hooks
    5. Notifies clients to reload

    If a build is already in progress, changes are queued and will trigger
    another build when the current one completes. This prevents lost changes
    during rapid editing (especially important for autodoc pages).

    Args:
        changed_paths: Set of changed file paths
        event_types: Set of event types (created, modified, deleted, moved)
    """
    with trigger._build_lock:
        if trigger._building:
            # Queue changes instead of discarding them
            trigger._pending_changes.update(changed_paths)
            trigger._pending_event_types.update(event_types)
            logger.debug(
                "build_changes_queued",
                queued_count=len(changed_paths),
                total_pending=len(trigger._pending_changes),
            )
            return
        trigger._building = True

    try:
        trigger._execute_build(changed_paths, event_types)
    finally:
        # Check for queued changes before releasing lock
        queued_changes: set[Path] = set()
        queued_events: set[str] = set()
        with trigger._build_lock:
            trigger._building = False
            if trigger._pending_changes:
                queued_changes = trigger._pending_changes.copy()
                queued_events = trigger._pending_event_types.copy()
                trigger._pending_changes.clear()
                trigger._pending_event_types.clear()

        # Trigger another build if changes were queued during this build
        if queued_changes:
            logger.info(
                "build_queued_changes_triggering",
                queued_count=len(queued_changes),
                queued_events=list(queued_events),
            )
            # Recursive call to handle the queued changes
            trigger.trigger_build(queued_changes, queued_events)
